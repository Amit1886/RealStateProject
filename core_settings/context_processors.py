import os
from django.conf import settings
from .models import UISettings, CompanySettings

def global_settings(request):
    is_local_base_url = bool(getattr(settings, "IS_LOCAL_BASE_URL", False))
    running_runserver = bool(getattr(settings, "RUNNING_RUNSERVER", False))
    desktop_mode = bool(getattr(settings, "DESKTOP_MODE", False))

    # When running locally (or desktop), prefer local vendor assets over CDN so UI works offline.
    use_local_vendor_assets = bool(desktop_mode or running_runserver or is_local_base_url)

    return {
        "ui": UISettings.objects.first(),
        "company": CompanySettings.objects.first(),
        "desktop_mode": desktop_mode,
        "desktop_app_version": (getattr(settings, "DESKTOP_APP_VERSION", "") or os.getenv("DESKTOP_APP_VERSION") or "0.0.0").strip(),
        "use_local_vendor_assets": use_local_vendor_assets,
        "is_local_base_url": is_local_base_url,
    }

def ui_settings(request):
    return {
        "ui": UISettings.objects.first()
    }
