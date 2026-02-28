import os
import sys
import django

# ensure project root on path
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "khatapro.settings")
django.setup()

from django.contrib.auth import get_user_model
from billing.models import Plan, PlanFeature, FeatureRegistry
from billing.services import sync_feature_registry, upgrade_subscription
from billing.models import PlanPermissions, UserFeatureOverride
from khataapp.models import UserProfile as KhataUserProfile

User = get_user_model()

username = "Demotest3"

user = User.objects.filter(username=username).first()
if not user:
    print(f"User {username} not found. Creating...")
    user = User.objects.create_user(username=username, password="demo1234")

# Ensure predictable demo credentials + identifier options for login screen (email/mobile).
user.set_password("demo1234")
if not user.email:
    user.email = "demotest3@example.com"
user.is_active = True
user.save(update_fields=["password", "email", "is_active"])

profile, _ = KhataUserProfile.objects.get_or_create(user=user)
if not profile.mobile:
    profile.mobile = f"900000{user.id:04d}"
if not profile.full_name:
    profile.full_name = "Demo Test 3"
profile.save(update_fields=["mobile", "full_name"])

print(f"Using user: {user.username} (id={user.id})")

# ensure feature registry exists
sync_feature_registry()

# find or create Premium plan
plan, created = Plan.objects.get_or_create(name="Premium", defaults={"price": 999.00, "price_monthly": 999.00, "price_yearly": 999.00, "active": True})
if created:
    print("Created Premium plan")
else:
    print("Found Premium plan")

# enable all features for premium plan
features = FeatureRegistry.objects.filter(active=True)
for feat in features:
    pf, _ = PlanFeature.objects.get_or_create(plan=plan, feature=feat)
    if not pf.enabled:
        pf.enabled = True
        pf.save()

# ensure PlanPermissions toggles are permissive
perm = getattr(plan, "permissions", None)
if not perm:
    perm = PlanPermissions.objects.create(plan=plan)

perm.allow_settings = True
perm.allow_commerce = True
perm.allow_orders = True
perm.allow_inventory = True
perm.allow_whatsapp = True
perm.allow_email = True
perm.allow_api_access = True
perm.allow_users = True
perm.allow_reports = True
perm.save()

# upgrade user's subscription
upgrade_subscription(user, plan)
print(f"Upgraded {user.username} to plan {plan.name}")

# add explicit user overrides for quick effect (settings + orders)
for key in ("settings.advanced", "commerce.orders"):
    feat = FeatureRegistry.objects.filter(key=key).first()
    if feat:
        uo, _ = UserFeatureOverride.objects.get_or_create(user=user, feature=feat)
        uo.is_enabled = True
        uo.save()

print("Feature overrides applied for settings and orders.")
print("Done. You can now log in as Demotest3 and visit /settings/ and POS UI.")
