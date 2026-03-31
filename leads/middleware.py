from __future__ import annotations

from django.http import JsonResponse

from .models import Lead
from .services import user_can_edit_lead


class LeadLockMiddleware:
    """
    Prevent unsafe lead mutations by users other than the assigned agent or admin.

    This is intentionally narrow: it only guards unsafe requests that resolve a lead pk
    so it doesn't interfere with list endpoints or unrelated views.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return None
        resolver_match = getattr(request, "resolver_match", None)
        if not resolver_match or not getattr(resolver_match, "app_name", ""):
            return None
        if "leads" not in (resolver_match.app_name or "") and "leads" not in (resolver_match.namespace or ""):
            return None
        lead_pk = view_kwargs.get("pk") or view_kwargs.get("lead_id") or view_kwargs.get("lead_pk")
        if not lead_pk:
            return None
        lead = Lead.objects.select_related("assigned_agent__user", "assigned_to").filter(pk=lead_pk).first()
        if not lead:
            return None
        if user_can_edit_lead(request.user, lead):
            return None
        return JsonResponse({"detail": "This lead is locked to another agent."}, status=403)
