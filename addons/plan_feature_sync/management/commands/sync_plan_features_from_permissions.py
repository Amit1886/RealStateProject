from django.core.management.base import BaseCommand

from billing.models import Plan, PlanPermissions

from addons.plan_feature_sync.signals import sync_plan_features_from_permissions


class Command(BaseCommand):
    help = "Sync billing.PlanFeature.enabled based on billing.PlanPermissions for one plan or all plans."

    def add_arguments(self, parser):
        parser.add_argument("--plan-id", type=int, default=None, help="Plan ID to sync")
        parser.add_argument("--plan-name", type=str, default=None, help="Plan name to sync")
        parser.add_argument("--all", action="store_true", help="Sync all active plans")

    def handle(self, *args, **options):
        plan_id = options.get("plan_id")
        plan_name = options.get("plan_name")
        sync_all = bool(options.get("all"))

        if not sync_all and not plan_id and not plan_name:
            self.stderr.write("Provide --plan-id, --plan-name, or --all.")
            return 2

        qs = Plan.objects.all()
        if sync_all:
            qs = qs.filter(active=True)
        if plan_id:
            qs = qs.filter(id=plan_id)
        if plan_name:
            qs = qs.filter(name=plan_name)

        plans = list(qs)
        if not plans:
            self.stderr.write("No matching plans found.")
            return 1

        total_updates = 0
        for plan in plans:
            perms, _ = PlanPermissions.objects.get_or_create(plan=plan)
            updated = sync_plan_features_from_permissions(perms)
            total_updates += updated
            self.stdout.write(f"{plan.id}:{plan.name} -> synced {updated} feature keys")

        self.stdout.write(f"Done. Total synced keys: {total_updates}")
        return 0

