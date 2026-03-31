# billing/apps.py
from django.apps import AppConfig

class BillingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "billing"

    def ready(self):
        # signals ko yahan import karna zaroori hai taki wo register ho jayein
        try:
            import billing.signals  # noqa: F401
        except Exception as exc:
            print(f"[billing] signals skipped: {exc}")
