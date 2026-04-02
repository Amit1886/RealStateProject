from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import json
from django.urls import reverse

from core_settings.permissions import has_feature
from core_settings.models import CompanySettings, UISettings, AppSettings
from core_settings.services import (
    get_settings_payload,
    apply_updates,
    undo_last_change,
    build_ai_hints,
    get_status_cards,
)
from accounts.models import UserProfile
from billing.models import Plan, PlanPermissions
from billing.models import FeatureRegistry, UserFeatureOverride
from django.contrib.auth import get_user_model
from validation.models import FraudAlert


SMART_PLAN_PERMISSION_SECTIONS = [
    (
        "Dashboard & Reports",
        [
            ("allow_dashboard", "Dashboard"),
            ("allow_reports", "Reports"),
            ("allow_pdf_export", "PDF export"),
            ("allow_excel_export", "Excel export"),
            ("allow_analytics", "Analytics"),
            ("allow_ledger", "Ledger"),
            ("allow_credit_report", "Credit report"),
        ],
    ),
    (
        "Party & Transactions",
        [
            ("allow_add_party", "Add party"),
            ("allow_edit_party", "Edit party"),
            ("allow_delete_party", "Delete party"),
            ("max_parties", "Max parties"),
            ("allow_add_transaction", "Add transaction"),
            ("allow_edit_transaction", "Edit transaction"),
            ("allow_delete_transaction", "Delete transaction"),
            ("allow_bulk_transaction", "Bulk transaction"),
        ],
    ),
    (
        "Commerce & Communication",
        [
            ("allow_commerce", "Commerce"),
            ("allow_warehouse", "Warehouse"),
            ("allow_orders", "Orders"),
            ("allow_inventory", "Inventory"),
            ("allow_whatsapp", "WhatsApp"),
            ("allow_sms", "SMS"),
            ("allow_email", "Email"),
        ],
    ),
    (
        "Admin & API",
        [
            ("allow_settings", "Settings"),
            ("allow_users", "Users"),
            ("allow_api_access", "API access"),
        ],
    ),
]

SMART_PLAN_PERMISSION_FIELDS = [
    field_name
    for _, fields in SMART_PLAN_PERMISSION_SECTIONS
    for field_name, _ in fields
    if field_name != "max_parties"
]


def party_disabled(request):
    return HttpResponse("❌ Party module disabled by admin")


@login_required
def settings_dashboard(request):
    """Main settings dashboard with plan-wise permissions"""

    # Get user's plan and permissions
    user_profile = UserProfile.objects.filter(user=request.user).first()
    user_plan = user_profile.plan if user_profile else None
    plan_permissions = user_plan.get_permissions() if user_plan else None

    # 🔐 Subscription permission
    if (not (request.user.is_staff or request.user.is_superuser)) and (not has_feature(request.user, "settings.advanced")):
        return HttpResponse("❌ Your plan does not allow Settings access")

    company = CompanySettings.objects.first()
    ui = UISettings.objects.first()
    app = AppSettings.objects.first()

    if request.method == "POST":

        # 🏢 Company
        if has_feature(request.user, "company"):
            company.company_name = request.POST.get("company_name")
            company.mobile = request.POST.get("mobile")
            company.email = request.POST.get("email")
            company.save()

        # 🎨 UI
        if has_feature(request.user, "ui"):
            ui.primary_color = request.POST.get("primary_color")
            ui.secondary_color = request.POST.get("secondary_color")
            ui.theme_mode = request.POST.get("theme_mode")
            ui.sidebar_position = request.POST.get("sidebar_position")
            ui.save()

        messages.success(request, "✅ Settings Updated Successfully")
        return redirect("settings")

    return render(request, "core_settings/dashboard.html", {
        "company": company,
        "ui": ui,
        "app": app,
        "user_plan": user_plan,
        "plan_permissions": plan_permissions,
    })


