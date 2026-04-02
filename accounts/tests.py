from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import LedgerEntry
from agents.models import Agent
from billing.models import Invoice
from customers.models import Customer
from deals.models import Deal
from deals.models_commission import Commission
from accounts.models import UserProfile
from leads.models import Lead, LeadActivity, LeadImportBatch, LeadSource, Property, PropertyImage, PropertyVideo
from payments.models import PaymentOrder
from rewards.models import ReferralEvent
from rewards.services import ensure_default_reward_rules, get_or_create_reward_coin, issue_scratch_cards
from wallet.models import WalletAccount
from wallet.services import get_or_create_wallet
from agents.hierarchy import ensure_wallet
from accounts.views import _wallet_tabs_for_user


class SignupUserLimitTests(TestCase):
    @override_settings(MAX_TEST_USERS=1)
    def test_signup_blocked_after_limit(self):
        User = get_user_model()
        User.objects.create_user(
            email="u1@example.com",
            password="pass12345",
            username="u1",
            mobile="9000000001",
        )

        resp = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "u2@example.com",
                "username": "u2",
                "mobile": "9000000002",
                "password": "pass12345X",
            },
            follow=False,
            secure=True,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:login"), resp["Location"])

    @override_settings(MAX_TEST_USERS=1, DESKTOP_MODE=True, OTP_BYPASS=True)
    def test_signup_allowed_in_desktop_mode_even_after_limit(self):
        User = get_user_model()
        User.objects.create_user(
            email="u1@example.com",
            password="pass12345",
            username="u1",
            mobile="9000000001",
        )

        resp = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "u2@example.com",
                "username": "u2",
                "mobile": "9000000002",
                "password": "pass12345X",
            },
            follow=False,
            secure=True,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], reverse("accounts:dashboard"))


class PasswordLoginTests(TestCase):
    def test_password_login_authenticates_by_email_username_field(self):
        User = get_user_model()
        User.objects.create_user(
            email="user@example.com",
            password="pass12345",
            username="not-an-email",
            mobile="9000000099",
            is_active=True,
        )

        resp = self.client.post(
            reverse("accounts:login"),
            {"identifier": "user@example.com", "password": "pass12345"},
            follow=False,
            secure=True,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], reverse("accounts:dashboard"))


class LedgerEntryBalanceRecalcTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="pass12345",
            username="owner",
            mobile="9000000100",
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            full_name="P1",
            mobile=self.user.mobile,
            business_name="",
            business_type="",
        )
        self.party = self.profile
        self.account = self.profile

    def test_update_running_balance_does_not_recurse(self):
        e1 = LedgerEntry.objects.create(
            account=self.account,
            party=self.party,
            amount=Decimal("100.00"),
            txn_type="credit",
        )
        e2 = LedgerEntry.objects.create(
            account=self.account,
            party=self.party,
            amount=Decimal("40.00"),
            txn_type="debit",
        )
        e1.refresh_from_db()
        e2.refresh_from_db()

        # Running = +100 - 40
        self.assertEqual(e1.balance, Decimal("100.00"))
        self.assertEqual(e2.balance, Decimal("60.00"))


class DashboardRenderTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="dashboard-admin@example.com",
            password="pass12345",
            username="dashboardadmin",
            mobile="9000000101",
            is_staff=True,
            is_superuser=True,
        )
        self.lead = Lead.objects.create(
            name="Demo Lead",
            mobile="9000000199",
            email="lead@example.com",
            source=Lead.Source.WEBSITE,
            status=Lead.Status.NEW,
            stage=Lead.Stage.NEW,
            budget=Decimal("3500000.00"),
            city="Lucknow",
        )
        self.agent_user = User.objects.create_user(
            email="agent@example.com",
            password="pass12345",
            username="agentuser",
            mobile="9000000201",
            is_active=True,
        )
        self.agent_user.role = "agent"
        self.agent_user.save(update_fields=["role"])
        self.agent, _ = Agent.objects.get_or_create(
            user=self.agent_user,
            defaults={
                "name": "Demo Agent",
                "phone": "9000000202",
                "city": "Lucknow",
                "district": "Lucknow",
                "state": "UP",
                "approval_status": Agent.ApprovalStatus.APPROVED,
                "performance_score": 88,
                "commission_rate": Decimal("2.50"),
                "kyc_verified": True,
            },
        )
        Agent.objects.filter(pk=self.agent.pk).update(
            name="Demo Agent",
            phone="9000000202",
            city="Lucknow",
            district="Lucknow",
            state="UP",
            approval_status=Agent.ApprovalStatus.APPROVED,
            performance_score=88,
            commission_rate=Decimal("2.50"),
            kyc_verified=True,
        )
        self.property = Property.objects.create(
            title="Skyline Residency",
            price=Decimal("4500000.00"),
            city="Lucknow",
            district="Lucknow",
            state="UP",
            location="Gomti Nagar",
            pin_code="226010",
            property_type=Property.Type.APARTMENT,
            status=Property.Status.APPROVED,
            assigned_agent=self.agent,
        )
        PropertyImage.objects.create(
            property=self.property,
            image_url="/static/demo/lakeview-house.png",
            caption="Front Elevation",
            sort_order=0,
            is_primary=True,
        )
        PropertyVideo.objects.create(
            property=self.property,
            video_url="/static/demo/lakeview-house.mp4",
            caption="Walkthrough Tour",
        )
        self.customer_user = get_user_model().objects.create_user(
            email="customer@example.com",
            password="pass12345",
            username="customeruser",
            mobile="9000000210",
            is_active=True,
        )
        self.customer = Customer.objects.create(
            user=self.customer_user,
            buyer_type=Customer.BuyerType.BUYER,
            assigned_agent=self.agent,
            city="Lucknow",
            district="Lucknow",
            state="UP",
        )
        self.lead.assigned_agent = self.agent
        self.lead.interested_property = self.property
        self.lead.converted_customer = self.customer
        self.lead.save(update_fields=["assigned_agent", "interested_property", "converted_customer", "updated_at"])
        self.deal = Deal.objects.create(
            lead=self.lead,
            customer=self.customer,
            agent=self.agent,
            property=self.property,
            deal_amount=Decimal("3500000.00"),
            commission_rate=Decimal("2.00"),
            commission_amount=Decimal("70000.00"),
            status=Deal.Status.PENDING,
            stage=Deal.Stage.INITIATED,
        )
        LeadActivity.objects.create(
            lead=self.lead,
            actor=self.user,
            activity_type="whatsapp",
            note="Seeded activity for reports workspace",
        )

    def test_accounts_dashboard_renders_crm_sections(self):
        self.client.force_login(self.user)
        Lead.objects.create(
            name="Second Lead",
            mobile="9000000300",
            email="second@example.com",
            source=Lead.Source.FACEBOOK,
            status=Lead.Status.CLOSED,
            stage=Lead.Stage.CLOSED,
            budget=Decimal("1500000.00"),
            city="Kanpur",
        )
        response = self.client.get(
            f"{reverse('accounts:dashboard')}?tab=leads&lead_query=Demo",
            follow=True,
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lead List")
        self.assertContains(response, 'name="lead_date_range"', html=False)
        self.assertContains(response, 'name="lead_query"', html=False)
        self.assertContains(response, 'name="lead_date_from"', html=False)
        self.assertContains(response, 'name="lead_date_to"', html=False)
        self.assertContains(response, "Download CSV")
        self.assertContains(response, "Share on WhatsApp")
        self.assertContains(response, reverse("accounts:lead_workspace", args=[self.lead.id]))
        self.assertContains(response, "Demo Lead")
        self.assertNotContains(response, "Second Lead")
        self.assertContains(response, "Open CRM")
        self.assertContains(response, reverse("core_settings:feature_control_tower"))
        self.assertContains(response, "Feature Control Tower")
        self.assertNotContains(response, "Workspace Pulse")
        self.assertNotContains(response, "Lead Engine Signals")

    def test_admin_dashboard_shows_control_tower(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:dashboard"), follow=True, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Workspace")
        self.assertContains(response, "Admin Control Tower")
        self.assertContains(response, "Users, Agents, Customers")
        self.assertContains(response, "Quick Dock")
        self.assertContains(response, "Source Assignment")
        self.assertContains(response, "Assign Lead")
        self.assertContains(response, "Bulk Assign")
        self.assertContains(response, "Create Source")
        self.assertContains(response, reverse("admin:accounts_user_changelist"))
        self.assertContains(response, reverse("admin:agents_agent_changelist"))
        self.assertContains(response, reverse("admin:customers_customer_changelist"))
        self.assertContains(response, reverse("admin:leads_leadsource_changelist"))
        self.assertContains(response, reverse("admin:leads_leadimportbatch_changelist"))
        self.assertContains(response, reverse("core_settings:feature_control_tower"))
        self.assertContains(response, "/api/docs/")
        self.assertContains(response, "Smart CRM Ops")
        self.assertContains(response, "Geo Auto Assign")
        self.assertContains(response, "Photo to Lead")
        self.assertContains(response, "Invoice + Payment")
        self.assertContains(response, "Smart Technology Stack")
        self.assertContains(response, "/api/v1/communication/")
        self.assertContains(response, "WhatsApp Automation")
        self.assertContains(response, "Lead Source Filters")
        self.assertContains(response, "Source Assignment")
        self.assertContains(response, "Intake Dock")
        self.assertContains(response, "1. Upload")
        self.assertContains(response, "Preview Import")
        self.assertContains(response, "Scrape Leads")
        self.assertContains(response, "Download Demo CSV")
        self.assertContains(response, "Run Bulk Agent Action")
        self.assertContains(response, "Import Monitor")
        self.assertContains(response, "Select All")
        self.assertContains(response, "Quick Presets")
        self.assertContains(response, "Failed Rows Drilldown")
        self.assertContains(response, "Duplicate Lead Insights")
        self.assertNotContains(response, "Workspace Pulse")
        self.assertNotContains(response, "One command center for leads")

    def test_admin_dashboard_action_can_assign_leads_by_source(self):
        self.client.force_login(self.user)
        first_source_lead = Lead.objects.create(
            name="Source Lead One",
            mobile="9000000311",
            email="source1@example.com",
            source=Lead.Source.FACEBOOK_ADS,
            status=Lead.Status.NEW,
            stage=Lead.Stage.NEW,
            budget=Decimal("1100000.00"),
            city="Lucknow",
        )
        second_source_lead = Lead.objects.create(
            name="Source Lead Two",
            mobile="9000000312",
            email="source2@example.com",
            source=Lead.Source.FACEBOOK_ADS,
            status=Lead.Status.NEW,
            stage=Lead.Stage.NEW,
            budget=Decimal("1200000.00"),
            city="Lucknow",
        )
        response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {
                "action": "assign_by_source",
                "source": Lead.Source.FACEBOOK_ADS,
                "agent_id": self.agent.id,
                "limit": "100",
                "reason": "Source assignment test",
            },
            follow=True,
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        first_source_lead.refresh_from_db()
        second_source_lead.refresh_from_db()
        self.assertEqual(first_source_lead.assigned_agent_id, self.agent.id)
        self.assertEqual(second_source_lead.assigned_agent_id, self.agent.id)

    def test_admin_dashboard_action_can_export_demo_lead_template(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {
                "action": "export_demo_lead_template",
                "source": Lead.Source.WEBSITE,
            },
            follow=False,
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn('attachment; filename="lead-demo-template.csv"', response["Content-Disposition"])
        content = response.content.decode()
        self.assertIn("Neha Gupta", content)
        self.assertIn("Demo Scrape", content)
        self.assertNotIn("Rahul Sharma", content)

    def test_admin_dashboard_action_can_assign_lead(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {
                "action": "assign_lead",
                "lead_id": self.lead.id,
                "agent_id": self.agent.id,
                "reason": "Manual assign from dashboard",
            },
            follow=True,
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.assigned_agent_id, self.agent.id)

    def test_admin_dashboard_action_can_bulk_assign_and_create_source(self):
        self.client.force_login(self.user)
        bulk_lead = Lead.objects.create(
            name="Bulk Lead",
            mobile="9000000302",
            email="bulk@example.com",
            source=Lead.Source.WEBSITE,
            status=Lead.Status.NEW,
            stage=Lead.Stage.NEW,
            budget=Decimal("1200000.00"),
            city="Lucknow",
        )
        response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {
                "action": "bulk_assign_leads",
                "lead_ids": [self.lead.id, bulk_lead.id],
                "agent_id": self.agent.id,
                "reason": "Bulk assign from dashboard",
            },
            follow=True,
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.lead.refresh_from_db()
        bulk_lead.refresh_from_db()
        self.assertEqual(self.lead.assigned_agent_id, self.agent.id)
        self.assertEqual(bulk_lead.assigned_agent_id, self.agent.id)

        source_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {
                "action": "create_lead_source",
                "name": "Meta Ads",
                "slug": "meta-ads",
                "kind": LeadSource.Kind.FACEBOOK_ADS,
                "source_value": Lead.Source.FACEBOOK_ADS,
                "endpoint_url": "https://example.com/webhook",
                "verify_token": "verify-123",
                "webhook_secret": "secret-123",
                "auto_assign": "1",
            },
            follow=True,
            secure=True,
        )
        self.assertEqual(source_response.status_code, 200)
        self.assertTrue(LeadSource.objects.filter(slug="meta-ads", name="Meta Ads").exists())

    def test_admin_dashboard_action_can_create_and_manage_people(self):
        self.client.force_login(self.user)
        agent_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {
                "action": "create_agent",
                "name": "New Agent",
                "email": "newagent@example.com",
                "mobile": "9000000400",
                "username": "newagent",
                "city": "Lucknow",
                "district": "Lucknow",
                "state": "UP",
                "pin_code": "226010",
            },
            follow=True,
            secure=True,
        )
        self.assertEqual(agent_response.status_code, 200)
        agent = Agent.objects.select_related("user").get(user__email="newagent@example.com")
        self.assertTrue(agent.user.is_active)
        self.assertTrue(agent.is_active)

        customer_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {
                "action": "create_customer",
                "name": "New Customer",
                "email": "newcustomer@example.com",
                "mobile": "9000000401",
                "username": "newcustomer",
                "buyer_type": Customer.BuyerType.BUYER,
                "city": "Noida",
                "district": "Gautam Buddha Nagar",
                "state": "UP",
            },
            follow=True,
            secure=True,
        )
        self.assertEqual(customer_response.status_code, 200)
        customer = Customer.objects.select_related("user").get(user__email="newcustomer@example.com")
        self.assertTrue(customer.user.is_active)

        deactivate_agent_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {"action": "toggle_agent_status", "agent_id": agent.id, "state": "inactive"},
            follow=True,
            secure=True,
        )
        self.assertEqual(deactivate_agent_response.status_code, 200)
        agent.refresh_from_db()
        agent.user.refresh_from_db()
        self.assertFalse(agent.is_active)
        self.assertFalse(agent.user.is_active)

        deactivate_customer_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {"action": "toggle_customer_status", "customer_id": customer.id, "state": "inactive"},
            follow=True,
            secure=True,
        )
        self.assertEqual(deactivate_customer_response.status_code, 200)
        customer.user.refresh_from_db()
        self.assertFalse(customer.user.is_active)

        delete_agent_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {"action": "delete_agent", "agent_id": agent.id},
            follow=True,
            secure=True,
        )
        self.assertEqual(delete_agent_response.status_code, 200)
        self.assertFalse(Agent.objects.filter(id=agent.id).exists())

        delete_customer_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {"action": "delete_customer", "customer_id": customer.id},
            follow=True,
            secure=True,
        )
        self.assertEqual(delete_customer_response.status_code, 200)
        self.assertFalse(Customer.objects.filter(id=customer.id).exists())

    def test_admin_dashboard_action_can_create_manual_lead(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {
                "action": "create_lead",
                "name": "Manual Capture",
                "phone": "9000000600",
                "email": "manual-capture@example.com",
                "source": Lead.Source.MANUAL,
                "stage": Lead.Stage.NEW,
                "status": Lead.Status.NEW,
                "interest_type": Lead.InterestType.BUY,
                "city": "Lucknow",
                "district": "Lucknow",
                "state": "UP",
                "budget": "2400000",
                "notes": "Entered from dashboard",
                "auto_assign": "1",
            },
            follow=True,
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        lead = Lead.objects.get(mobile="9000000600")
        self.assertEqual(lead.name, "Manual Capture")
        self.assertEqual(lead.source, Lead.Source.MANUAL)
        self.assertEqual(lead.assigned_agent_id, self.agent.id)

    def test_admin_dashboard_action_can_edit_people_profiles(self):
        self.client.force_login(self.user)
        agent_create_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {
                "action": "create_agent",
                "name": "Editable Agent",
                "email": "editable-agent@example.com",
                "mobile": "9000000500",
                "username": "editableagent",
                "city": "Lucknow",
                "district": "Lucknow",
                "state": "UP",
                "pin_code": "226010",
            },
            follow=True,
            secure=True,
        )
        self.assertEqual(agent_create_response.status_code, 200)
        agent = Agent.objects.select_related("user").get(user__email="editable-agent@example.com")

        customer_create_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {
                "action": "create_customer",
                "name": "Editable Customer",
                "email": "editable-customer@example.com",
                "mobile": "9000000501",
                "username": "editablecustomer",
                "buyer_type": Customer.BuyerType.BUYER,
                "city": "Noida",
                "district": "Gautam Buddha Nagar",
                "state": "UP",
            },
            follow=True,
            secure=True,
        )
        self.assertEqual(customer_create_response.status_code, 200)
        customer = Customer.objects.select_related("user").get(user__email="editable-customer@example.com")

        agent_update_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {
                "action": "update_agent",
                "agent_id": agent.id,
                "name": "Updated Agent",
                "mobile": "9000000502",
                "city": "Delhi",
                "district": "New Delhi",
                "state": "Delhi",
                "pin_code": "110001",
                "specialization": Agent.Specialization.COMMERCIAL,
                "approval_status": Agent.ApprovalStatus.APPROVED,
                "is_active": "inactive",
            },
            follow=True,
            secure=True,
        )
        self.assertEqual(agent_update_response.status_code, 200)
        agent.refresh_from_db()
        agent.user.refresh_from_db()
        self.assertEqual(agent.name, "Updated Agent")
        self.assertEqual(agent.phone, "9000000502")
        self.assertEqual(agent.city, "Delhi")
        self.assertEqual(agent.specialization, Agent.Specialization.COMMERCIAL)
        self.assertEqual(agent.approval_status, Agent.ApprovalStatus.APPROVED)
        self.assertFalse(agent.is_active)
        self.assertFalse(agent.user.is_active)

        customer_update_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {
                "action": "update_customer",
                "customer_id": customer.id,
                "name": "Updated Customer",
                "mobile": "9000000503",
                "buyer_type": Customer.BuyerType.BOTH,
                "preferred_location": "Noida Sector 62",
                "city": "Noida",
                "district": "Gautam Buddha Nagar",
                "state": "UP",
                "pin_code": "201301",
                "is_active": "inactive",
            },
            follow=True,
            secure=True,
        )
        self.assertEqual(customer_update_response.status_code, 200)
        customer.refresh_from_db()
        customer.user.refresh_from_db()
        self.assertEqual(customer.buyer_type, Customer.BuyerType.BOTH)
        self.assertEqual(customer.preferred_location, "Noida Sector 62")
        self.assertEqual(customer.city, "Noida")
        self.assertFalse(customer.user.is_active)

    def test_admin_dashboard_action_can_bulk_manage_people(self):
        self.client.force_login(self.user)
        extra_agent_user = get_user_model().objects.create_user(
            email="bulk-agent@example.com",
            password="pass12345",
            username="bulkagent",
            mobile="9000000510",
            is_active=True,
        )
        extra_agent = Agent.objects.create(
            user=extra_agent_user,
            name="Bulk Agent",
            phone="9000000511",
            city="Lucknow",
            district="Lucknow",
            state="UP",
            approval_status=Agent.ApprovalStatus.APPROVED,
            performance_score=80,
            commission_rate=Decimal("2.50"),
            kyc_verified=True,
        )
        extra_customer_user = get_user_model().objects.create_user(
            email="bulk-customer@example.com",
            password="pass12345",
            username="bulkcustomer",
            mobile="9000000512",
            is_active=True,
        )
        extra_customer = Customer.objects.create(
            user=extra_customer_user,
            buyer_type=Customer.BuyerType.BUYER,
            city="Noida",
            district="Gautam Buddha Nagar",
            state="UP",
        )

        bulk_agent_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {
                "action": "bulk_manage_agents",
                "agent_ids": [self.agent.id, extra_agent.id],
                "bulk_action": "deactivate",
            },
            follow=True,
            secure=True,
        )
        self.assertEqual(bulk_agent_response.status_code, 200)
        self.agent.refresh_from_db()
        extra_agent.refresh_from_db()
        self.assertFalse(self.agent.is_active)
        self.assertFalse(extra_agent.is_active)
        self.agent.user.refresh_from_db()
        extra_agent.user.refresh_from_db()
        self.assertFalse(self.agent.user.is_active)
        self.assertFalse(extra_agent.user.is_active)

        bulk_customer_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {
                "action": "bulk_manage_customers",
                "customer_ids": [extra_customer.id],
                "bulk_action": "delete",
            },
            follow=True,
            secure=True,
        )
        self.assertEqual(bulk_customer_response.status_code, 200)
        self.assertFalse(Customer.objects.filter(id=extra_customer.id).exists())

    def test_admin_dashboard_shows_import_and_duplicate_insights(self):
        self.client.force_login(self.user)
        duplicate_lead = Lead.objects.create(
            name="Duplicate Lead",
            mobile=self.lead.mobile,
            email="duplicate@example.com",
            source=Lead.Source.WEBSITE,
            status=Lead.Status.NEW,
            stage=Lead.Stage.NEW,
            budget=Decimal("1800000.00"),
            city="Lucknow",
            is_duplicate=True,
            duplicate_reason="Matched by phone/email",
        )
        LeadImportBatch.objects.create(
            source_name="API Feed",
            import_type=LeadImportBatch.ImportType.API,
            status=LeadImportBatch.Status.FAILED,
            total_rows=10,
            processed_rows=10,
            created_leads=4,
            duplicate_rows=2,
            failed_rows=3,
            error_report=[
                {"row": 2, "message": "Invalid phone"},
                {"row": 4, "message": "Duplicate lead detected"},
                {"row": 7, "message": "Missing name"},
            ],
        )
        response = self.client.get(reverse("accounts:dashboard"), follow=True, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Failed Rows Drilldown")
        self.assertContains(response, "Duplicate Lead Insights")
        self.assertContains(response, "API Feed")
        self.assertContains(response, "Invalid phone")
        self.assertContains(response, duplicate_lead.name)

        export_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {"action": "export_failed_imports"},
            follow=False,
            secure=True,
        )
        self.assertEqual(export_response.status_code, 200)
        self.assertEqual(export_response["Content-Type"], "text/csv")
        self.assertIn('attachment; filename="failed-import-rows.csv"', export_response["Content-Disposition"])
        self.assertIn("Invalid phone", export_response.content.decode())

        duplicate_export_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {"action": "export_duplicate_leads"},
            follow=False,
            secure=True,
        )
        self.assertEqual(duplicate_export_response.status_code, 200)
        self.assertEqual(duplicate_export_response["Content-Type"], "text/csv")
        self.assertIn('attachment; filename="duplicate-leads.csv"', duplicate_export_response["Content-Disposition"])
        self.assertIn("Matched by phone/email", duplicate_export_response.content.decode())

        resolve_response = self.client.post(
            reverse("accounts:admin_dashboard_action"),
            {"action": "resolve_duplicate_lead", "lead_id": duplicate_lead.id},
            follow=True,
            secure=True,
        )
        self.assertEqual(resolve_response.status_code, 200)
        duplicate_lead.refresh_from_db()
        self.assertFalse(duplicate_lead.is_duplicate)
        self.assertEqual(duplicate_lead.duplicate_reason, "")
        self.assertIsNone(duplicate_lead.duplicate_of)

    def test_accounts_dashboard_leads_tab_exports_filtered_csv(self):
        self.client.force_login(self.user)
        Lead.objects.create(
            name="Archived Lead",
            mobile="9000000301",
            email="archived@example.com",
            source=Lead.Source.GOOGLE,
            status=Lead.Status.CLOSED,
            stage=Lead.Stage.CLOSED,
            budget=Decimal("990000.00"),
            city="Noida",
        )
        response = self.client.get(
            f"{reverse('accounts:dashboard')}?tab=leads&lead_status=new&lead_export=csv",
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn('attachment; filename="lead-list.csv"', response["Content-Disposition"])
        content = response.content.decode()
        self.assertIn("Demo Lead", content)
        self.assertNotIn("Archived Lead", content)

    def test_agent_dashboard_renders_without_wallet_relation_error(self):
        self.client.force_login(self.agent_user)
        response = self.client.get(f"{reverse('accounts:dashboard')}?tab=dashboard", follow=True, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard Overview")
        self.assertContains(response, "Wallet")

    def test_lead_workspace_renders_action_sections(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:lead_workspace", args=[self.lead.id]), follow=True, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lead CRM Workspace")
        self.assertContains(response, "Agent Action Buttons")
        self.assertContains(response, self.lead.name)

    def test_lead_workspace_note_action_creates_activity(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:lead_workspace_action", args=[self.lead.id]),
            {"action": "add_note", "note": "Lead contacted from dashboard", "return_anchor": "timeline-panel"},
            follow=True,
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            LeadActivity.objects.filter(
                lead=self.lead,
                activity_type="note",
                note__icontains="Lead contacted from dashboard",
            ).exists()
        )

    def test_superadmin_index_renders_control_tower(self):
        self.client.force_login(self.user)
        response = self.client.get("/superadmin/", follow=True, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Real Estate Control Tower")

    def test_dashboard_tabs_expose_property_deal_agent_and_wallet_openers(self):
        self.client.force_login(self.user)

        properties_response = self.client.get(f"{reverse('accounts:dashboard')}?tab=properties", follow=True, secure=True)
        self.assertEqual(properties_response.status_code, 200)
        self.assertContains(properties_response, reverse("accounts:property_workspace", args=[self.property.id]))
        self.assertContains(properties_response, "Apply Filters")
        self.assertContains(properties_response, 'name="property_date_range"', html=False)
        self.assertContains(properties_response, 'name="property_date_from"', html=False)
        self.assertContains(properties_response, 'name="property_date_to"', html=False)
        self.assertNotContains(properties_response, "Workspace Pulse")

        deals_response = self.client.get(f"{reverse('accounts:dashboard')}?tab=deals", follow=True, secure=True)
        self.assertEqual(deals_response.status_code, 200)
        self.assertContains(deals_response, reverse("accounts:deal_workspace", args=[self.deal.id]))
        self.assertContains(deals_response, "Download CSV")
        self.assertContains(deals_response, 'name="deal_date_range"', html=False)
        self.assertContains(deals_response, 'name="deal_date_from"', html=False)
        self.assertContains(deals_response, 'name="deal_date_to"', html=False)
        self.assertNotContains(deals_response, "Workspace Pulse")

        agents_response = self.client.get(f"{reverse('accounts:dashboard')}?tab=agents", follow=True, secure=True)
        self.assertEqual(agents_response.status_code, 200)
        self.assertContains(agents_response, reverse("accounts:agent_workspace", args=[self.agent.id]))
        self.assertContains(agents_response, "Share on WhatsApp")
        self.assertContains(agents_response, 'name="agent_date_range"', html=False)
        self.assertContains(agents_response, 'name="agent_date_from"', html=False)
        self.assertContains(agents_response, 'name="agent_date_to"', html=False)
        self.assertNotContains(agents_response, "Workspace Pulse")

        reports_response = self.client.get(f"{reverse('accounts:dashboard')}?tab=reports", follow=True, secure=True)
        self.assertEqual(reports_response.status_code, 200)
        self.assertContains(reports_response, "Search Activity")
        self.assertContains(reports_response, "Download CSV")
        self.assertNotContains(reports_response, "Workspace Pulse")

        wallet_response = self.client.get(f"{reverse('accounts:dashboard')}?tab=wallet", follow=True, secure=True)
        self.assertEqual(wallet_response.status_code, 200)
        self.assertContains(wallet_response, "Wallet Detail")
        self.assertContains(wallet_response, reverse("accounts:wallet_workspace"))

    def test_property_deal_agent_wallet_reports_and_settings_workspaces_render(self):
        self.client.force_login(self.user)

        property_response = self.client.get(reverse("accounts:property_workspace", args=[self.property.id]), follow=True, secure=True)
        self.assertEqual(property_response.status_code, 200)
        self.assertContains(property_response, "Property Workspace")
        self.assertContains(property_response, self.property.title)
        self.assertContains(property_response, "Live Map")
        self.assertContains(property_response, "Google + MapMyIndia")
        self.assertContains(property_response, "Property Snapshot")
        self.assertContains(property_response, "Media + Finance at a glance")
        self.assertContains(property_response, "Open Google Maps")
        self.assertContains(property_response, "MapMyIndia Demo")
        self.assertContains(property_response, "Media Vault")
        self.assertContains(property_response, "Media Showcase")
        self.assertContains(property_response, "Featured Image + Video")
        self.assertContains(property_response, "Save Image")
        self.assertContains(property_response, "Save Video")
        self.assertContains(property_response, "obj-card-grid--mosaic")
        self.assertContains(property_response, "data-lightbox-modal", html=False)
        self.assertContains(property_response, "Primary")
        self.assertContains(property_response, "Open")
        self.assertContains(property_response, "Preview")
        self.assertContains(property_response, "Front Elevation")
        self.assertContains(property_response, "Walkthrough Tour")
        self.assertContains(property_response, "/static/demo/lakeview-house.png")
        self.assertContains(property_response, "/static/demo/lakeview-house.mp4")
        self.assertContains(property_response, "Invoice")
        self.assertContains(property_response, "Commission")
        self.assertContains(property_response, "Deal Mapping")
        self.assertContains(property_response, "Property + Lead + Customer + Agent")
        self.assertContains(property_response, "customer@example.com")
        self.assertContains(property_response, "Invoice + Commission Release")
        self.assertContains(property_response, "Generate Link")
        self.assertContains(property_response, "Release Commission")

        deal_response = self.client.get(reverse("accounts:deal_workspace", args=[self.deal.id]), follow=True, secure=True)
        self.assertEqual(deal_response.status_code, 200)
        self.assertContains(deal_response, "Deal Workspace")
        self.assertContains(deal_response, f"Deal #{self.deal.id}")

        agent_response = self.client.get(reverse("accounts:agent_workspace", args=[self.agent.id]), follow=True, secure=True)
        self.assertEqual(agent_response.status_code, 200)
        self.assertContains(agent_response, "Agent Workspace")
        self.assertContains(agent_response, self.agent.name)

        wallet_response = self.client.get(reverse("accounts:wallet_workspace"), follow=True, secure=True)
        self.assertEqual(wallet_response.status_code, 200)
        self.assertContains(wallet_response, "Wallet Workspace")

        reports_response = self.client.get(reverse("accounts:reports_workspace"), follow=True, secure=True)
        self.assertEqual(reports_response.status_code, 200)
        self.assertContains(reports_response, "Reports Workspace")
        self.assertContains(reports_response, reverse("accounts:lead_workspace", args=[self.lead.id]))
        self.assertContains(reports_response, "Deal Trace")
        self.assertContains(reports_response, "Property-to-Deal Map")
        self.assertContains(reports_response, "customer@example.com")

        settings_response = self.client.get(reverse("accounts:settings_workspace"), follow=True, secure=True)
        self.assertEqual(settings_response.status_code, 200)
        self.assertContains(settings_response, "Settings Workspace")

    def test_agent_wallet_tabs_helper_shows_reward_tabs(self):
        self.assertEqual(
            [tab["key"] for tab in _wallet_tabs_for_user(self.agent_user, "/wallet")],
            ["dashboard", "transactions", "spin", "rewards", "referrals", "scratch"],
        )

    def test_agent_wallet_spin_ajax_returns_spin_result(self):
        self.client.force_login(self.agent_user)
        ensure_default_reward_rules()
        reward_coin = get_or_create_reward_coin(self.agent_user)
        reward_coin.available_spins = 1
        reward_coin.save(update_fields=["available_spins", "updated_at"])

        response = self.client.post(
            reverse("accounts:wallet_spin_api"),
            {},
            follow=False,
            secure=True,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("spin", payload)
        self.assertEqual(payload["remaining_spins"], 0)

    def test_agent_wallet_spin_json_fallback_without_requested_with_header(self):
        self.client.force_login(self.agent_user)
        ensure_default_reward_rules()
        reward_coin = get_or_create_reward_coin(self.agent_user)
        reward_coin.available_spins = 1
        reward_coin.save(update_fields=["available_spins", "updated_at"])

        response = self.client.post(
            reverse("accounts:wallet_spin_api"),
            {},
            follow=False,
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("spin", payload)

    def test_agent_wallet_scratch_reveal_ajax_returns_success(self):
        self.client.force_login(self.agent_user)
        ensure_default_reward_rules()
        issue_scratch_cards(self.agent_user, count=1, metadata={"source": "test"})
        card = self.agent_user.scratch_cards.first()
        self.assertIsNotNone(card)

        response = self.client.post(
            reverse("accounts:wallet_scratch_reveal_api"),
            {"card_id": card.id},
            follow=False,
            secure=True,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["scratch"]["status"], "revealed")

    def test_agent_wallet_referrals_tab_shows_copy_actions(self):
        self.client.force_login(self.agent_user)
        response = self.client.get(f"{reverse('accounts:wallet_workspace')}?tab=referrals", follow=True, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-copy-target="code"')
        self.assertContains(response, 'data-copy-target="link"')
        self.assertContains(response, 'data-copy-target="message"')
        self.assertContains(response, 'data-copy-share-whatsapp')
        self.assertContains(response, 'aria-label="Share on WhatsApp"')
        self.assertContains(response, 'aria-label="Share by SMS"')
        self.assertContains(response, 'aria-label="Share by email"')

    def test_agent_wallet_scratch_tab_shows_phone_style_overlay(self):
        self.client.force_login(self.agent_user)
        ensure_default_reward_rules()
        issue_scratch_cards(self.agent_user, count=1, metadata={"source": "test"})
        response = self.client.get(f"{reverse('accounts:wallet_workspace')}?tab=scratch", follow=True, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-scratch-card')
        self.assertContains(response, 'data-scratch-canvas')
        self.assertContains(response, 'w-scratch-cover')

    @override_settings(DESKTOP_MODE=True)
    def test_wallet_workspace_demo_mode_auto_seeds_spin_and_scratch(self):
        self.client.force_login(self.agent_user)
        response = self.client.get(f"{reverse('accounts:wallet_workspace')}?tab=spin", follow=True, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Spin wheel"')
        self.assertNotContains(response, 'w-spin-button" type="submit" disabled')
        scratch_response = self.client.get(f"{reverse('accounts:wallet_workspace')}?tab=scratch", follow=True, secure=True)
        self.assertEqual(scratch_response.status_code, 200)
        self.assertContains(scratch_response, 'data-scratch-card')

    def test_wallet_spin_api_returns_json_without_ajax_header(self):
        self.client.force_login(self.agent_user)
        ensure_default_reward_rules()
        reward_coin = get_or_create_reward_coin(self.agent_user)
        reward_coin.available_spins = 1
        reward_coin.save(update_fields=["available_spins", "updated_at"])

        response = self.client.post(
            reverse("accounts:wallet_spin_api"),
            {},
            follow=False,
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])

    def test_wallet_workspace_action_returns_json_for_spin_without_ajax_header(self):
        self.client.force_login(self.agent_user)
        ensure_default_reward_rules()
        reward_coin = get_or_create_reward_coin(self.agent_user)
        reward_coin.available_spins = 1
        reward_coin.save(update_fields=["available_spins", "updated_at"])

        response = self.client.post(
            reverse("accounts:wallet_workspace_action"),
            {"action": "spin", "active_tab": "spin"},
            follow=False,
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("spin", payload)

    def test_wallet_scratch_reveal_api_returns_json_without_ajax_header(self):
        self.client.force_login(self.agent_user)
        ensure_default_reward_rules()
        issue_scratch_cards(self.agent_user, count=1, metadata={"source": "test"})
        card = self.agent_user.scratch_cards.first()
        self.assertIsNotNone(card)

        response = self.client.post(
            reverse("accounts:wallet_scratch_reveal_api"),
            {"card_id": card.id},
            follow=False,
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])

    def test_wallet_workspace_action_returns_json_for_scratch_without_ajax_header(self):
        self.client.force_login(self.agent_user)
        ensure_default_reward_rules()
        issue_scratch_cards(self.agent_user, count=1, metadata={"source": "test"})
        card = self.agent_user.scratch_cards.first()
        self.assertIsNotNone(card)

        response = self.client.post(
            reverse("accounts:wallet_workspace_action"),
            {"action": "reveal_scratch", "active_tab": "scratch", "card_id": card.id},
            follow=False,
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("scratch", payload)

    def test_property_workspace_can_generate_payment_link_and_release_commission(self):
        self.client.force_login(self.user)
        agent_wallet = ensure_wallet(self.agent)
        agent_wallet.refresh_from_db()
        self.assertEqual(agent_wallet.balance, Decimal("0.00"))
        payment_response = self.client.post(
            reverse("accounts:property_workspace", args=[self.property.id]),
            {
                "action": "generate_payment_link",
                "deal_id": self.deal.id,
                "amount": "3500000.00",
                "gateway": "dummy",
            },
            follow=True,
            secure=True,
        )
        self.assertEqual(payment_response.status_code, 200)
        invoice = Invoice.objects.filter(lead=self.lead).select_related("payment_order").first()
        self.assertIsNotNone(invoice)
        self.assertIsNotNone(invoice.payment_order)

        invoice.payment_order.mark_paid(provider_payment_id="PAY-DEMO-001")
        commission_response = self.client.post(
            reverse("accounts:property_workspace", args=[self.property.id]),
            {
                "action": "release_commission",
                "deal_id": self.deal.id,
            },
            follow=True,
            secure=True,
        )
        self.assertEqual(commission_response.status_code, 200)
        commission = Commission.objects.get(deal=self.deal)
        self.assertTrue(commission.settled)
        agent_wallet.refresh_from_db()
        self.assertEqual(agent_wallet.balance, commission.agent_amount)

    def test_property_tab_date_filter_limits_rows(self):
        self.client.force_login(self.user)
        older_property = Property.objects.create(
            title="Old Hills",
            price=Decimal("3200000.00"),
            city="Lucknow",
            district="Lucknow",
            state="UP",
            location="Aliganj",
            pin_code="226024",
            property_type=Property.Type.APARTMENT,
            status=Property.Status.APPROVED,
            assigned_agent=self.agent,
        )
        old_stamp = timezone.now() - timedelta(days=10)
        Property.objects.filter(pk=older_property.pk).update(created_at=old_stamp, updated_at=old_stamp)

        response = self.client.get(
            f"{reverse('accounts:dashboard')}?tab=properties&property_date_from={timezone.localdate().isoformat()}",
            follow=True,
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skyline Residency")
        self.assertNotContains(response, "Old Hills")

    def test_lead_tab_today_preset_limits_rows(self):
        self.client.force_login(self.user)
        old_lead = Lead.objects.create(
            name="Yesterday Lead",
            mobile="9000000302",
            email="yesterday@example.com",
            source=Lead.Source.GOOGLE,
            status=Lead.Status.NEW,
            stage=Lead.Stage.NEW,
            budget=Decimal("1800000.00"),
            city="Noida",
        )
        old_stamp = timezone.now() - timedelta(days=1)
        Lead.objects.filter(pk=old_lead.pk).update(created_at=old_stamp, updated_at=old_stamp)

        response = self.client.get(
            f"{reverse('accounts:dashboard')}?tab=leads&lead_date_range=today",
            follow=True,
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Demo Lead")
        self.assertNotContains(response, "Yesterday Lead")


class SettingsWorkspaceProfileTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="settings-user@example.com",
            password="pass12345",
            username="settingsuser",
            mobile="9000000441",
            is_active=True,
        )

    def test_settings_workspace_updates_profile_details(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:settings_workspace"),
            {
                "email": "settings-user@example.com",
                "full_name": "Settings User",
                "mobile": "9000000441",
                "business_name": "Modern Estates",
                "business_type": "Real Estate",
                "gst_number": "09ABCDE1234F1Z5",
                "address": "Sector 21, Noida",
            },
            follow=True,
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Workspace saved successfully.")
        profile = UserProfile.objects.get(user=self.user)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Settings User")
        self.assertEqual(profile.business_name, "Modern Estates")


@override_settings(DESKTOP_MODE=True, OTP_BYPASS=True, DISABLE_CELERY=True)
class ReferralSignupTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.referrer = User.objects.create_user(
            email="referrer@example.com",
            password="pass12345",
            username="referrer",
            mobile="9000000301",
            is_active=True,
        )

    def test_signup_page_prefills_referral_code(self):
        response = self.client.get(f"{reverse('accounts:signup')}?ref={self.referrer.referral_code}", secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.referrer.referral_code)

    def test_signup_assigns_referred_by_and_tracks_event(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "invitee@example.com",
                "username": "invitee",
                "mobile": "9000000302",
                "password": "pass12345X",
                "referral_code": self.referrer.referral_code,
            },
            follow=False,
            secure=True,
        )
        self.assertEqual(response.status_code, 302)
        invitee = get_user_model().objects.get(email="invitee@example.com")
        self.assertEqual(invitee.referred_by_id, self.referrer.id)
        self.assertTrue(
            ReferralEvent.objects.filter(referrer=self.referrer, referred_user=invitee).exists()
        )

    def test_edit_profile_renders_even_with_duplicate_wallet_accounts(self):
        self.client.force_login(self.referrer)
        wallet = get_or_create_wallet(self.referrer)
        WalletAccount.objects.create(
            user=self.referrer,
            wallet=wallet,
            account_type=WalletAccount.AccountType.WALLET,
            linked_wallet=wallet,
            label="Internal Wallet 1",
            status=WalletAccount.Status.VERIFIED,
        )
        WalletAccount.objects.create(
            user=self.referrer,
            wallet=wallet,
            account_type=WalletAccount.AccountType.WALLET,
            linked_wallet=wallet,
            label="Internal Wallet 2",
            status=WalletAccount.Status.VERIFIED,
        )

        response = self.client.get(reverse("accounts:edit_profile"), follow=True, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Wallet Snapshot")
        self.assertContains(response, reverse("kyc:dashboard"))
        self.assertContains(response, reverse("billing:invoice_list"))
