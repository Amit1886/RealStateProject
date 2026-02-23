from django.apps import AppConfig


class HotfixesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "addons.hotfixes"
    verbose_name = "Addons Hotfixes"

    def ready(self):
        from .patches import accounts_dashboard  # noqa: F401

