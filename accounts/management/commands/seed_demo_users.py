from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from billing.services import ensure_free_plan, get_effective_plan
from core_settings.models import CompanySettings
from accounts.models import UserProfile as AccountsUserProfile
from accounts.models import UserProfile


class Command(BaseCommand):
    help = "Create demo users for QA (Demotest3 + Superadmin)"

    def handle(self, *args, **options):
        User = get_user_model()

        company, _ = CompanySettings.objects.get_or_create(company_name="JaisTech Demo Company")

        # Standard ERP role groups (used by role gating)
        role_groups = {}
        for name in ["Super Admin", "Admin", "Agent", "User"]:
            role_groups[name], _ = Group.objects.get_or_create(name=name)

        # Superadmin
        super_username = "Superadmin"
        super_password = "Admin@123"
        super_email = "superadmin@example.com"
        superuser, created = User.objects.get_or_create(
            username=super_username,
            defaults={"email": super_email, "is_staff": True, "is_superuser": True, "is_active": True},
        )
        if created:
            superuser.set_password(super_password)
            superuser.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS("OK: Superadmin created"))
        else:
            if not superuser.is_superuser:
                superuser.is_staff = True
                superuser.is_superuser = True
                superuser.is_active = True
                superuser.save(update_fields=["is_staff", "is_superuser", "is_active"])
            self.stdout.write("INFO: Superadmin already exists")

        UserProfile.objects.get_or_create(
            user=superuser,
            defaults={"full_name": "Super Admin", "business_name": "KhataPro HQ", "created_from": "admin"},
        )
        AccountsUserProfile.objects.get_or_create(
            user=superuser,
            defaults={
                "company": company,
                "full_name": "Super Admin",
                "mobile": "9999999999",
                "business_name": "KhataPro HQ",
                "plan": get_effective_plan(superuser),
            },
        )
        superuser.groups.add(role_groups["Super Admin"])

        # Demo user
        demo_username = "Demotest3"
        demo_password = "Demo@123"
        demo_email = "demotest3@example.com"
        demo_user, demo_created = User.objects.get_or_create(
            username=demo_username,
            defaults={"email": demo_email, "is_active": True},
        )
        if demo_created:
            demo_user.set_password(demo_password)
            demo_user.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS("OK: Demotest3 created"))
        else:
            self.stdout.write("INFO: Demotest3 already exists")

        ensure_free_plan(demo_user)
        plan = get_effective_plan(demo_user)
        profile, _ = UserProfile.objects.get_or_create(
            user=demo_user,
            defaults={"full_name": "Demo Test 3", "business_name": "Demo Business", "created_from": "admin"},
        )
        if plan and profile.plan_id != plan.id:
            profile.plan = plan
            profile.save(update_fields=["plan"])

        AccountsUserProfile.objects.get_or_create(
            user=demo_user,
            defaults={
                "company": company,
                "full_name": "Demo Test 3",
                "mobile": "9999999999",
                "business_name": "Demo Business",
                "plan": plan,
            },
        )
        demo_user.groups.add(role_groups["Admin"])

        self.stdout.write("Credentials:")
        self.stdout.write(f"  - Superadmin / {super_password}")
        self.stdout.write(f"  - Demotest3 / {demo_password}")
