from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from addons.common.db import DB_EXCEPTIONS, db_unavailable
from addons.ads_manager.models import Campaign
from addons.ads_manager.services import compute_roi, enforce_budget, queue_metrics_sync
from addons.common.permissions import IsStaffOrSuperuser


class CampaignListAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def get(self, request):
        try:
            rows = Campaign.objects.select_related("account").order_by("-created_at")[:100]
            return Response(
                [
                    {
                        "id": row.id,
                        "name": row.name,
                        "platform": row.account.platform,
                        "status": row.status,
                        "daily_budget": row.daily_budget,
                    }
                    for row in rows
                ]
            )
        except DB_EXCEPTIONS:
            return db_unavailable()


class CampaignROIApi(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def get(self, request, campaign_id: int):
        try:
            campaign = Campaign.objects.filter(id=campaign_id).first()
            if not campaign:
                return Response({"detail": "campaign not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(compute_roi(campaign))
        except DB_EXCEPTIONS:
            return db_unavailable()


class CampaignSyncAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def post(self, request, campaign_id: int):
        try:
            campaign = Campaign.objects.filter(id=campaign_id).first()
            if not campaign:
                return Response({"detail": "campaign not found"}, status=status.HTTP_404_NOT_FOUND)
            queue_metrics_sync(campaign)
            return Response({"status": "queued"}, status=status.HTTP_202_ACCEPTED)
        except DB_EXCEPTIONS:
            return db_unavailable()


class CampaignBudgetGuardAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def post(self, request, campaign_id: int):
        try:
            campaign = Campaign.objects.filter(id=campaign_id).first()
            if not campaign:
                return Response({"detail": "campaign not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(enforce_budget(campaign))
        except DB_EXCEPTIONS:
            return db_unavailable()
