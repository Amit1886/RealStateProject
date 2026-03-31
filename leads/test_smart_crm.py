import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from agents.models import Agent
from leads.models import Lead
from saas_core.models import Company


@override_settings(DISABLE_CELERY=True)
class SmartCrmLeadApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(name="Smart CRM Realty")
        self.admin = User.objects.create_user(
            email="smart-admin@example.com",
            username="smart-admin",
            mobile="9000000701",
            password="Admin@123",
            role="super_admin",
            company=self.company,
            is_staff=True,
        )
        self.agent1_user = User.objects.create_user(
            email="geo-agent1@example.com",
            username="geo-agent1",
            mobile="9000000702",
            password="Agent@123",
            role="agent",
            company=self.company,
        )
        self.agent2_user = User.objects.create_user(
            email="geo-agent2@example.com",
            username="geo-agent2",
            mobile="9000000703",
            password="Agent@123",
            role="agent",
            company=self.company,
        )
        self.agent1 = self.agent1_user.agent_profile
        self.agent1.name = "Nearby Agent"
        self.agent1.phone = self.agent1_user.mobile
        self.agent1.approval_status = Agent.ApprovalStatus.APPROVED
        self.agent1.current_latitude = 26.8467
        self.agent1.current_longitude = 80.9462
        self.agent1.assigned_location = {"city": "Lucknow"}
        self.agent1.current_location = {"lat": 26.8467, "lng": 80.9462}
        self.agent1.save()

        self.agent2 = self.agent2_user.agent_profile
        self.agent2.name = "Far Agent"
        self.agent2.phone = self.agent2_user.mobile
        self.agent2.approval_status = Agent.ApprovalStatus.APPROVED
        self.agent2.current_latitude = 28.6139
        self.agent2.current_longitude = 77.2090
        self.agent2.assigned_location = {"city": "Delhi"}
        self.agent2.current_location = {"lat": 28.6139, "lng": 77.2090}
        self.agent2.save()

    def test_geo_assign_endpoint_picks_nearest_agent(self):
        lead = Lead.objects.create(
            company=self.company,
            created_by=self.admin,
            name="Geo Lead",
            mobile="9999900200",
            city="Lucknow",
            state="Uttar Pradesh",
            geo_location={"lat": 26.85, "lng": 80.95},
            assigned_agent=self.agent2,
            assigned_to=self.agent2_user,
        )

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("api-assign-geo"),
            json.dumps({"lead_id": lead.id, "reason": "Geo test"}),
            content_type="application/json",
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        lead.refresh_from_db()
        self.assertEqual(lead.assigned_agent_id, self.agent1.id)
        self.assertTrue(lead.is_locked)
        self.assertEqual(lead.locked_by_id, self.agent1.id)

    def test_photo_to_lead_endpoint_can_preview_and_create(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("api-photo-to-lead"),
            json.dumps({"raw_text": "Rahul Sharma\nPhone: 9876543210\nEmail: rahul@example.com", "create_lead": "true"}),
            content_type="application/json",
            secure=True,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Lead.objects.filter(company=self.company, mobile="9876543210").count(), 1)

    def test_lock_and_unlock_endpoints_respect_admin_controls(self):
        lead = Lead.objects.create(
            company=self.company,
            created_by=self.admin,
            name="Locked Lead",
            mobile="9999900201",
            assigned_agent=self.agent1,
            assigned_to=self.agent1_user,
        )
        self.client.force_login(self.agent2_user)
        forbidden = self.client.post(reverse("api-lead-lock"), json.dumps({"lead_id": lead.id}), content_type="application/json", secure=True)
        self.assertEqual(forbidden.status_code, 403)

        self.client.force_login(self.admin)
        unlocked = self.client.post(
            reverse("api-lead-unlock"),
            json.dumps({"lead_id": lead.id, "reason": "Admin override"}),
            content_type="application/json",
            secure=True,
        )
        self.assertEqual(unlocked.status_code, 200)
        lead.refresh_from_db()
        self.assertFalse(lead.is_locked)
