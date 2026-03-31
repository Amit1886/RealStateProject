from django.apps import AppConfig


class APIIntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api_integrations"
    verbose_name = "API Integrations"

    def ready(self):
        # Placeholder for future signal hooks (provider credential refresh, etc.)
        return
