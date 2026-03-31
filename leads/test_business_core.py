from datetime import datetime, timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import SaaSRole, User
from agents.models import Agent
from leads.models import Lead
from leads.pipeline import check_deadline_breach, refresh_stage_deadline
from saas_core.models import Company


@override_settings(VOICE_AI_ENABLED=False, DISABLE_CELERY=True)
class LeadBusinessCoreTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Core Realty")
        self.user = User.objects.create_user(
            email="agent-core@example.com",
            username="agent-core",
            mobile="9000000001",
            password="Agent@123",
            role=SaaSRole.AGENT,
            company=self.company,
        )
        self.agent = self.user.agent_profile
        self.agent.name = "Core Agent"
        self.agent.phone = self.user.mobile
        self.agent.approval_status = Agent.ApprovalStatus.APPROVED
        self.agent.save()

    def test_refresh_stage_deadline_sets_stage_specific_deadline(self):
        lead = Lead.objects.create(
            company=self.company,
            name="Deadline Lead",
            mobile="9999900001",
            assigned_agent=self.agent,
            assigned_to=self.user,
            stage=Lead.Stage.QUALIFIED,
        )

        when = timezone.make_aware(datetime(2026, 1, 1, 9, 0, 0))
        refresh_stage_deadline(lead, stage_changed_at=when)

        lead.refresh_from_db()
        self.assertEqual(lead.stage_updated_at, when)
        self.assertEqual(lead.stage_deadline, when + timedelta(days=2))
        self.assertFalse(lead.is_overdue)

    def test_check_deadline_breach_marks_overdue(self):
        lead = Lead.objects.create(
            company=self.company,
            name="Overdue Lead",
            mobile="9999900002",
            assigned_agent=self.agent,
            assigned_to=self.user,
            stage=Lead.Stage.NEGOTIATION,
        )
        past = timezone.now() - timedelta(days=2)
        Lead.objects.filter(pk=lead.pk).update(stage_deadline=past, is_overdue=False)

        breached = check_deadline_breach()

        lead.refresh_from_db()
        self.assertIn(lead.id, breached)
        self.assertTrue(lead.is_overdue)
