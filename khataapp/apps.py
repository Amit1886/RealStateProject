from django.apps import AppConfig

class KhataappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'khataapp'

    def ready(self):
        import khataapp.signals