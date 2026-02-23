from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .services import get_state, get_user_state, reset_state, set_toggle


def _branch_code(request) -> str:
    return request.GET.get("branch_code", "default")


@staff_member_required
def index(request):
    return render(request, "demo_center/index.html", {"state": get_state(_branch_code(request))})


@staff_member_required
def admin_dashboard(request):
    return render(request, "demo_center/admin_dashboard.html", {"state": get_state(_branch_code(request))})


@staff_member_required
def user_experience(request):
    # Admin view of the user flow (dummy timeline + metrics)
    return render(request, "demo_center/user_experience.html", {"state": get_state(_branch_code(request))})


@login_required
def user_demo(request):
    # Real demo data view for the logged-in user (e.g., Demotest3).
    return render(request, "demo_center/user_demo.html", {"state": get_user_state(request.user, _branch_code(request))})


@staff_member_required
def marketing_ads(request):
    return render(request, "demo_center/marketing_ads.html", {"state": get_state(_branch_code(request))})


@staff_member_required
def courier_transport(request):
    return render(request, "demo_center/courier_transport.html", {"state": get_state(_branch_code(request))})


@staff_member_required
def accounting(request):
    return render(request, "demo_center/accounting.html", {"state": get_state(_branch_code(request))})


@staff_member_required
def hr(request):
    return render(request, "demo_center/hr.html", {"state": get_state(_branch_code(request))})


@staff_member_required
def autopilot_logs(request):
    return render(request, "demo_center/autopilot_logs.html", {"state": get_state(_branch_code(request))})


@staff_member_required
def how_it_works(request):
    return render(request, "demo_center/how_it_works.html", {"state": get_state(_branch_code(request))})


@staff_member_required
def api_state(request):
    return JsonResponse(get_state(_branch_code(request)))


@login_required
def api_user_state(request):
    return JsonResponse(get_user_state(request.user, _branch_code(request)))


@staff_member_required
@require_http_methods(["POST"])
def api_reset(request):
    return JsonResponse(reset_state(_branch_code(request)))


@staff_member_required
@require_http_methods(["POST"])
def api_toggle(request, key: str):
    enabled = str(request.POST.get("enabled", "true")).strip().lower() in {"1", "true", "yes", "on"}
    return JsonResponse(set_toggle(_branch_code(request), key, enabled))


@staff_member_required
@require_http_methods(["POST"])
def reset_and_redirect(request):
    reset_state(_branch_code(request))
    return redirect("demo_center:index")
