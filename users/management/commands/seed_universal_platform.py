from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from commission.models import CommissionRule
from products.models import Category, Product, WarehouseInventory
from users.models import UserProfileExt, UserRole
from warehouse.models import Warehouse


class Command(BaseCommand):
    help = "Seed universal billing + POS + quick commerce sample data"

    def handle(self, *args, **options):
        User = get_user_model()

        admin, _ = User.objects.get_or_create(email="admin@saas.local", defaults={"username": "admin", "mobile": "9999999999", "is_staff": True, "is_superuser": True})
        admin.set_password("Admin@123")
        admin.save(update_fields=["password"])

        roles = [
            ("b2b@saas.local", UserRole.B2B_CUSTOMER),
            ("b2c@saas.local", UserRole.B2C_CUSTOMER),
            ("sales@saas.local", UserRole.SALESMAN),
            ("delivery@saas.local", UserRole.DELIVERY_PARTNER),
            ("cashier@saas.local", UserRole.POS_CASHIER),
        ]
        for idx, (email, role) in enumerate(roles, 1):
            user, _ = User.objects.get_or_create(email=email, defaults={"username": email.split("@")[0], "mobile": f"900000000{idx}"})
            user.set_password("Demo@123")
            user.save(update_fields=["password"])
            UserProfileExt.objects.get_or_create(user=user, defaults={"role": role})

        wh, _ = Warehouse.objects.get_or_create(code="DS-01", defaults={"name": "Central Dark Store", "latitude": 28.6139, "longitude": 77.2090, "capacity_units": 5000})

        cat, _ = Category.objects.get_or_create(slug="groceries", defaults={"name": "Groceries"})
        p1, _ = Product.objects.get_or_create(sku="RICE001", defaults={"name": "Basmati Rice 5kg", "category": cat, "barcode": "8901234567890", "gst_percent": Decimal("5.00"), "mrp": Decimal("650"), "b2b_price": Decimal("560"), "b2c_price": Decimal("620"), "wholesale_price": Decimal("540")})
        p2, _ = Product.objects.get_or_create(sku="OIL001", defaults={"name": "Sunflower Oil 1L", "category": cat, "barcode": "8901234567891", "gst_percent": Decimal("5.00"), "mrp": Decimal("160"), "b2b_price": Decimal("130"), "b2c_price": Decimal("145"), "wholesale_price": Decimal("125")})

        WarehouseInventory.objects.get_or_create(warehouse=wh, product=p1, defaults={"available_qty": 300})
        WarehouseInventory.objects.get_or_create(warehouse=wh, product=p2, defaults={"available_qty": 500})

        CommissionRule.objects.get_or_create(name="Default Margin Rule", defaults={"salesman_percent": Decimal("10"), "delivery_percent": Decimal("5"), "is_default": True})

        self.stdout.write(self.style.SUCCESS("Universal platform seed data created."))
