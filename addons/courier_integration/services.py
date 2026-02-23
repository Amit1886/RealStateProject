from __future__ import annotations

import os
from typing import Dict, Optional

from django.utils.crypto import get_random_string
from django.utils.timezone import now

from addons.courier_integration.models import CourierProvider, CourierProviderConfig, Shipment, ShipmentEvent


def _mock_enabled() -> bool:
    return os.getenv("COURIER_INTEGRATION_MOCK", "True").strip().lower() in {"1", "true", "yes", "y", "on"}


def _generate_awb(prefix: str = "AWB") -> str:
    return f"{prefix}-{now().strftime('%Y%m%d')}-{get_random_string(10).upper()}"


def get_provider_config(*, branch_code: str, provider: str) -> Optional[CourierProviderConfig]:
    return CourierProviderConfig.objects.filter(branch_code=branch_code, provider=provider, is_active=True).first()


def create_shipment(
    *,
    branch_code: str,
    provider: str,
    ref_type: str,
    ref: str,
    payload: Optional[Dict] = None,
) -> Shipment:
    shipment = Shipment.objects.create(
        branch_code=branch_code or "default",
        provider=provider or CourierProvider.SHIPROCKET,
        ref_type=ref_type,
        ref=ref,
        status=Shipment.Status.CREATED,
        meta=payload or {},
    )

    if _mock_enabled():
        shipment.awb = _generate_awb(prefix=str(provider).upper())
        shipment.tracking_number = shipment.awb
        shipment.tracking_url = f"https://tracking.example/{shipment.awb}"
        shipment.status = Shipment.Status.BOOKED
        shipment.last_synced_at = now()
        shipment.save(update_fields=["awb", "tracking_number", "tracking_url", "status", "last_synced_at", "updated_at"])
        ShipmentEvent.objects.create(shipment=shipment, event_type="mock_booked", payload={"awb": shipment.awb})

    return shipment


def apply_tracking_update(*, shipment: Shipment, status: str, payload: Dict) -> Shipment:
    shipment.status = status
    shipment.last_synced_at = now()
    shipment.meta = {**(shipment.meta or {}), **(payload or {})}
    shipment.save(update_fields=["status", "last_synced_at", "meta", "updated_at"])
    ShipmentEvent.objects.create(shipment=shipment, event_type="tracking_update", payload=payload or {})
    return shipment

