from django.apps import AppConfig


class EcommerceEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "addons.ecommerce_engine"
    verbose_name = "Addons Ecommerce Engine"

    def ready(self):
        from . import signals  # noqa: F401
