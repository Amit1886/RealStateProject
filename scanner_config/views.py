from rest_framework import decorators, permissions, response, viewsets

from .models import ScanEvent, ScannerConfig
from .serializers import ScanEventSerializer, ScannerConfigSerializer
from .services.scanner_engine import detect_barcode_type


class ScannerConfigViewSet(viewsets.ModelViewSet):
    queryset = ScannerConfig.objects.select_related("user").all()
    serializer_class = ScannerConfigSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScanEventViewSet(viewsets.ModelViewSet):
    queryset = ScanEvent.objects.select_related("user", "scanner_config").all()
    serializer_class = ScanEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    @decorators.action(detail=False, methods=["post"])
    def detect(self, request):
        code = request.data.get("raw_code", "")
        return response.Response({"code_type": detect_barcode_type(code)})
