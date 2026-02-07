from django import template
from billing.services import user_has_feature

register = template.Library()


@register.simple_tag(takes_context=True)
def feature_allowed(context, feature_key):
    user = context.get("request").user
    if not user or not user.is_authenticated:
        return False
    return user_has_feature(user, feature_key)
