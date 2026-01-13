from billing.models import Subscription
from core_settings.models import FeatureSettings, SaaSSettings, ModuleSettings


def get_company(user):
    try:
        return user.userprofile.company
    except:
        return None


def get_active_subscription(user):
    try:
        return Subscription.objects.get(company=get_company(user), active=True)
    except:
        return None


def has_feature(user, feature_name):
    # Super admin always allowed
    if user.is_superuser:
        return True

    # SaaS switch
    saas = SaaSSettings.objects.first()
    if saas and not saas.enable_subscription:
        return True

    sub = get_active_subscription(user)
    if not sub:
        return False

    # Check if feature is enabled in system
    if not FeatureSettings.objects.filter(feature=feature_name, enabled=True).exists():
        return False

    # Check if plan has this feature
    return sub.plan.features.filter(feature=feature_name).exists()


def has_module(user, module_name):
    # Super admin
    if user.is_superuser:
        return True

    module = ModuleSettings.objects.filter(module=module_name, enabled=True).first()
    if not module:
        return False

    return True
