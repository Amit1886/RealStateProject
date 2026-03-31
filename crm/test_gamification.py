from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from agents.models import Agent
from crm.models import AgentScore
from crm.performance import sync_agent_score
from leads.models import Lead
from saas_core.models import Company


@override_settings(DISABLE_CELERY=True)
class GamificationApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(name="Gamification Realty")
        self.admin = User.objects.create_user(
            email="gamify-admin@example.com",
            username="gamify-admin",
            mobile="9000000801",
            password="Admin@123",
            role="super_admin",
            company=self.company,
            is_staff=True,
        )
        self.agent_user = User.objects.create_user(
            email="leader-agent@example.com",
            username="leader-agent",
            mobile="9000000802",
            password="Agent@123",
            role="agent",
            company=self.company,
        )
        self.agent = self.agent_user.agent_profile
        self.agent.name = "Leader Agent"
        self.agent.phone = self.agent_user.mobile
        self.agent.approval_status = Agent.ApprovalStatus.APPROVED
        self.agent.save()

        Lead.objects.create(
            company=self.company,
            created_by=self.admin,
            name="Score Lead 1",
            mobile="9999900301",
            assigned_agent=self.agent,
            assigned_to=self.agent_user,
        )
        Lead.objects.create(
            company=self.company,
            created_by=self.admin,
            name="Score Lead 2",
            mobile="9999900302",
            assigned_agent=self.agent,
            assigned_to=self.agent_user,
            status=Lead.Status.CONVERTED,
            stage=Lead.Stage.CONVERTED,
        )
        sync_agent_score(self.agent)

    def test_leaderboard_api_returns_agent_scores(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("api-leaderboard"), {"days": 30}, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["results"])
        self.assertEqual(response.json()["results"][0]["agent_id"], self.agent.id)

    def test_agent_stats_api_returns_gamification_snapshot(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("api-agent-stats"), {"agent_id": self.agent.id, "days": 30}, secure=True)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["agent_id"], self.agent.id)
        self.assertGreaterEqual(data["points"], 0)
        self.assertTrue(AgentScore.objects.filter(agent=self.agent).exists())
