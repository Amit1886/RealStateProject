import os

from django.http import JsonResponse
from django.utils import timezone


def healthcheck(request):
    token = os.getenv("HEALTHCHECK_TOKEN", "").strip()
    if token:
        provided = request.headers.get("X-Health-Token") or request.GET.get("token", "")
        if provided != token:
            return JsonResponse({"status": "forbidden"}, status=403)

    return JsonResponse(
        {
            "status": "ok",
            "ts": timezone.now().isoformat(),
        }
    )
