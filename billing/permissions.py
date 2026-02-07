from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect

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
