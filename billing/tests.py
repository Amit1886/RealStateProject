from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from billing.models import FeatureRegistry, Plan, PlanFeature, Subscription
from billing.services import get_effective_plan, user_has_feature
from django.contrib.auth import get_user_model
from khataapp.models import UserProfile


class GroupPlanPermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user1@example.com",
            password="pass12345",
            username="user1",
            mobile="9990001111",
        )
        UserProfile.objects.create(user=self.user)

        self.group_basic = Group.objects.create(name="basic-group")
        self.group_pro = Group.objects.create(name="pro-group")

        self.plan_basic = Plan.objects.create(name="Basic", price=0, price_monthly=0, price_yearly=0, trial_days=0, active=True)
        self.plan_pro = Plan.objects.create(name="Pro", price=999, price_monthly=999, price_yearly=9999, trial_days=0, active=True)

        self.plan_basic.groups.add(self.group_basic)
        self.plan_pro.groups.add(self.group_pro)

    def test_effective_plan_from_group_when_no_subscription_or_profile_plan(self):
        profile = self.user.khata_profile
        profile.plan = None
        profile.save(update_fields=["plan"])

        self.user.groups.add(self.group_pro)

        plan = get_effective_plan(self.user)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.id, self.plan_pro.id)

    def test_effective_plan_prefers_active_subscription(self):
        self.user.groups.add(self.group_pro)

        Subscription.objects.create(user=self.user, plan=self.plan_basic, status="active", start_date=timezone.now())

        plan = get_effective_plan(self.user)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.id, self.plan_basic.id)

    def test_user_has_feature_uses_group_plan(self):
        profile = self.user.khata_profile
        profile.plan = None
        profile.save(update_fields=["plan"])
        self.user.groups.add(self.group_pro)

        feature = FeatureRegistry.objects.create(key="custom.group_feature", label="Group Feature", group="Test", active=True)
        PlanFeature.objects.create(plan=self.plan_pro, feature=feature, enabled=True)

        self.assertTrue(user_has_feature(self.user, "custom.group_feature"))
