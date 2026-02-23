from django.apps import AppConfig


class SystemModeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'system_mode'
    verbose_name = "System Mode Controller"
