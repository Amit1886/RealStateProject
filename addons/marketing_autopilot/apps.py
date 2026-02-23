from django.apps import AppConfig


class MarketingAutopilotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "addons.marketing_autopilot"
    verbose_name = "Addons Marketing Autopilot"

    def ready(self):
        from . import signals  # noqa: F401
