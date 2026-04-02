from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from billing.models import FeatureRegistry, Plan, UserFeatureOverride
from accounts.models import UserProfile


class FeatureControlTowerTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="tower-admin@example.com",
            password="pass12345",
            username="tower-admin",
            mobile="9000000900",
            is_staff=True,
        )
        self.user = User.objects.create_user(
            email="tower-user@example.com",
            password="pass12345",
            username="tower-user",
            mobile="9000000901",
        )
        UserProfile.objects.create(user=self.user)
        self.plan = Plan.objects.create(
            name="Tower Plan",
            price=0,
            price_monthly=0,
            price_yearly=0,
            trial_days=0,
            active=True,
        )
        self.feature = FeatureRegistry.objects.create(
            key="tower.feature",
            label="Tower Feature",
            group="Tower",
            active=True,
        )
        self.client.force_login(self.admin)

    def test_feature_control_tower_renders(self):
        resp = self.client.get(reverse("core_settings:feature_control_tower"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Feature Control Tower")
        self.assertContains(resp, "Enable Visible")
        self.assertContains(resp, "Disable Visible")
        self.assertContains(resp, "Search plan")
        self.assertContains(resp, "Search user")
        self.assertContains(resp, "Plan Active")
        self.assertContains(resp, "User Active")
        self.assertContains(resp, "Registry Active")
        self.assertContains(resp, "Selected Plan")
        self.assertContains(resp, "Selected User")
        self.assertContains(resp, "Tower Plan")
        self.assertContains(resp, "tower-user@example.com")
        self.assertContains(resp, "Jump to Plan")
        self.assertContains(resp, "Jump to User")
        self.assertContains(resp, "Plan Enabled")
        self.assertContains(resp, "Override On")

    def test_plan_permissions_can_be_saved_from_tower(self):
        resp = self.client.post(
            reverse("core_settings:feature_control_tower"),
            {
                "action": "plan",
                "plan_id": self.plan.id,
                "allow_dashboard": "on",
                "allow_reports": "on",
                "max_parties": "321",
            },
        )
        self.assertEqual(resp.status_code, 302)
        perms = self.plan.get_permissions()
        self.assertTrue(perms.allow_dashboard)
        self.assertTrue(perms.allow_reports)
        self.assertEqual(perms.max_parties, 321)

    def test_user_override_can_force_feature_off(self):
        resp = self.client.post(
            reverse("core_settings:feature_control_tower"),
            {
                "action": "user",
                "user_id": self.user.id,
                f"override_{self.feature.id}": "disabled",
            },
        )
        self.assertEqual(resp.status_code, 302)
        override = UserFeatureOverride.objects.get(user=self.user, feature=self.feature)
        self.assertFalse(override.is_enabled)
