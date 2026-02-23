from django.apps import AppConfig


class AiCallAssistantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "addons.ai_call_assistant"
    verbose_name = "Addons AI Call Assistant"

    def ready(self):
        from . import signals  # noqa: F401
