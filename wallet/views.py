from __future__ import annotations

from django.http import HttpResponse
from django.db.models import Q
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from wallet.models import Wallet, WalletAccount, WalletAuditLog, WalletLedger, WalletTransaction, WalletTransfer, WithdrawRequest
from wallet.serializers import (
    WalletAccountSerializer,
    WalletAmountActionSerializer,
    WalletAuditLogSerializer,
    WalletLedgerSerializer,
    WalletSerializer,
    WalletStatementRequestSerializer,
    WalletTransactionSerializer,
    WalletTransferActionSerializer,
    WalletTransferSerializer,
    WithdrawRequestSerializer,
)
from wallet.services import (
    approve_withdrawal,
    create_linked_account,
    credit_wallet,
    debit_wallet,
    get_or_create_wallet,
    get_wallet_summary,
    mark_withdrawal_paid,
    reject_withdrawal,
    request_withdrawal,
    sync_profile_payment_accounts,
    transfer_between_wallets,
)
from wallet.statements import build_statement_rows, get_statement_queryset, render_statement_csv, render_statement_pdf, render_statement_xlsx


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Wallet.objects.select_related("user")
        if user.is_superuser or user.is_staff:
            return queryset
        return queryset.filter(user=user)

    @action(detail=False, methods=["get"])
    def balance(self, request):
        wallet = get_or_create_wallet(request.user)
        return Response(WalletSerializer(wallet, context={"request": request}).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        summary = get_wallet_summary(request.user)
        return Response(
            {
                "wallet": WalletSerializer(summary["wallet"], context={"request": request}).data,
                "available_balance": summary["available_balance"],
                "total_credit": summary["total_credit"],
                "total_debit": summary["total_debit"],
                "linked_accounts": WalletAccountSerializer(summary["linked_accounts"], many=True, context={"request": request}).data,
                "recent_transactions": WalletTransactionSerializer(summary["recent_transactions"], many=True, context={"request": request}).data,
                "recent_transfers": WalletTransferSerializer(summary["recent_transfers"], many=True, context={"request": request}).data,
                "withdraw_requests": WithdrawRequestSerializer(summary["withdraw_requests"], many=True, context={"request": request}).data,
            }
        )

    @action(detail=False, methods=["post"])
    def add_money(self, request):
        serializer = WalletAmountActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        wallet, txn = credit_wallet(
            request.user,
            serializer.validated_data["amount"],
            source=WalletTransaction.Source.ADD_MONEY,
            reference=serializer.validated_data.get("reference", ""),
            metadata=serializer.validated_data.get("metadata"),
            narration=serializer.validated_data.get("narration", "") or "Add money",
            actor=request.user,
        )
        return Response(
            {
                "wallet": WalletSerializer(wallet, context={"request": request}).data,
                "transaction": WalletTransactionSerializer(txn, context={"request": request}).data,
            }
        )

    @action(detail=False, methods=["post"])
    def spend(self, request):
        serializer = WalletAmountActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            wallet, txn = debit_wallet(
                request.user,
                serializer.validated_data["amount"],
                source=WalletTransaction.Source.SERVICE,
                reference=serializer.validated_data.get("reference", ""),
                metadata=serializer.validated_data.get("metadata"),
                narration=serializer.validated_data.get("narration", "") or "Service debit",
                actor=request.user,
            )
        except ValueError as exc:
            raise serializers.ValidationError({"amount": str(exc)})
        return Response(
            {
                "wallet": WalletSerializer(wallet, context={"request": request}).data,
                "transaction": WalletTransactionSerializer(txn, context={"request": request}).data,
            }
        )

    @action(detail=False, methods=["post"])
    def transfer(self, request):
        serializer = WalletTransferActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        recipient = None
        if data.get("recipient_wallet_code"):
            recipient_wallet = Wallet.objects.select_related("user").filter(wallet_code=data["recipient_wallet_code"]).first()
            if recipient_wallet:
                recipient = recipient_wallet.user
        elif data.get("recipient_user_id"):
            recipient_wallet = Wallet.objects.select_related("user").filter(user_id=data["recipient_user_id"]).first()
            recipient = recipient_wallet.user if recipient_wallet else None
        if recipient is None:
            raise serializers.ValidationError({"recipient_wallet_code": "Valid recipient wallet not found"})
        sender_account = WalletAccount.objects.filter(user=request.user, pk=data.get("sender_account_id")).first() if data.get("sender_account_id") else None
        receiver_account = WalletAccount.objects.filter(user=recipient, pk=data.get("receiver_account_id")).first() if data.get("receiver_account_id") else None
        try:
            transfer = transfer_between_wallets(
                request.user,
                recipient,
                data["amount"],
                note=data.get("note", ""),
                sender_account=sender_account,
                receiver_account=receiver_account,
                metadata=data.get("metadata"),
                actor=request.user,
            )
        except ValueError as exc:
            raise serializers.ValidationError({"amount": str(exc)})
        return Response(WalletTransferSerializer(transfer, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def sync_accounts(self, request):
        sync_profile_payment_accounts(request.user)
        accounts = WalletAccount.objects.filter(user=request.user).order_by("-is_default", "-updated_at")
        return Response(WalletAccountSerializer(accounts, many=True, context={"request": request}).data)

    @action(detail=False, methods=["get"])
    def statement(self, request):
        serializer = WalletStatementRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        wallet = get_or_create_wallet(request.user)
        queryset = get_statement_queryset(
            request.user,
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            entry_type=params.get("entry_type", ""),
            source=params.get("source", ""),
        )
        rows = build_statement_rows(queryset)
        export_format = params.get("format", "csv")
        filename_stub = f"wallet_statement_{wallet.wallet_code or wallet.pk}"
        if export_format == "xlsx":
            content = render_statement_xlsx(rows)
            response = HttpResponse(
                content,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename_stub}.xlsx"'
            return response
        if export_format == "pdf":
            pdf_bytes = render_statement_pdf(
                request.user,
                wallet,
                rows,
                start_date=params.get("start_date"),
                end_date=params.get("end_date"),
                request=request,
            )
            response = HttpResponse(pdf_bytes or b"", content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{filename_stub}.pdf"'
            return response
        response = HttpResponse(render_statement_csv(rows), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename_stub}.csv"'
        return response


class WalletAccountViewSet(viewsets.ModelViewSet):
    serializer_class = WalletAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = WalletAccount.objects.select_related("user", "wallet", "linked_wallet")
        if self.request.user.is_superuser or self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        data = serializer.validated_data
        account = create_linked_account(
            self.request.user,
            account_type=data["account_type"],
            label=data.get("label", ""),
            beneficiary_name=data.get("beneficiary_name", ""),
            bank_name=data.get("bank_name", ""),
            account_number=data.get("account_number", ""),
            ifsc_code=data.get("ifsc_code", ""),
            upi_id=data.get("upi_id", ""),
            linked_wallet=data.get("linked_wallet"),
            is_default=data.get("is_default", False),
            status=data.get("status", WalletAccount.Status.PENDING),
            metadata=data.get("metadata"),
        )
        serializer.instance = account


class WalletTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = WalletTransaction.objects.select_related("wallet", "wallet__user", "counterparty_wallet", "counterparty_wallet__user")
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return queryset
        return queryset.filter(wallet__user=user)


class WalletLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletLedgerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = WalletLedger.objects.select_related("wallet", "transaction", "actor")
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return queryset
        return queryset.filter(wallet__user=user)


class WalletTransferViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletTransferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = WalletTransfer.objects.select_related(
            "sender_wallet",
            "sender_wallet__user",
            "receiver_wallet",
            "receiver_wallet__user",
            "sender_transaction",
            "receiver_transaction",
        )
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return queryset
        return queryset.filter(Q(sender_wallet__user=user) | Q(receiver_wallet__user=user))


class WithdrawRequestViewSet(viewsets.ModelViewSet):
    serializer_class = WithdrawRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = WithdrawRequest.objects.select_related("wallet", "user", "destination_account", "processed_by")
        if user.is_superuser or user.is_staff:
            return queryset
        return queryset.filter(user=user)

    def perform_create(self, serializer):
        amount = serializer.validated_data["amount"]
        destination_account = serializer.validated_data.get("destination_account")
        try:
            request_obj = request_withdrawal(
                self.request.user,
                amount,
                metadata=serializer.validated_data.get("metadata"),
                destination_account=destination_account,
            )
            serializer.instance = request_obj
        except ValueError as exc:
            raise serializers.ValidationError({"amount": str(exc)})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        obj = self.get_object()
        approve_withdrawal(obj, approver=request.user, payout_reference=request.data.get("payout_reference", ""))
        return Response(WithdrawRequestSerializer(obj, context={"request": request}).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        obj = self.get_object()
        reject_withdrawal(obj, approver=request.user, reason=request.data.get("reason", ""))
        return Response(WithdrawRequestSerializer(obj, context={"request": request}).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def mark_paid(self, request, pk=None):
        obj = self.get_object()
        mark_withdrawal_paid(obj, approver=request.user, payout_reference=request.data.get("payout_reference", ""))
        return Response(WithdrawRequestSerializer(obj, context={"request": request}).data)


class WalletAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletAuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = WalletAuditLog.objects.select_related("wallet", "transaction", "actor")
        if self.request.user.is_superuser or self.request.user.is_staff:
            return queryset
        return queryset.filter(wallet__user=self.request.user)
