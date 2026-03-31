from django.apps import AppConfig


class PlanFeatureSyncConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "addons.plan_feature_sync"
    verbose_name = "Addon: Plan -> Feature Sync"

    def ready(self):
        # Register signals (kept in addon to avoid touching billing/core apps).
        try:
            from . import signals  # noqa: F401
        except Exception as exc:
            print(f"[plan_feature_sync] signals skipped: {exc}")
