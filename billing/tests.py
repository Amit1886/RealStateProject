from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from billing.invoice_engine import ensure_invoice_for_payment_order
from billing.models import FeatureRegistry, Invoice, Plan, PlanFeature, Subscription, UserFeatureOverride
from billing.services import get_effective_plan, sync_feature_registry, user_has_feature
from django.contrib.auth import get_user_model
from khataapp.models import UserProfile
from payments.models import PaymentOrder
from wallet.services import get_or_create_wallet


class GroupPlanPermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user1@example.com",
            password="pass12345",
            username="user1",
            mobile="9990001111",
        )
        UserProfile.objects.create(user=self.user)

        self.group_basic = Group.objects.create(name="basic-group")
        self.group_pro = Group.objects.create(name="pro-group")

        self.plan_basic = Plan.objects.create(name="Basic", price=0, price_monthly=0, price_yearly=0, trial_days=0, active=True)
        self.plan_pro = Plan.objects.create(name="Pro", price=999, price_monthly=999, price_yearly=9999, trial_days=0, active=True)

        self.plan_basic.groups.add(self.group_basic)
        self.plan_pro.groups.add(self.group_pro)

    def test_effective_plan_from_group_when_no_subscription_or_profile_plan(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.plan = None
        profile.save(update_fields=["plan"])

        self.user.groups.add(self.group_pro)

        plan = get_effective_plan(self.user)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.id, self.plan_pro.id)

    def test_effective_plan_prefers_active_subscription(self):
        self.user.groups.add(self.group_pro)

        Subscription.objects.create(user=self.user, plan=self.plan_basic, status="active", start_date=timezone.now())

        plan = get_effective_plan(self.user)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.id, self.plan_basic.id)

    def test_user_has_feature_uses_group_plan(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.plan = None
        profile.save(update_fields=["plan"])
        self.user.groups.add(self.group_pro)

        feature = FeatureRegistry.objects.create(key="custom.group_feature", label="Group Feature", group="Test", active=True)
        PlanFeature.objects.create(plan=self.plan_pro, feature=feature, enabled=True)

        self.assertTrue(user_has_feature(self.user, "custom.group_feature"))

    def test_user_feature_override_can_disable_feature(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.plan = self.plan_pro
        profile.save(update_fields=["plan"])

        feature = FeatureRegistry.objects.create(key="custom.override_feature", label="Override Feature", group="Test", active=True)
        PlanFeature.objects.create(plan=self.plan_pro, feature=feature, enabled=True)
        UserFeatureOverride.objects.create(user=self.user, feature=feature, is_enabled=False)

        self.assertFalse(user_has_feature(self.user, "custom.override_feature"))

    def test_global_feature_toggle_can_disable_everyone(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.plan = self.plan_pro
        profile.save(update_fields=["plan"])

        feature = FeatureRegistry.objects.create(key="custom.global_off_feature", label="Global Off Feature", group="Test", active=True)
        PlanFeature.objects.create(plan=self.plan_pro, feature=feature, enabled=True)
        UserFeatureOverride.objects.create(user=self.user, feature=feature, is_enabled=True)

        self.assertTrue(user_has_feature(self.user, "custom.global_off_feature"))
        feature.active = False
        feature.save(update_fields=["active"])
        self.assertFalse(user_has_feature(self.user, "custom.global_off_feature"))

    def test_real_estate_feature_registry_sync_includes_crm_keys(self):
        sync_feature_registry()
        self.assertTrue(FeatureRegistry.objects.filter(key="crm.leads").exists())
        self.assertTrue(FeatureRegistry.objects.filter(key="crm.properties").exists())
        self.assertTrue(FeatureRegistry.objects.filter(key="crm.project_launch").exists())


class BillingInvoiceWorkspaceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="billing-demo@example.com",
            password="pass12345",
            username="billingdemo",
            mobile="9000000602",
        )
        UserProfile.objects.create(user=self.user, full_name="Billing Demo")

    def test_invoice_pages_render_for_generated_wallet_invoice(self):
        wallet = get_or_create_wallet(self.user)
        payment_order = PaymentOrder.objects.create(
            user=self.user,
            wallet=wallet,
            amount="999.00",
            gateway=PaymentOrder.Gateway.DUMMY,
            purpose=PaymentOrder.Purpose.WALLET_TOPUP,
            status=PaymentOrder.Status.PAID,
        )
        invoice = ensure_invoice_for_payment_order(payment_order)

        self.client.force_login(self.user)
        list_response = self.client.get(reverse("billing:invoice_list"), secure=True)
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, invoice.invoice_number)

        detail_response = self.client.get(reverse("billing:invoice_detail", args=[invoice.invoice_number]), secure=True)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Wallet recharge")

        pdf_response = self.client.get(reverse("billing:invoice_pdf", args=[invoice.invoice_number]), secure=True)
        self.assertEqual(pdf_response.status_code, 200)


class SmartInvoiceApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="invoice-admin@example.com",
            password="pass12345",
            username="invoiceadmin",
            mobile="9000000603",
            is_staff=True,
            role="super_admin",
        )
        self.customer = User.objects.create_user(
            email="invoice-customer@example.com",
            password="pass12345",
            username="invoicecustomer",
            mobile="9000000604",
        )

    def test_invoice_create_and_payment_link_api(self):
        from leads.models import Lead
        from saas_core.models import Company

        company = Company.objects.create(name="Invoice API Realty")
        lead = Lead.objects.create(
            company=company,
            created_by=self.admin,
            name="Invoice Lead",
            mobile="9999900401",
            email="invoice.lead@example.com",
            deal_value="750000.00",
        )

        self.client.force_login(self.admin)
        invoice_response = self.client.post(
            reverse("api-invoice-create"),
            {"lead_id": lead.id, "amount": "750000.00", "product_name": "Lead Conversion Service"},
            secure=True,
        )
        self.assertEqual(invoice_response.status_code, 201)
        invoice_number = invoice_response.json()["invoice_number"]
        invoice = Invoice.objects.get(invoice_number=invoice_number)

        payment_response = self.client.post(
            reverse("api-payment-link"),
            {"invoice_id": invoice.id, "amount": "750000.00", "gateway": "dummy"},
            secure=True,
        )
        self.assertEqual(payment_response.status_code, 201)
        self.assertIn("payment_order", payment_response.json())
