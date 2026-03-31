from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts.models import SaaSRole, User
from agents.kyc import approve_agent_kyc, reject_agent_kyc
from agents.models import Agent, AgentTransfer
from agents.transfer import perform_agent_transfer
from deals.models import Deal
from leads.models import Lead
from saas_core.models import Company


class AgentBusinessCoreTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Agent Core Realty")

    def _make_agent(self, email: str, username: str):
        user = User.objects.create_user(
            email=email,
            username=username,
            mobile=f"91{User.objects.count() + 100000000}",
            password="Agent@123",
            role=SaaSRole.AGENT,
            company=self.company,
        )
        agent = user.agent_profile
        agent.name = username.replace("-", " ").title()
        agent.phone = user.mobile
        agent.approval_status = Agent.ApprovalStatus.APPROVED
        agent.save()
        return user, agent

    def test_agent_kyc_approval_and_rejection(self):
        admin_user = User.objects.create_user(
            email="admin-core@example.com",
            username="admin-core",
            mobile="9111111111",
            password="Admin@123",
            role=SaaSRole.SUPER_ADMIN,
            company=self.company,
            is_staff=True,
        )
        _, agent = self._make_agent("kyc-agent@example.com", "kyc-agent")
        verification = agent.verifications.create(
            document_type="license",
            document_file=SimpleUploadedFile("license.pdf", b"fake-pdf", content_type="application/pdf"),
        )

        approve_agent_kyc(agent, admin=admin_user, remarks="Looks good")
        agent.refresh_from_db()
        verification.refresh_from_db()
        self.assertEqual(agent.kyc_status, "verified")
        self.assertIsNotNone(agent.kyc_verified_at)
        self.assertEqual(verification.status, verification.Status.APPROVED)
        self.assertEqual(verification.verified_by, admin_user)

        reject_agent_kyc(agent, admin=admin_user, remarks="Document mismatch")
        agent.refresh_from_db()
        verification.refresh_from_db()
        self.assertEqual(agent.kyc_status, "rejected")
        self.assertEqual(verification.status, verification.Status.REJECTED)

    def test_agent_transfer_reassigns_leads_and_deals(self):
        admin_user = User.objects.create_user(
            email="transfer-admin@example.com",
            username="transfer-admin",
            mobile="9222222222",
            password="Admin@123",
            role=SaaSRole.SUPER_ADMIN,
            company=self.company,
            is_staff=True,
        )
        old_user, old_agent = self._make_agent("old-agent@example.com", "old-agent")
        new_user, new_agent = self._make_agent("new-agent@example.com", "new-agent")
        lead = Lead.objects.create(
            company=self.company,
            name="Transfer Lead",
            mobile="9999911111",
            assigned_agent=old_agent,
            assigned_to=old_user,
        )
        deal = Deal.objects.create(company=self.company, lead=lead, agent=old_agent)

        transfer = perform_agent_transfer(
            old_agent=old_agent,
            new_agent=new_agent,
            transferred_by=admin_user,
            transfer_type="both",
            reason="Team rebalancing",
        )

        lead.refresh_from_db()
        deal.refresh_from_db()
        self.assertEqual(lead.assigned_agent, new_agent)
        self.assertEqual(deal.agent, new_agent)
        self.assertEqual(transfer.reassigned_leads, 1)
        self.assertEqual(transfer.reassigned_deals, 1)
        self.assertTrue(AgentTransfer.objects.filter(pk=transfer.pk).exists())
