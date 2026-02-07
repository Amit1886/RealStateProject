from billing.services import user_has_feature
from core_settings.models import FeatureSettings, SaaSSettings, ModuleSettings


def get_company(user):
    try:
        return user.userprofile.company
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

    # Check if feature is enabled in system (fallback allow if feature not defined)
    if FeatureSettings.objects.filter(feature=feature_name).exists():
        if not FeatureSettings.objects.filter(feature=feature_name, enabled=True).exists():
            return False

    # Check if plan has this feature
    return user_has_feature(user, feature_name)


def has_module(user, module_name):
    # Super admin
    if user.is_superuser:
        return True

    module = ModuleSettings.objects.filter(module=module_name, enabled=True).first()
    if not module:
        return False

    return True
