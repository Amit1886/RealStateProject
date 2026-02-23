from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from addons.common.db import DB_EXCEPTIONS, db_unavailable
from addons.common.permissions import IsStaffOrSuperuser
from addons.marketing_autopilot.models import ContentSchedule
from addons.marketing_autopilot.services import generate_caption, generate_hashtags, queue_creative_asset, schedule_post


class MarketingTextGenAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def post(self, request):
        topic = request.data.get("topic", "")
        if not topic:
            return Response({"detail": "topic is required"}, status=status.HTTP_400_BAD_REQUEST)
        tone = request.data.get("tone", "professional")
        return Response({"caption": generate_caption(topic, tone), "hashtags": generate_hashtags(topic)})


class MarketingScheduleListAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def get(self, request):
        try:
            rows = ContentSchedule.objects.order_by("-scheduled_for")[:100]
            return Response(
                [
                    {
                        "id": row.id,
                        "platform": row.platform,
                        "title": row.title,
                        "status": row.status,
                        "scheduled_for": row.scheduled_for,
                    }
                    for row in rows
                ]
            )
        except DB_EXCEPTIONS:
            return db_unavailable()


class MarketingScheduleCreateAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def post(self, request):
        scheduled_for = parse_datetime(request.data.get("scheduled_for", ""))
        if not scheduled_for:
            return Response({"detail": "valid scheduled_for is required"}, status=status.HTTP_400_BAD_REQUEST)

        payload = {
            "branch_code": request.data.get("branch_code", "default"),
            "platform": request.data.get("platform"),
            "title": request.data.get("title"),
            "caption": request.data.get("caption", ""),
            "hashtags": request.data.get("hashtags", ""),
            "media_url": request.data.get("media_url", ""),
            "scheduled_for": scheduled_for,
        }
        if not payload["platform"] or not payload["title"]:
            return Response({"detail": "platform and title are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            schedule = schedule_post(payload)
            return Response({"schedule_id": schedule.id, "status": schedule.status}, status=status.HTTP_201_CREATED)
        except DB_EXCEPTIONS:
            return db_unavailable()


class CreativeAssetCreateAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def post(self, request):
        kind = request.data.get("kind")
        prompt = request.data.get("prompt")
        if not kind or not prompt:
            return Response({"detail": "kind and prompt are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            asset = queue_creative_asset(kind=kind, prompt=prompt, branch_code=request.data.get("branch_code", "default"))
            return Response({"asset_id": asset.id, "status": asset.status}, status=status.HTTP_201_CREATED)
        except DB_EXCEPTIONS:
            return db_unavailable()
