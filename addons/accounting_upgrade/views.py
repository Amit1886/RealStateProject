from rest_framework.response import Response
from rest_framework.views import APIView

from addons.common.permissions import IsStaffOrSuperuser


class HealthAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def get(self, request):
        return Response({"status": "ok", "addon": "accounting_upgrade"})

