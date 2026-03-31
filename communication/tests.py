from rest_framework.test import APITestCase

from accounts.models import SaaSRole, User
from communication.models import EmailLog, SMSLog
from notifications.models import Notification


class CommunicationEventTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="comm-agent@example.com",
            username="comm-agent",
            mobile="9000000002",
            password="Agent@123",
            role=SaaSRole.AGENT,
        )
        self.client.force_authenticate(self.user)

    def test_event_endpoint_creates_logs(self):
        response = self.client.post(
            "/api/v1/communication/events/",
            {
                "title": "New lead assigned",
                "body": "Lead #12 routed to you",
                "channels": ["in_app", "email", "sms"],
                "email": self.user.email,
                "phone": self.user.mobile,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        self.assertEqual(EmailLog.objects.filter(recipient=self.user.email).count(), 1)
        self.assertEqual(SMSLog.objects.filter(phone=self.user.mobile).count(), 1)
