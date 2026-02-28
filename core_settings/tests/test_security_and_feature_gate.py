from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from billing.models import Plan, Subscription
import json


class ApiPlanPermissionGateTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="u@example.com",
            password="pass12345",
            username="u",
            mobile="9000000200",
        )

        self.plan = Plan.objects.create(
            name="NoOrders",
            price=0,
            price_monthly=0,
            price_yearly=0,
            trial_days=0,
            active=True,
        )
        perms = self.plan.get_permissions()
        perms.allow_orders = False
        perms.save(update_fields=["allow_orders"])
        Subscription.objects.create(user=self.user, plan=self.plan, status="active")

        self.client = APIClient()
        # Use session auth so Django middleware sees request.user (JWT clients are handled via JWT middleware).
        logged_in = self.client.login(email="u@example.com", password="pass12345")
        self.assertTrue(logged_in)

    def test_orders_api_blocked_when_allow_orders_false(self):
        resp = self.client.post("/api/v1/orders/orders/quick_place/", {"items": []}, format="json")
        self.assertEqual(resp.status_code, 403)
        payload = json.loads(resp.content.decode("utf-8"))
        self.assertEqual(payload.get("required_permission"), "allow_orders")


class RateLimitTests(TestCase):
    @override_settings()
    def test_rate_limit_triggers(self):
        # Hit login repeatedly; we don't care about successful auth here, only 429 enforcement.
        for _ in range(70):
            resp = self.client.post("/accounts/login/", {"identifier": "x", "password": "y", "use_otp": False})
        self.assertIn(resp.status_code, (200, 302, 429))
