import os
import django
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'khatapro.settings')
django.setup()

from django.contrib.auth import get_user_model
from billing.models import Subscription, FeatureRegistry, UserFeatureOverride, PlanFeature
from billing.services import user_has_feature, get_active_subscription

User = get_user_model()

username = 'Demotest3'
user = User.objects.filter(username=username).first()

if not user:
    print(f"User {username} not found!")
    sys.exit(1)

print(f"\n=== Debug Info for {user.username} ===\n")

# Check subscription
sub = get_active_subscription(user)
print(f"Active Subscription: {sub}")
if sub:
    print(f"  Plan: {sub.plan}")
    print(f"  Status: {sub.status}")
    print(f"  Start Date: {sub.start_date}")

# Check if superuser
print(f"Is Superuser: {user.is_superuser}")

# Check specific features
features_to_check = [
    'settings.advanced',
    'commerce.orders',
    'commerce.suppliers',
    'commerce.inventory',
]

print(f"\n--- Feature Access ---")
for feat_key in features_to_check:
    has_it = user_has_feature(user, feat_key)
    print(f"{feat_key}: {has_it}")

# Check user overrides
print(f"\n--- User Feature Overrides ---")
overrides = UserFeatureOverride.objects.filter(user=user)
for override in overrides:
    print(f"  {override.feature.key}: {override.is_enabled}")

# Check plan features if subscribed
if sub and sub.plan:
    print(f"\n--- Plan Features for {sub.plan.name} ---")
    plan_features = PlanFeature.objects.filter(plan=sub.plan, enabled=True)
    for pf in plan_features[:10]:  # Show first 10
        print(f"  {pf.feature.key}: enabled")
    print(f"  ... and {plan_features.count()} total enabled features")
