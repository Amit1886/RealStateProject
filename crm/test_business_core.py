from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import SaaSRole, User
from crm.inventory_hold import expire_due_holds, release_hold
from crm.models import UnitHold
from leads.models import Property
from saas_core.models import Company


class InventoryHoldCoreTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Inventory Core Realty")
        self.admin = User.objects.create_user(
            email="inventory-admin@example.com",
            username="inventory-admin",
            mobile="9666666666",
            password="Admin@123",
            role=SaaSRole.SUPER_ADMIN,
            company=self.company,
            is_staff=True,
        )
        self.property = Property.objects.create(
            title="Hold Unit",
            price="2500000.00",
            city="Lucknow",
            company=self.company,
        )

    def test_hold_expiry_and_release(self):
        hold = UnitHold.objects.create(
            unit=self.property,
            agent=self.admin,
            hold_end=timezone.now() - timedelta(hours=1),
            reason="Test hold",
        )

        expired = expire_due_holds()
        hold.refresh_from_db()
        self.assertEqual(expired, 1)
        self.assertEqual(hold.status, UnitHold.HoldStatus.EXPIRED)

        hold = UnitHold.objects.create(
            unit=self.property,
            agent=self.admin,
            hold_end=timezone.now() + timedelta(hours=1),
            reason="Release me",
        )
        release_hold(hold, reason="Customer released unit")
        hold.refresh_from_db()
        self.assertEqual(hold.status, UnitHold.HoldStatus.RELEASED)
        self.assertIsNotNone(hold.released_at)
