from django.apps import AppConfig


class DealsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "deals"
    verbose_name = "Deals"

    def ready(self):
        from . import signals  # noqa
