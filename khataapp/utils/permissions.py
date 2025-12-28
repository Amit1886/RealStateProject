# khataapp/utils/permissions.py
from django.core.exceptions import ObjectDoesNotExist

def user_has_feature(user, feature_name):
    """
    Check if a user has access to a feature based on their plan.
    Returns True/False
    """
    try:
        profile = user.khata_profile  # OneToOne UserProfile
        plan = profile.plan
        if not plan:
            return False  # No plan, no features

        # Example: assuming Plan model has a JSONField/ListField 'features'
        if hasattr(plan, 'features'):
            return feature_name in plan.features
        else:
            # If no features defined, allow all for now
            return True

    except ObjectDoesNotExist:
        return False  # No profile, deny access
