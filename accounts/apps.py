from django.apps import AppConfig
import os


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        # ---- load signals ----
        import accounts.signals

        # ---- optional auto superuser create (Render free workaround) ----
        if os.environ.get("AUTO_CREATE_SUPERUSER", "false").lower() != "true":
            return

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
            email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
            password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "Admin@123")

            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                )
                print("✅ Auto superuser created")

        except Exception as e:
            print("⚠️ Superuser auto-create skipped:", e)
