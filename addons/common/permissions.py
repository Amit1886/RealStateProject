from rest_framework.permissions import BasePermission


class IsStaffOrSuperuser(BasePermission):
    """Restrict addon APIs to elevated users by default."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))
