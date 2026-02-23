from django.apps import AppConfig


class AdsManagerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "addons.ads_manager"
    verbose_name = "Addons Ads Manager"

    def ready(self):
        from . import signals  # noqa: F401
