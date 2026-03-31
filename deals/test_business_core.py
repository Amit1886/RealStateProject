from django.test import TestCase

from accounts.models import SaaSRole, User
from agents.models import Agent
from crm.models import OverrideLog
from deals.models import Deal, Payment
from deals.services import adjust_payment
from leads.models import Lead
from saas_core.models import Company


class PaymentAdjustmentCoreTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Payment Core Realty")
        self.admin = User.objects.create_user(
            email="payment-admin@example.com",
            username="payment-admin",
            mobile="9444444444",
            password="Admin@123",
            role=SaaSRole.SUPER_ADMIN,
            company=self.company,
            is_staff=True,
        )
        agent_user = User.objects.create_user(
            email="payment-agent@example.com",
            username="payment-agent",
            mobile="9555555555",
            password="Agent@123",
            role=SaaSRole.AGENT,
            company=self.company,
        )
        self.agent = agent_user.agent_profile
        self.agent.name = "Payment Agent"
        self.agent.phone = agent_user.mobile
        self.agent.approval_status = Agent.ApprovalStatus.APPROVED
        self.agent.save()
        self.lead = Lead.objects.create(
            company=self.company,
            name="Payment Lead",
            mobile="9999944444",
            assigned_agent=self.agent,
            assigned_to=agent_user,
        )
        self.deal = Deal.objects.create(company=self.company, lead=self.lead, agent=self.agent)
        self.payment = Payment.objects.create(deal=self.deal, amount="50000.00")

    def test_adjust_payment_records_history_and_override(self):
        adjust_payment(self.payment, adjusted_amount="42000.00", note="Excess payment moved to next installment", actor=self.admin)

        self.payment.refresh_from_db()
        self.assertEqual(str(self.payment.adjusted_amount), "42000.00")
        self.assertEqual(self.payment.adjustment_note, "Excess payment moved to next installment")
        self.assertEqual(len(self.payment.adjustment_history), 1)
        self.assertTrue(OverrideLog.objects.filter(action_type="payment_adjustment", target_model="deals.Payment").exists())
