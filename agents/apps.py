from django.apps import AppConfig


class AgentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "agents"
    verbose_name = "Agents"

    def ready(self):
        # Import signal handlers for agent auto-provisioning and metrics updates.
        from . import signals  # noqa: F401
