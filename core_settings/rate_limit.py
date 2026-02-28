import os
import time
import sys

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


class RateLimitMiddleware:
    """
    Simple fixed-window rate limiting for high-risk endpoints.

    Defaults are intentionally permissive; tune via env vars:
    - RL_LOGIN_PER_MIN (default 30)
    - RL_OTP_PER_MIN (default 30)
    - RL_JWT_PER_MIN (default 60)
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.login_per_min = int(os.getenv("RL_LOGIN_PER_MIN", "30"))
        self.otp_per_min = int(os.getenv("RL_OTP_PER_MIN", "30"))
        self.jwt_per_min = int(os.getenv("RL_JWT_PER_MIN", "60"))

        enabled_env = os.getenv("RATE_LIMIT_ENABLED")
        if enabled_env is None:
            # Dev-friendly default: avoid accidental 429s while testing locally.
            running_tests = "test" in sys.argv
            self.enabled = not (settings.DEBUG or running_tests)
        else:
            self.enabled = enabled_env.lower() == "true"

    def __call__(self, request):
        if not self.enabled:
            return self.get_response(request)

        path = request.path
        method = request.method.upper()

        user = getattr(request, "user", None)
        if user and user.is_authenticated and (user.is_staff or user.is_superuser):
            return self.get_response(request)

        if method == "POST":
            if path.startswith("/accounts/login/"):
                limited, meta = self._hit(request, scope="login", limit=self.login_per_min)
                if limited:
                    return self._reject(meta)
            elif path.startswith("/accounts/verify-otp"):
                limited, meta = self._hit(request, scope="otp", limit=self.otp_per_min)
                if limited:
                    return self._reject(meta)
            elif path.startswith("/api/auth/token/") or path.startswith("/api/auth/token/refresh/"):
                limited, meta = self._hit(request, scope="jwt", limit=self.jwt_per_min)
                if limited:
                    return self._reject(meta)

        return self.get_response(request)

    def _client_ip(self, request) -> str:
        # Best-effort IP extraction; do not trust XFF unless your proxy sanitizes it.
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR") or "unknown"

    def _hit(self, request, scope: str, limit: int):
        ip = self._client_ip(request)
        window = int(time.time() // 60)
        key = f"rl:{scope}:{ip}:{window}"
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=70)
            count = 1
        remaining = max(0, limit - count)
        return count > limit, {"scope": scope, "limit_per_min": limit, "remaining": remaining}

    def _reject(self, meta: dict):
        return JsonResponse(
            {
                "detail": "Too many requests. Please try again soon.",
                "rate_limit": meta,
            },
            status=429,
        )
