from django.apps import AppConfig


class RewardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rewards"
    verbose_name = "Agent Rewards"

    def ready(self):
        from . import signals  # noqa: F401
