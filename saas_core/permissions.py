from rest_framework import permissions


class IsTenantUser(permissions.BasePermission):
    """
    Ensures authenticated user belongs to request.company.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        company = getattr(request, "company", None)
        return company and getattr(request.user, "company_id", None) == company.id
