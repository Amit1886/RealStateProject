import os

from rest_framework.permissions import BasePermission


class HasStorefrontKey(BasePermission):
    """
    Protect public storefront APIs with a shared key.

    Send `X-Storefront-Key: <key>` header.
    """

    header_name = "HTTP_X_STOREFRONT_KEY"
    env_name = "STOREFRONT_PUBLIC_API_KEY"

    def has_permission(self, request, view):
        expected = os.getenv(self.env_name, "").strip()
        if not expected:
            return False
        provided = (request.META.get(self.header_name) or "").strip()
        return bool(provided) and provided == expected

