from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from khataapp.models import UserProfile as KhataProfile
from wallet.models import WalletAccount, WalletTransfer, WithdrawRequest
from wallet.services import credit_wallet, get_or_create_wallet, mark_withdrawal_paid, request_withdrawal, sync_profile_payment_accounts, transfer_between_wallets


@override_settings(DISABLE_CELERY=True)
class WalletServiceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.sender = User.objects.create_user(
            email="wallet-sender@example.com",
            password="pass12345",
            username="walletsender",
            mobile="9000000401",
            is_active=True,
        )
        self.receiver = User.objects.create_user(
            email="wallet-receiver@example.com",
            password="pass12345",
            username="walletreceiver",
            mobile="9000000402",
            is_active=True,
        )

    def test_transfer_between_wallets_updates_both_sides(self):
        credit_wallet(self.sender, Decimal("1000.00"), source="manual", narration="Seed balance", actor=self.sender)
        transfer = transfer_between_wallets(self.sender, self.receiver, Decimal("250.00"), note="Internal payout", actor=self.sender)

        self.assertEqual(transfer.status, WalletTransfer.Status.SUCCESS)
        self.assertEqual(get_or_create_wallet(self.sender).balance, Decimal("750.00"))
        self.assertEqual(get_or_create_wallet(self.receiver).balance, Decimal("250.00"))

    def test_withdrawal_lifecycle_locks_then_settles_balance(self):
        credit_wallet(self.sender, Decimal("500.00"), source="manual", narration="Seed balance", actor=self.sender)

        withdraw_request = request_withdrawal(self.sender, Decimal("120.00"))
        wallet = get_or_create_wallet(self.sender)
        self.assertEqual(withdraw_request.status, WithdrawRequest.Status.PENDING)
        self.assertEqual(wallet.balance, Decimal("500.00"))
        self.assertEqual(wallet.locked_balance, Decimal("120.00"))
        self.assertEqual(wallet.available_balance, Decimal("380.00"))

        mark_withdrawal_paid(withdraw_request, approver=self.sender, payout_reference="UTR123")
        wallet.refresh_from_db()
        withdraw_request.refresh_from_db()
        self.assertEqual(withdraw_request.status, WithdrawRequest.Status.PAID)
        self.assertEqual(wallet.balance, Decimal("380.00"))
        self.assertEqual(wallet.locked_balance, Decimal("0.00"))

    def test_sync_profile_payment_accounts_tolerates_duplicate_rows(self):
        wallet = get_or_create_wallet(self.sender)
        profile = KhataProfile.objects.create(
            user=self.sender,
            mobile=self.sender.mobile,
            full_name="Wallet Sender",
            upi_id="walletsender@upi",
            account_number="1234567890",
            ifsc_code="TEST0001",
            bank_name="Demo Bank",
        )
        WalletAccount.objects.create(
            user=self.sender,
            wallet=wallet,
            account_type=WalletAccount.AccountType.WALLET,
            linked_wallet=wallet,
            label="Internal Wallet A",
            status=WalletAccount.Status.VERIFIED,
        )
        WalletAccount.objects.create(
            user=self.sender,
            wallet=wallet,
            account_type=WalletAccount.AccountType.WALLET,
            linked_wallet=wallet,
            label="Internal Wallet B",
            status=WalletAccount.Status.VERIFIED,
        )

        created_accounts = sync_profile_payment_accounts(self.sender)

        self.assertEqual(profile.upi_id, "walletsender@upi")
        self.assertLessEqual(
            WalletAccount.objects.filter(user=self.sender, account_type=WalletAccount.AccountType.WALLET, linked_wallet=wallet).count(),
            2,
        )
        self.assertEqual(WalletAccount.objects.filter(user=self.sender, account_type=WalletAccount.AccountType.UPI, upi_id="walletsender@upi").count(), 1)
        self.assertEqual(WalletAccount.objects.filter(user=self.sender, account_type=WalletAccount.AccountType.BANK, account_number="1234567890").count(), 1)
        self.assertEqual(len(created_accounts), 2)
