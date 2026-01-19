from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from core_settings.permissions import has_feature
from core_settings.models import CompanySettings, UISettings, AppSettings
from khataapp.models import UserProfile
from billing.models import Plan, PlanPermissions


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
    if not has_feature(request.user, "settings"):
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
    
    plans = Plan.objects.filter(active=True).prefetch_related('permissions')
    
    return render(request, "core_settings/plan_permissions.html", {
        "plans": plans,
    })


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
