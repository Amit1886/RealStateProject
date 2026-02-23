from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from addons.common.db import DB_EXCEPTIONS, db_unavailable
from addons.common.permissions import IsStaffOrSuperuser
from addons.ecommerce_engine.models import StorefrontOrder, StorefrontProduct
from addons.ecommerce_engine.services import create_storefront_order, mark_payment_paid, sync_products_from_billing


class StorefrontProductListAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def get(self, request):
        try:
            rows = StorefrontProduct.objects.order_by("product_name")[:200]
            return Response(
                [
                    {
                        "id": row.id,
                        "sku": row.sku,
                        "product_name": row.product_name,
                        "price": row.price,
                        "available_stock": row.available_stock,
                        "selected_for_online": row.selected_for_online,
                        "is_published": row.is_published,
                    }
                    for row in rows
                ]
            )
        except DB_EXCEPTIONS:
            return db_unavailable()


class SyncProductsAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def post(self, request):
        try:
            count = sync_products_from_billing(branch_code=request.data.get("branch_code", "default"))
            return Response({"synced": count})
        except DB_EXCEPTIONS:
            return db_unavailable()


class StorefrontOrderCreateAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def post(self, request):
        required = ["order_number", "customer_name", "customer_phone", "items"]
        for key in required:
            if key not in request.data:
                return Response({"detail": f"{key} is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            order = create_storefront_order(request.data)
            return Response({"order_id": order.id, "total_amount": order.total_amount}, status=status.HTTP_201_CREATED)
        except DB_EXCEPTIONS:
            return db_unavailable()


class StorefrontOrderListAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def get(self, request):
        try:
            rows = StorefrontOrder.objects.order_by("-created_at")[:100]
            return Response(
                [
                    {
                        "id": row.id,
                        "order_number": row.order_number,
                        "customer_name": row.customer_name,
                        "status": row.status,
                        "payment_status": row.payment_status,
                        "synced_to_billing": row.synced_to_billing,
                    }
                    for row in rows
                ]
            )
        except DB_EXCEPTIONS:
            return db_unavailable()


class StorefrontPaymentSuccessAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def post(self, request, order_id: int):
        try:
            order = StorefrontOrder.objects.filter(id=order_id).first()
            if not order:
                return Response({"detail": "order not found"}, status=status.HTTP_404_NOT_FOUND)
            gateway = request.data.get("gateway", "razorpay")
            payment_ref = request.data.get("payment_ref", f"txn-{order.id}")
            mark_payment_paid(order, gateway=gateway, payment_ref=payment_ref)
            return Response({"status": order.payment_status, "order_status": order.status})
        except DB_EXCEPTIONS:
            return db_unavailable()
