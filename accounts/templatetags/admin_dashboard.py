from django import template

from accounts.services.crm_dashboard import build_crm_dashboard_context


register = template.Library()


@register.simple_tag(takes_context=True)
def admin_crm_overview(context):
    request = context.get("request")
    user = getattr(request, "user", None)
    return build_crm_dashboard_context(user)
