from django.apps import apps as django_apps
from django.urls import include, path
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([IsAdminUser])
def addons_health(request):
    return Response(
        {
            "status": "ok",
            "message": "Addon platform is active.",
            "path_prefix": "/addons/",
        }
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def addon_not_installed(request, addon_key: str):
    return Response(
        {"detail": f"Addon '{addon_key}' is not enabled (missing from INSTALLED_APPS)."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _maybe_include(*, url_prefix: str, addon_key: str, app_path: str, urlconf: str, namespace: str):
    if django_apps.is_installed(app_path):
        return path(url_prefix, include((urlconf, namespace), namespace=namespace))
    return path(url_prefix, addon_not_installed, {"addon_key": addon_key})


urlpatterns = [path("addons/health/", addons_health, name="addons_health")]

urlpatterns += [
    _maybe_include(
        url_prefix="addons/demo_center/",
        addon_key="demo_center",
        app_path="addons.demo_center",
        urlconf="addons.demo_center.urls",
        namespace="demo_center",
    ),
    _maybe_include(
        url_prefix="demo/",
        addon_key="demo_center",
        app_path="addons.demo_center",
        urlconf="addons.demo_center.urls",
        namespace="demo_center_public",
    ),
    _maybe_include(
        url_prefix="addons/autopilot/",
        addon_key="autopilot_engine",
        app_path="addons.autopilot_engine",
        urlconf="addons.autopilot_engine.urls",
        namespace="autopilot_engine",
    ),
    _maybe_include(
        url_prefix="addons/ai-call/",
        addon_key="ai_call_assistant",
        app_path="addons.ai_call_assistant",
        urlconf="addons.ai_call_assistant.urls",
        namespace="ai_call_assistant",
    ),
    _maybe_include(
        url_prefix="addons/marketing/",
        addon_key="marketing_autopilot",
        app_path="addons.marketing_autopilot",
        urlconf="addons.marketing_autopilot.urls",
        namespace="marketing_autopilot",
    ),
    _maybe_include(
        url_prefix="addons/ads/",
        addon_key="ads_manager",
        app_path="addons.ads_manager",
        urlconf="addons.ads_manager.urls",
        namespace="ads_manager",
    ),
    _maybe_include(
        url_prefix="addons/ecommerce/",
        addon_key="ecommerce_engine",
        app_path="addons.ecommerce_engine",
        urlconf="addons.ecommerce_engine.urls",
        namespace="ecommerce_engine",
    ),
    _maybe_include(
        url_prefix="addons/courier/",
        addon_key="courier_integration",
        app_path="addons.courier_integration",
        urlconf="addons.courier_integration.urls",
        namespace="courier_integration",
    ),
    _maybe_include(
        url_prefix="addons/transport/",
        addon_key="transport_management",
        app_path="addons.transport_management",
        urlconf="addons.transport_management.urls",
        namespace="transport_management",
    ),
    _maybe_include(
        url_prefix="addons/warehouse-plus/",
        addon_key="warehouse_plus",
        app_path="addons.warehouse_plus",
        urlconf="addons.warehouse_plus.urls",
        namespace="warehouse_plus",
    ),
    _maybe_include(
        url_prefix="addons/hr/",
        addon_key="hr_autopilot",
        app_path="addons.hr_autopilot",
        urlconf="addons.hr_autopilot.urls",
        namespace="hr_autopilot",
    ),
    _maybe_include(
        url_prefix="addons/accounting/",
        addon_key="accounting_upgrade",
        app_path="addons.accounting_upgrade",
        urlconf="addons.accounting_upgrade.urls",
        namespace="accounting_upgrade",
    ),
    _maybe_include(
        url_prefix="addons/banking/",
        addon_key="banking_automation",
        app_path="addons.banking_automation",
        urlconf="addons.banking_automation.urls",
        namespace="banking_automation",
    ),
    _maybe_include(
        url_prefix="addons/analytics-ai/",
        addon_key="analytics_ai",
        app_path="addons.analytics_ai",
        urlconf="addons.analytics_ai.urls",
        namespace="analytics_ai",
    ),
]
