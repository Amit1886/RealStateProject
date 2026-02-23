import os

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from addons.common.db import DB_EXCEPTIONS, db_unavailable
from addons.common.permissions import IsStaffOrSuperuser
from addons.courier_integration.models import Shipment
from addons.courier_integration.services import apply_tracking_update, create_shipment


class HealthAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def get(self, request):
        return Response({"status": "ok", "addon": "courier_integration"})


class ShipmentListAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def get(self, request):
        try:
            rows = Shipment.objects.order_by("-created_at")[:100]
            return Response(
                [
                    {
                        "id": row.id,
                        "provider": row.provider,
                        "status": row.status,
                        "ref_type": row.ref_type,
                        "ref": row.ref,
                        "awb": row.awb,
                        "tracking_url": row.tracking_url,
                        "created_at": row.created_at,
                    }
                    for row in rows
                ]
            )
        except DB_EXCEPTIONS:
            return db_unavailable()


class ShipmentCreateAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def post(self, request):
        try:
            ref = request.data.get("ref")
            if not ref:
                return Response({"detail": "ref is required"}, status=status.HTTP_400_BAD_REQUEST)
            provider = request.data.get("provider", "shiprocket")
            ref_type = request.data.get("ref_type", "storefront_order")
            shipment = create_shipment(
                branch_code=request.data.get("branch_code", "default"),
                provider=provider,
                ref_type=ref_type,
                ref=ref,
                payload={"requested_by": getattr(request.user, "id", None)},
            )
            return Response({"shipment_id": shipment.id, "awb": shipment.awb, "status": shipment.status}, status=status.HTTP_201_CREATED)
        except DB_EXCEPTIONS:
            return db_unavailable()


class ShipmentDetailAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def get(self, request, shipment_id: int):
        try:
            row = Shipment.objects.filter(id=shipment_id).first()
            if not row:
                return Response({"detail": "shipment not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(
                {
                    "id": row.id,
                    "provider": row.provider,
                    "status": row.status,
                    "ref_type": row.ref_type,
                    "ref": row.ref,
                    "awb": row.awb,
                    "tracking_number": row.tracking_number,
                    "tracking_url": row.tracking_url,
                    "meta": row.meta,
                    "last_synced_at": row.last_synced_at,
                }
            )
        except DB_EXCEPTIONS:
            return db_unavailable()


class CourierWebhookAPI(APIView):
    """
    Minimal webhook receiver for courier status updates.

    Protect with `X-Courier-Key` and `COURIER_WEBHOOK_KEY` env.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        expected = os.getenv("COURIER_WEBHOOK_KEY", "").strip()
        provided = (request.META.get("HTTP_X_COURIER_KEY") or "").strip()
        if not expected or provided != expected:
            return Response({"detail": "unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            shipment_id = request.data.get("shipment_id")
            new_status = request.data.get("status")
            if not shipment_id or not new_status:
                return Response({"detail": "shipment_id and status are required"}, status=status.HTTP_400_BAD_REQUEST)

            shipment = Shipment.objects.filter(id=shipment_id).first()
            if not shipment:
                return Response({"detail": "shipment not found"}, status=status.HTTP_404_NOT_FOUND)

            apply_tracking_update(shipment=shipment, status=new_status, payload={"webhook": request.data})
            return Response({"status": "ok"})
        except DB_EXCEPTIONS:
            return db_unavailable()

