from django.db import transaction
from django.db.models import F

from products.models import WarehouseInventory


@transaction.atomic
def reserve_stock(warehouse_id: int, product_id: int, qty: int) -> bool:
    updated = WarehouseInventory.objects.filter(
        warehouse_id=warehouse_id,
        product_id=product_id,
        available_qty__gte=F("reserved_qty") + qty,
    ).update(reserved_qty=F("reserved_qty") + qty)
    return updated > 0


@transaction.atomic
def deduct_stock(warehouse_id: int, product_id: int, qty: int) -> bool:
    updated = WarehouseInventory.objects.filter(
        warehouse_id=warehouse_id,
        product_id=product_id,
        reserved_qty__gte=qty,
    ).update(available_qty=F("available_qty") - qty, reserved_qty=F("reserved_qty") - qty)
    return updated > 0
