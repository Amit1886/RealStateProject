from django.conf import settings
from django.http import HttpResponse


def _allowed_origins():
    configured = [x.strip() for x in getattr(settings, "CORS_ALLOWED_ORIGINS", []) if x.strip()]
    if configured:
        return configured

    if settings.DEBUG or getattr(settings, "RUNNING_RUNSERVER", False):
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ]
    return []


class DevCorsMiddleware:
    """
    Minimal CORS support for local frontend/mobile development.

    We keep this intentionally narrow and environment-driven instead of adding
    a new dependency just for the dev dashboard/app origins.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin", "")
        allowed_origins = _allowed_origins()
        allow_all = getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False)
        origin_allowed = allow_all or origin in allowed_origins

        if request.method == "OPTIONS" and origin and origin_allowed:
            response = HttpResponse(status=200)
        else:
            response = self.get_response(request)

        if origin and origin_allowed:
            response["Access-Control-Allow-Origin"] = "*" if allow_all else origin
            response["Vary"] = "Origin"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Company-ID"
            response["Access-Control-Expose-Headers"] = "Content-Type"

        return response
