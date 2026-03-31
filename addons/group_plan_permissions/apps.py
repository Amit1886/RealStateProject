from django.apps import AppConfig


class GroupPlanPermissionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "addons.group_plan_permissions"
    verbose_name = "Addons Group Plan Permissions"

    def ready(self):
        try:
            from . import signals  # noqa: F401
        except Exception as exc:
            print(f"[group_plan_permissions] signals skipped: {exc}")
