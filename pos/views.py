from django.views.generic import TemplateView
from rest_framework import decorators, permissions, response, viewsets

from .models import POSHoldBill, POSReprintLog, POSSession, POSTerminal
from .serializers import POSHoldBillSerializer, POSReprintLogSerializer, POSSessionSerializer, POSTerminalSerializer
from .services.pos_engine import hold_bill, retrieve_hold_bill


class POSView(TemplateView):
    template_name = "pos/terminal.html"


class POSTerminalViewSet(viewsets.ModelViewSet):
    queryset = POSTerminal.objects.select_related("user").all()
    serializer_class = POSTerminalSerializer
    permission_classes = [permissions.IsAuthenticated]


class POSSessionViewSet(viewsets.ModelViewSet):
    queryset = POSSession.objects.select_related("terminal", "cashier").all()
    serializer_class = POSSessionSerializer
    permission_classes = [permissions.IsAuthenticated]


class POSHoldBillViewSet(viewsets.ModelViewSet):
    queryset = POSHoldBill.objects.select_related("session").all()
    serializer_class = POSHoldBillSerializer
    permission_classes = [permissions.IsAuthenticated]

    @decorators.action(detail=False, methods=["post"])
    def hold(self, request):
        bill = hold_bill(request.data["session_id"], request.data["payload"])
        return response.Response(self.get_serializer(bill).data)

    @decorators.action(detail=False, methods=["get"], url_path="retrieve-hold")
    def retrieve_hold(self, request):
        code = request.query_params.get("hold_code", "")
        bill = retrieve_hold_bill(code)
        return response.Response(self.get_serializer(bill).data if bill else {})


class POSReprintLogViewSet(viewsets.ModelViewSet):
    queryset = POSReprintLog.objects.select_related("order", "cashier").all()
    serializer_class = POSReprintLogSerializer
    permission_classes = [permissions.IsAuthenticated]
