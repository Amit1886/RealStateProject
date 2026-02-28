from rest_framework.permissions import BasePermission

from billing.services import get_effective_plan


class PlanAPIPermissionGate(BasePermission):
    """
    Enforce billing.PlanPermissions flags for authenticated API callers.

    This is required for JWT-auth clients because AuthenticationMiddleware does not
    populate request.user for JWT requests (DRF does it later in the request cycle).
    """

    api_permission_map = [
        ("/api/v1/warehouses/", "allow_warehouse"),
        ("/api/v1/products/", "allow_inventory"),
        ("/api/v1/orders/", "allow_orders"),
        ("/api/v1/pos/", "allow_orders"),
        ("/api/v1/printers/", "allow_commerce"),
        ("/api/v1/scanners/", "allow_inventory"),
        ("/api/v1/commission/", "allow_analytics"),
        ("/api/v1/delivery/", "allow_orders"),
        ("/api/v1/payments/", "allow_commerce"),
        ("/api/v1/analytics/", "allow_analytics"),
        ("/api/v1/ai/", "allow_analytics"),
        ("/api/v1/realtime/", "allow_api_access"),
        ("/api/v1/users/", "allow_users"),
    ]

    def has_permission(self, request, view):
        path = request.path or ""
        if not path.startswith("/api/"):
            return True

        # Let IsAuthenticated handle 401 vs 403.
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return True

        if user.is_superuser:
            return True

        required_perm = None
        for prefix, perm_field in self.api_permission_map:
            if path.startswith(prefix):
                required_perm = perm_field
                break

        if not required_perm:
            return True

        plan = get_effective_plan(user)
        perms = plan.get_permissions() if plan else None
        allowed = bool(perms and getattr(perms, required_perm, False))
        if not allowed:
            # Useful for logs / debugging.
            request._required_permission = required_perm  # noqa: SLF001
        return allowed
