from django.apps import AppConfig


class AutopilotEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "addons.autopilot_engine"
    verbose_name = "Addons Autopilot Engine"

    def ready(self):
        from . import signals  # noqa: F401
        from . import listeners  # noqa: F401
        from .integrations import legacy_events  # noqa: F401
