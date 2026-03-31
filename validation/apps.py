from django.apps import AppConfig


class ValidationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "validation"
    verbose_name = "Smart Alerts"

    def ready(self):
        try:
            from validation import signals  # noqa: F401
        except Exception:
            # Smart alerts must never break app boot.
            pass

