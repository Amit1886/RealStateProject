from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.utils import timezone

from billing.permissions import FeatureActionPermission
from .services import adjust_payment, settle_deal_commission
from .models import Deal, Payment
from .serializers import DealSerializer, PaymentSerializer


class DealViewSet(viewsets.ModelViewSet):
    queryset = Deal.objects.select_related("lead", "property", "agent", "company")
    serializer_class = DealSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.deals"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        role = (getattr(user, "role", "") or "").strip().lower()
        if role in {"agent", "super_agent", "area_admin"}:
            return qs.filter(agent__user=user)
        if role == "customer":
            return qs.filter(customer__user=user)
        company = getattr(user, "company", None)
        return qs.filter(company=company)

    def perform_create(self, serializer):
        lead = serializer.validated_data.get("lead")
        deal = serializer.save(
            company=serializer.validated_data.get("company") or getattr(lead, "company", None),
            property=serializer.validated_data.get("property") or getattr(lead, "interested_property", None),
            agent=serializer.validated_data.get("agent") or getattr(lead, "assigned_agent", None),
        )
        return deal

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        deal = self.get_object()
        deal.status = Deal.Status.WON
        deal.stage = Deal.Stage.CLOSED
        deal.closed_at = timezone.now()
        deal.closing_date = timezone.localdate()
        deal.save(update_fields=["status", "stage", "closed_at", "closing_date", "updated_at"])

        if deal.commission_amount > 0:
            settle_deal_commission(deal, settled=False, credit_agent_wallet=False, note=f"Deal {deal.id}")
        try:
            from communication.services import queue_notification_event

            recipients = [deal.agent.user]
            if getattr(deal.lead, "created_by", None):
                recipients.append(deal.lead.created_by)
            queue_notification_event(
                users=recipients,
                title="Deal closed",
                body=f"Deal #{deal.id} closed at {deal.deal_amount}.",
                lead=deal.lead,
                channels=["in_app", "email"],
                email=getattr(deal.agent.user, "email", ""),
                sender=request.user,
                metadata={"deal_id": deal.id, "commission_amount": str(deal.commission_amount)},
            )
        except Exception:
            pass
        return Response(DealSerializer(deal, context={"request": request}).data)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("deal", "lead", "customer", "agent", "approved_by")
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.deals"
    feature_key_map = {
        "approve": "crm.admin_override",
        "mark_paid": "crm.payment_adjustments",
        "adjust": "crm.payment_adjustments",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        role = (getattr(user, "role", "") or "").strip().lower()
        if role in {"agent", "super_agent", "area_admin"}:
            return qs.filter(agent__user=user)
        if role == "customer":
            return qs.filter(customer__user=user)
        company = getattr(user, "company", None)
        return qs.filter(company=company)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not (request.user.is_superuser or getattr(request.user, "is_staff", False)):
            raise PermissionDenied("Only admins can approve payouts.")
        payment = self.get_object()
        payment.status = Payment.Status.APPROVED
        payment.approved_by = request.user
        payment.approved_at = timezone.now()
        payment.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return Response(self.get_serializer(payment).data)

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        if not (request.user.is_superuser or getattr(request.user, "is_staff", False)):
            raise PermissionDenied("Only admins can mark payments paid.")
        payment = self.get_object()
        previous_status = payment.status
        payment.status = Payment.Status.PAID
        payment.paid_at = timezone.now()
        if previous_status != Payment.Status.APPROVED:
            payment.approved_by = request.user
            payment.approved_at = payment.approved_at or timezone.now()
        payment.save(update_fields=["status", "paid_at", "approved_by", "approved_at", "updated_at"])
        return Response(self.get_serializer(payment).data)

    @action(detail=True, methods=["post"])
    def adjust(self, request, pk=None):
        if not (request.user.is_superuser or getattr(request.user, "is_staff", False)):
            raise PermissionDenied("Only admins can adjust payments.")
        payment = self.get_object()
        adjusted_amount = request.data.get("adjusted_amount")
        if adjusted_amount is None:
            return Response({"detail": "adjusted_amount is required"}, status=400)
        try:
            adjusted_amount = float(adjusted_amount)
        except Exception:
            return Response({"detail": "adjusted_amount must be numeric"}, status=400)
        note = request.data.get("note", "")
        adjust_payment(payment, adjusted_amount=adjusted_amount, note=note, actor=request.user)
        return Response(self.get_serializer(payment).data)
