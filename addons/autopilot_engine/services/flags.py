from __future__ import annotations

import os
from typing import Optional

from django.db.utils import OperationalError, ProgrammingError


def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


def is_enabled(key: str, default: bool = False) -> bool:
    if env_bool(f"ADDON_{key.upper()}_ENABLED", default):
        return True

    try:
        from addons.autopilot_engine.models import FeatureToggle

        toggle: Optional[FeatureToggle] = FeatureToggle.objects.filter(key=key).first()
        if toggle is None:
            return default
        return bool(toggle.enabled)
    except (OperationalError, ProgrammingError):
        return default
