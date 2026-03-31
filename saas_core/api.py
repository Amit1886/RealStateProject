from rest_framework import permissions, viewsets, mixins


class IsCompanyMember(permissions.BasePermission):
    """
    Allow only if request.company is set and matches user's company (or user is superuser).
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return bool(getattr(request.user, "company_id", None) and request.company and request.user.company_id == request.company.id)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        company_id = getattr(obj, "company_id", None)
        if company_id is None:
            return False
        return request.company and request.company.id == company_id


class RoleRequired(permissions.BasePermission):
    """
    Enforce allowed roles list on the view (set view.allowed_roles).
    """

    def has_permission(self, request, view):
        allowed = getattr(view, "allowed_roles", None)
        if not allowed:
            return True
        user_role = getattr(request.user, "role", "")
        return bool(user_role in allowed)


class CompanyQuerysetMixin:
    """
    Filters queryset by request.company and sets company on create.
    Assumes model has company FK.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        company = getattr(self.request, "company", None)
        if company:
            return qs.filter(company=company)
        return qs.none()

    def perform_create(self, serializer):
        company = getattr(self.request, "company", None)
        serializer.save(company=company)
