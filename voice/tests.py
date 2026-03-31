from django.test import TestCase

from accounts.models import SaaSRole, User
from agents.models import Agent
from leads.models import Lead
from voice.models import VoiceCall
from voice.services import apply_voice_qualification


class VoiceQualificationTests(TestCase):
    def test_apply_voice_qualification_updates_lead(self):
        user = User.objects.create_user(
            email="voice-agent@example.com",
            username="voice-agent",
            mobile="9100000004",
            password="Agent@123",
            role=SaaSRole.AGENT,
        )
        agent = Agent.objects.get(user=user)
        agent.name = "Voice Agent"
        agent.city = "Basti"
        agent.district = "Basti"
        agent.state = "Uttar Pradesh"
        agent.pin_code = "272001"
        agent.approval_status = Agent.ApprovalStatus.APPROVED
        agent.save()
        lead = Lead.objects.create(name="Voice Lead", mobile="9100000005", city="Basti", district="Basti", state="Uttar Pradesh")
        call = VoiceCall.objects.create(lead=lead, trigger=VoiceCall.Trigger.MANUAL)

        apply_voice_qualification(
            call,
            transcript="I want to buy in Basti with budget 30 lakh",
            responses={
                "buy_or_sell": "buy",
                "location": "Basti",
                "budget": "3000000",
                "interested": "yes",
            },
        )

        lead.refresh_from_db()
        call.refresh_from_db()
        self.assertTrue(call.qualified)
        self.assertEqual(call.qualification_status, "qualified")
        self.assertEqual(str(lead.budget), "3000000.00")
        self.assertEqual(lead.status, Lead.Status.QUALIFIED)