@login_required
def plan_permissions_view(request):
    """View all plans and their permissions - Admin Only"""
    
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponse("❌ Admin access required")
    if request.method == "POST":
        plan_id = request.POST.get("plan_id")
        plan = Plan.objects.filter(id=plan_id).first()
        if not plan:
            messages.error(request, "Plan not found.")
            return _redirect_feature_tower()
        _save_plan_permissions(plan, request.POST)
        messages.success(request, f"Permissions updated for {plan.name}.")
        return _redirect_feature_tower(plan_id=plan.id)
    return _redirect_feature_tower()


@login_required
def user_feature_overrides_view(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponse("❌ Admin access required")
    if request.method == "POST":
        selected_user_id = request.POST.get("user_id")
        selected_user = get_user_model().objects.filter(id=selected_user_id).first()
        if not selected_user:
            messages.error(request, "User not found.")
            return _redirect_feature_tower()
        features = FeatureRegistry.objects.filter(active=True).order_by("group", "label")
        _save_user_overrides(selected_user, features, request.POST)
        messages.success(request, "User overrides updated.")
        return _redirect_feature_tower(user_id=selected_user.id)
    return _redirect_feature_tower()


def _redirect_feature_tower(plan_id=None, user_id=None):
    url = reverse("core_settings:feature_control_tower")
    query = []
    if plan_id:
        query.append(f"plan_id={plan_id}")
    if user_id:
        query.append(f"user_id={user_id}")
    return redirect(f"{url}?{'&'.join(query)}" if query else url)


def _plan_permission_state(plan):
    perms = plan.get_permissions()
    state = {}
    for field_name in SMART_PLAN_PERMISSION_FIELDS:
        state[field_name] = bool(getattr(perms, field_name, False))
    state["max_parties"] = int(getattr(perms, "max_parties", 0) or 0)
    return state


def _save_plan_permissions(plan, post_data):
    perms = plan.get_permissions()
    for field_name in SMART_PLAN_PERMISSION_FIELDS:
        setattr(perms, field_name, post_data.get(field_name) == "on")

    max_parties = post_data.get("max_parties")
    if max_parties is not None and str(max_parties).strip().isdigit():
        perms.max_parties = int(max_parties)
    perms.save()
    return perms


def _save_user_overrides(user, features, post_data):
    current_overrides = {
        ov.feature_id: ov
        for ov in UserFeatureOverride.objects.filter(user=user, feature__in=features)
    }
    for feature in features:
        mode = (post_data.get(f"override_{feature.id}") or "inherit").strip().lower()
        existing = current_overrides.get(feature.id)
        if mode == "inherit":
            if existing:
                existing.delete()
            continue
        UserFeatureOverride.objects.update_or_create(
            user=user,
            feature=feature,
            defaults={
                "is_enabled": mode == "enabled",
                "note": "",
            },
        )


def _save_feature_registry(post_data):
    active_ids = set()
    for raw_id in post_data.getlist("registry_feature"):
        try:
            active_ids.add(int(raw_id))
        except Exception:
            continue
    FeatureRegistry.objects.update(active=False)
    if active_ids:
        FeatureRegistry.objects.filter(id__in=active_ids).update(active=True)


@login_required
def feature_control_tower(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponse("❌ Admin access required", status=403)

    sync_qs = FeatureRegistry.objects.all()
    if not sync_qs.exists():
        # Keep the registry fresh before rendering the UI.
        from billing.services import sync_feature_registry

        sync_feature_registry()

    plans = Plan.objects.filter(active=True).prefetch_related("permissions").order_by("price_monthly", "price", "name")
    users = get_user_model().objects.filter(is_active=True).order_by("email")
    features = FeatureRegistry.objects.filter(active=True).order_by("group", "label")
    registry_active_count = features.count()
    active_plan_count = plans.count()
    active_user_count = users.count()

    selected_plan_id = request.GET.get("plan_id") or request.POST.get("plan_id")
    selected_plan = Plan.objects.filter(id=selected_plan_id).first() if selected_plan_id else plans.first()
    if selected_plan is None:
        selected_plan = plans.first()

    selected_user_id = request.GET.get("user_id") or request.POST.get("user_id")
    selected_user = users.filter(id=selected_user_id).first() if selected_user_id else users.first()

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip().lower()
        if action == "plan" and selected_plan:
            _save_plan_permissions(selected_plan, request.POST)
            messages.success(request, f"Plan permissions saved for {selected_plan.name}.")
            return _redirect_feature_tower(plan_id=selected_plan.id, user_id=getattr(selected_user, "id", None))
        if action == "user" and selected_user:
            _save_user_overrides(selected_user, features, request.POST)
            messages.success(request, f"Feature overrides saved for {selected_user.email or selected_user}.")
            return _redirect_feature_tower(plan_id=getattr(selected_plan, "id", None), user_id=selected_user.id)
        if action == "registry":
            _save_feature_registry(request.POST)
            messages.success(request, "Global feature registry updated.")
            return _redirect_feature_tower(plan_id=getattr(selected_plan, "id", None), user_id=getattr(selected_user, "id", None))

    selected_plan_permissions = _plan_permission_state(selected_plan) if selected_plan else {}
    selected_plan_enabled_count = sum(
        1 for key, value in selected_plan_permissions.items() if key != "max_parties" and bool(value)
    ) if selected_plan_permissions else 0
    selected_plan_disabled_count = max(len(SMART_PLAN_PERMISSION_FIELDS) - selected_plan_enabled_count, 0)
    selected_user_overrides = {}
    if selected_user:
        selected_user_overrides = {
            ov.feature_id: ("enabled" if ov.is_enabled else "disabled")
            for ov in UserFeatureOverride.objects.filter(user=selected_user)
        }
    selected_user_enabled_overrides = sum(1 for mode in selected_user_overrides.values() if mode == "enabled")
    selected_user_disabled_overrides = sum(1 for mode in selected_user_overrides.values() if mode == "disabled")
    selected_user_inherited_features = max(len(features) - len(selected_user_overrides), 0)
    feature_groups = []
    current_group = None
    current_items = []
    for feature in features:
        feature_item = {
            "id": feature.id,
            "key": feature.key,
            "label": feature.label,
            "active": feature.active,
            "description": feature.description,
            "mode": selected_user_overrides.get(feature.id, "inherit"),
        }
        if current_group != feature.group:
            if current_group is not None:
                feature_groups.append({"name": current_group, "items": current_items})
            current_group = feature.group
            current_items = []
        current_items.append(feature_item)
    if current_group is not None:
        feature_groups.append({"name": current_group, "items": current_items})

    plan_sections = []
    for section_title, fields in SMART_PLAN_PERMISSION_SECTIONS:
        plan_sections.append(
            {
                "title": section_title,
                "fields": [
                    {
                        "name": field_name,
                        "label": label,
                        "value": selected_plan_permissions.get(field_name, False),
                    }
                    for field_name, label in fields
                ],
            }
        )

    return render(
        request,
        "core_settings/admin_control_tower.html",
        {
            "plans": plans,
            "users": users,
            "feature_groups": feature_groups,
            "selected_plan": selected_plan,
            "selected_user": selected_user,
            "selected_plan_permissions": selected_plan_permissions,
            "selected_plan_enabled_count": selected_plan_enabled_count,
            "selected_plan_disabled_count": selected_plan_disabled_count,
            "selected_user_overrides": selected_user_overrides,
            "selected_user_enabled_overrides": selected_user_enabled_overrides,
            "selected_user_disabled_overrides": selected_user_disabled_overrides,
            "selected_user_inherited_features": selected_user_inherited_features,
            "plan_sections": plan_sections,
            "all_features": features,
            "registry_active_count": registry_active_count,
            "active_plan_count": active_plan_count,
            "active_user_count": active_user_count,
        },
    )


@login_required
def user_permissions_view(request):
    """View current user's plan permissions"""
    
    user_profile = UserProfile.objects.filter(user=request.user).first()
    user_plan = user_profile.plan if user_profile else None
    plan_permissions = user_plan.get_permissions() if user_plan else None
    
    if not user_plan:
        messages.error(request, "❌ No plan assigned to your account")
        return redirect("accounts:dashboard")
    
    # Get all permission fields
    permission_categories = {
        "📊 Dashboard & Reports": {
            "allow_dashboard": plan_permissions.allow_dashboard if plan_permissions else False,
            "allow_reports": plan_permissions.allow_reports if plan_permissions else False,
            "allow_pdf_export": plan_permissions.allow_pdf_export if plan_permissions else False,
            "allow_excel_export": plan_permissions.allow_excel_export if plan_permissions else False,
            "allow_analytics": plan_permissions.allow_analytics if plan_permissions else False,
        },
        "👥 Party Management": {
            "allow_add_party": plan_permissions.allow_add_party if plan_permissions else False,
            "allow_edit_party": plan_permissions.allow_edit_party if plan_permissions else False,
            "allow_delete_party": plan_permissions.allow_delete_party if plan_permissions else False,
            "max_parties": plan_permissions.max_parties if plan_permissions else 0,
        },
        "💰 Transactions": {
            "allow_add_transaction": plan_permissions.allow_add_transaction if plan_permissions else False,
            "allow_edit_transaction": plan_permissions.allow_edit_transaction if plan_permissions else False,
            "allow_delete_transaction": plan_permissions.allow_delete_transaction if plan_permissions else False,
            "allow_bulk_transaction": plan_permissions.allow_bulk_transaction if plan_permissions else False,
        },
        "📦 Commerce & Warehouse": {
            "allow_commerce": plan_permissions.allow_commerce if plan_permissions else False,
            "allow_warehouse": plan_permissions.allow_warehouse if plan_permissions else False,
            "allow_orders": plan_permissions.allow_orders if plan_permissions else False,
            "allow_inventory": plan_permissions.allow_inventory if plan_permissions else False,
        },
        "📱 Communication": {
            "allow_whatsapp": plan_permissions.allow_whatsapp if plan_permissions else False,
            "allow_sms": plan_permissions.allow_sms if plan_permissions else False,
            "allow_email": plan_permissions.allow_email if plan_permissions else False,
        },
        "📊 Ledger & Credit": {
            "allow_ledger": plan_permissions.allow_ledger if plan_permissions else False,
            "allow_credit_report": plan_permissions.allow_credit_report if plan_permissions else False,
        },
        "🔧 Admin & Settings": {
            "allow_settings": plan_permissions.allow_settings if plan_permissions else False,
            "allow_users": plan_permissions.allow_users if plan_permissions else False,
            "allow_api_access": plan_permissions.allow_api_access if plan_permissions else False,
        },
    }
    
    return render(request, "core_settings/user_permissions.html", {
        "user_plan": user_plan,
        "permission_categories": permission_categories,
    })


# ---------------- Unified Settings Center ----------------

@login_required
def settings_center(request):
    if (not (request.user.is_staff or request.user.is_superuser)) and (not has_feature(request.user, "settings.advanced")):
        return HttpResponse("Your plan does not allow Settings access")
    payload = get_settings_payload(request.user)
    ai_hints = build_ai_hints(payload)
    status_cards = get_status_cards(payload)
    if request.user.is_staff or request.user.is_superuser:
        open_alerts = FraudAlert.objects.filter(status=FraudAlert.Status.OPEN).count()
    else:
        open_alerts = FraudAlert.objects.filter(owner=request.user, status=FraudAlert.Status.OPEN).count()
    return render(request, "core_settings/settings_dashboard.html", {
        "settings_payload": payload,
        "ai_hints": ai_hints,
        "status_cards": status_cards,
        "open_alerts_count": open_alerts,
    })


@login_required
def api_settings_all(request):
    payload = get_settings_payload(request.user)
    response = {
        "status": "ok",
        "settings": payload,
        "ai_hints": build_ai_hints(payload),
        "status_cards": get_status_cards(payload),
    }
    return JsonResponse(response)


@login_required
@require_POST
def api_settings_update(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    action = payload.get("action", "update")
    if action == "undo":
        key = payload.get("key")
        if not key:
            return JsonResponse({"status": "error", "message": "Missing key"}, status=400)
        value = undo_last_change(request.user, key)
        if value is None:
            return JsonResponse({"status": "error", "message": "Nothing to undo"}, status=400)
        return JsonResponse({"status": "ok", "key": key, "value": value})

    updates = payload.get("updates", [])
    results = apply_updates(request.user, updates)
    return JsonResponse({"status": "ok", "results": results})
