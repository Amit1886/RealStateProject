from django.contrib.auth.models import AnonymousUser


class JWTAuthenticationMiddleware:
    """
    Populate request.user for JWT-auth API calls.

    This enables upstream Django middleware (feature gates, auditing, etc.) to enforce
    access for token-auth clients, not only session-auth clients.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only attempt JWT auth for API paths.
        if (request.path or "").startswith("/api/"):
            user = getattr(request, "user", None)
            if not user or isinstance(user, AnonymousUser) or not getattr(user, "is_authenticated", False):
                try:
                    from rest_framework_simplejwt.authentication import JWTAuthentication

                    authenticator = JWTAuthentication()
                    auth = authenticator.authenticate(request)
                    if auth:
                        request.user, request.auth = auth
                except Exception:
                    # Leave request.user unchanged on any auth parsing/validation issue.
                    pass

        return self.get_response(request)
