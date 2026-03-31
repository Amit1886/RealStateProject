from functools import wraps

from django.http import JsonResponse
from django.shortcuts import redirect
from rest_framework.permissions import BasePermission

from billing.services import user_has_feature


def feature_required(feature_key, redirect_url="/billing/upgrade/"):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if user_has_feature(request.user, feature_key):
                return view_func(request, *args, **kwargs)
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {"status": "locked", "message": "This feature requires upgrade."},
                    status=403,
                )
            return redirect(redirect_url)
        return _wrapped
    return decorator


class FeatureActionPermission(BasePermission):
    message = "This feature is disabled for your plan."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if user.is_superuser or getattr(user, "is_staff", False):
            return True
        feature_key = getattr(view, "feature_key", None)
        action_map = getattr(view, "feature_key_map", None) or {}
        action = getattr(view, "action", None)
        if action and action in action_map:
            feature_key = action_map[action]
        if not feature_key:
            return True
        return user_has_feature(user, feature_key)
