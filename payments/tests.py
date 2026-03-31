import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from billing.models import Invoice
from payments.models import PaymentOrder, PaymentTransaction
from payments.services.gateway import create_payment_order, simulate_payment_success
from wallet.services import get_or_create_wallet


@override_settings(DISABLE_CELERY=True)
class PaymentGatewayFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="payments@example.com",
            password="pass12345",
            username="paymentuser",
            mobile="9000000601",
        )

    def test_simulated_payment_credits_wallet_and_generates_invoice(self):
        wallet = get_or_create_wallet(self.user)
        payment_order = create_payment_order(
            user=self.user,
            wallet=wallet,
            amount=Decimal("1250.00"),
            gateway=PaymentOrder.Gateway.RAZORPAY,
        )

        paid_order, payment_txn = simulate_payment_success(payment_order)

        wallet.refresh_from_db()
        self.assertEqual(paid_order.status, PaymentOrder.Status.PAID)
        self.assertEqual(payment_txn.status, PaymentTransaction.Status.SUCCESS)
        self.assertTrue(payment_txn.credited_to_wallet)
        self.assertEqual(wallet.balance, Decimal("1250.00"))
        self.assertTrue(Invoice.objects.filter(payment_order=paid_order).exists())

    def test_checkout_page_renders_for_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("payments:checkout"), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add money to wallet")

    def test_generic_webhook_alias_processes_demo_payload(self):
        wallet = get_or_create_wallet(self.user)
        payment_order = create_payment_order(
            user=self.user,
            wallet=wallet,
            amount=Decimal("250.00"),
            gateway=PaymentOrder.Gateway.DUMMY,
        )

        response = self.client.post(
            reverse("api-payment-webhook"),
            json.dumps({"reference_id": str(payment_order.reference_id), "status": "paid", "payment_id": "PAY_DEMO_1"}),
            content_type="application/json",
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        payment_order.refresh_from_db()
        self.assertEqual(payment_order.status, PaymentOrder.Status.PAID)
