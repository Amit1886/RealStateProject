from django.apps import AppConfig


class SMSCenterConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sms_center"
    verbose_name = "SMS Center"

    def ready(self) -> None:
        # Register signal handlers.
        from . import signals  # noqa: F401

