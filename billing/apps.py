# billing/apps.py
from django.apps import AppConfig

class BillingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "billing"

    def ready(self):
        # signals ko yahan import karna zaroori hai taki wo register ho jayein
        import billing.signals
