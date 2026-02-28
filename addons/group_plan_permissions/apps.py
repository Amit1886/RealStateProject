from django.apps import AppConfig


class GroupPlanPermissionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "addons.group_plan_permissions"
    verbose_name = "Addons Group Plan Permissions"

    def ready(self):
        from . import signals  # noqa: F401
