from rest_framework import decorators, filters, permissions, response, status, viewsets

from .models import Order, OrderItem, OrderReturn, POSBill
from .serializers import OrderItemSerializer, OrderReturnSerializer, OrderSerializer, POSBillSerializer
from .services.order_engine import place_order, recalculate_order


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related("customer", "salesman", "warehouse").prefetch_related("items").all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["order_number", "walk_in_customer_name", "customer__email"]
    ordering_fields = ["created_at", "updated_at", "total_amount"]

    @decorators.action(detail=True, methods=["post"])
    def recalculate(self, request, pk=None):
        order = self.get_object()
        recalculate_order(order)
        return response.Response(self.get_serializer(order).data)

    @decorators.action(detail=False, methods=["post"])
    def quick_place(self, request):
        order = place_order(request.data, actor=request.user)
        return response.Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.select_related("order", "product").all()
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]


class POSBillViewSet(viewsets.ModelViewSet):
    queryset = POSBill.objects.select_related("order", "cashier").all()
    serializer_class = POSBillSerializer
    permission_classes = [permissions.IsAuthenticated]


class OrderReturnViewSet(viewsets.ModelViewSet):
    queryset = OrderReturn.objects.select_related("order").all()
    serializer_class = OrderReturnSerializer
    permission_classes = [permissions.IsAuthenticated]
