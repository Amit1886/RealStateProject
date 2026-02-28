from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Grant a testing user full plan permissions + all features enabled."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="Demotest3")
        parser.add_argument("--plan-name", default="TestingFull")

    @transaction.atomic
    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model

        from billing.models import FeatureRegistry, Plan, PlanFeature, Subscription
        from billing.services import sync_feature_registry

        username = options["username"]
        plan_name = options["plan_name"]

        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if not user:
            raise CommandError(f"User not found: {username}")

        # Ensure feature registry rows exist.
        sync_feature_registry()

        plan, _ = Plan.objects.get_or_create(
            name=plan_name,
            defaults={
                "price": 0,
                "price_monthly": 0,
                "price_yearly": 0,
                "trial_days": 0,
                "active": True,
            },
        )
        if not plan.active:
            plan.active = True
            plan.save(update_fields=["active", "updated_at"])

        perms = plan.get_permissions()
        # Flip all boolean permission fields ON.
        bool_fields = [
            "allow_dashboard",
            "allow_reports",
            "allow_pdf_export",
            "allow_excel_export",
            "allow_add_party",
            "allow_edit_party",
            "allow_delete_party",
            "allow_add_transaction",
            "allow_edit_transaction",
            "allow_delete_transaction",
            "allow_bulk_transaction",
            "allow_commerce",
            "allow_warehouse",
            "allow_orders",
            "allow_inventory",
            "allow_whatsapp",
            "allow_sms",
            "allow_email",
            "allow_settings",
            "allow_users",
            "allow_api_access",
            "allow_ledger",
            "allow_credit_report",
            "allow_analytics",
        ]
        for field in bool_fields:
            if hasattr(perms, field):
                setattr(perms, field, True)
        if hasattr(perms, "max_parties"):
            perms.max_parties = 100000
        perms.save()

        # Enable every active FeatureRegistry key for this plan.
        for feature in FeatureRegistry.objects.filter(active=True):
            PlanFeature.objects.update_or_create(
                plan=plan,
                feature=feature,
                defaults={"enabled": True},
            )

        # Ensure user has an active subscription with this plan.
        sub = (
            Subscription.objects.filter(user=user)
            .order_by("-created_at")
            .first()
        )
        if sub:
            sub.plan = plan
            sub.status = "active"
            sub.save(update_fields=["plan", "status"])
        else:
            Subscription.objects.create(user=user, plan=plan, status="active")

        # Also sync khataapp profile plan, because parts of the UI display it.
        try:
            from khataapp.models import UserProfile as KhataProfile

            profile = KhataProfile.objects.filter(user=user).first()
            if profile:
                profile.plan = plan
                profile.save(update_fields=["plan", "updated_at"])
        except Exception:
            pass

        self.stdout.write(self.style.SUCCESS(f"Granted full testing access to {username} via plan '{plan_name}'"))
