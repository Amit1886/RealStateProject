from django.test import TestCase, override_settings
from django.utils import timezone
from unittest.mock import patch

from accounts.models import SaaSRole, User
from agents.models import Agent
from leads.models import Lead
from visits.models import GroupVisit, GroupVisitAttendance, SiteVisit
from saas_core.models import Company


@override_settings(VOICE_AI_ENABLED=False, DISABLE_CELERY=True)
class VisitBusinessCoreTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Visit Core Realty")
        self.user = User.objects.create_user(
            email="visit-agent@example.com",
            username="visit-agent",
            mobile="9333333333",
            password="Agent@123",
            role=SaaSRole.AGENT,
            company=self.company,
        )
        self.agent = self.user.agent_profile
        self.agent.name = "Visit Agent"
        self.agent.phone = self.user.mobile
        self.agent.approval_status = Agent.ApprovalStatus.APPROVED
        self.agent.save()
        self.lead = Lead.objects.create(
            company=self.company,
            name="Visit Lead",
            mobile="9999933333",
            assigned_agent=self.agent,
            assigned_to=self.user,
        )

    def test_group_visit_and_site_visit_flag(self):
        group_visit = GroupVisit.objects.create(
            agent=self.agent,
            visit_date=timezone.now(),
            location="Site A",
            created_by=self.user,
        )
        GroupVisitAttendance.objects.create(group_visit=group_visit, lead=self.lead, attendance_status="present")
        visit = SiteVisit.objects.create(
            lead=self.lead,
            agent=self.agent,
            group_visit=group_visit,
            visit_date=timezone.now(),
            location="Site A",
        )

        visit.refresh_from_db()
        self.assertTrue(visit.is_group_visit)
        self.assertEqual(group_visit.attendance_rows.count(), 1)
        self.assertEqual(group_visit.leads.count(), 1)

    @patch("visits.signals.send_whatsapp_or_notify")
    def test_no_show_increments_lead_penalty(self, mocked_notify):
        SiteVisit.objects.create(
            lead=self.lead,
            agent=self.agent,
            visit_date=timezone.now(),
            location="Site B",
            is_no_show=True,
        )

        self.lead.refresh_from_db()
        self.assertEqual(self.lead.no_show_count, 1)
        self.assertLess(self.lead.reliability_score, 100)
        mocked_notify.assert_called_once()
