import logging
from typing import Any, Dict

from django.apps import apps
from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)


def get_addon_default_flags() -> Dict[str, bool]:
    return {
        "autopilot_engine": True,
        "ai_call_assistant": False,
        "marketing_autopilot": False,
        "ads_manager": False,
        "ecommerce_engine": False,
        "courier_integration": False,
        "transport_management": False,
        "warehouse_plus": False,
        "hr_autopilot": False,
        "accounting_upgrade": False,
        "banking_automation": False,
        "analytics_ai": False,
    }


def get_runtime_flag(name: str, fallback: bool = False) -> bool:
    env_flags = getattr(settings, "ADDON_FEATURE_FLAGS", {})
    if name in env_flags:
        return bool(env_flags[name])

    if apps.is_installed("addons.autopilot_engine"):
        try:
            from addons.autopilot_engine.models import FeatureToggle

            toggle = FeatureToggle.objects.filter(key=name, enabled=True).first()
            if toggle:
                return True
        except (OperationalError, ProgrammingError):  # tables not ready yet
            return fallback
    return fallback


def safe_log(event: str, payload: Dict[str, Any]) -> None:
    logger.info("addons.event.%s", event, extra={"payload": payload})
