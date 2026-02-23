from rest_framework import decorators, permissions, response, viewsets

from .models import DailyCashSummary, PaymentTransaction
from .serializers import DailyCashSummarySerializer, PaymentTransactionSerializer
from .services.gateway import create_razorpay_order_placeholder


class PaymentTransactionViewSet(viewsets.ModelViewSet):
    queryset = PaymentTransaction.objects.select_related("order", "user").all()
    serializer_class = PaymentTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @decorators.action(detail=False, methods=["post"])
    def razorpay_create(self, request):
        payload = create_razorpay_order_placeholder(request.data.get("amount"))
        return response.Response(payload)


class DailyCashSummaryViewSet(viewsets.ModelViewSet):
    queryset = DailyCashSummary.objects.select_related("cashier").all()
    serializer_class = DailyCashSummarySerializer
    permission_classes = [permissions.IsAuthenticated]
