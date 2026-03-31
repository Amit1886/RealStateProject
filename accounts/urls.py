# accounts/urls.py
from django.urls import path
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from realstateproject.lazy_views import lazy_view

app_name = "accounts"

# Simple fallback for features not available in this build.
def upgrade_redirect(request, *args, **kwargs):
    return redirect("billing:upgrade_plan")

urlpatterns = [
    path("signup/", lazy_view("accounts.views.signup_view"), name="signup"),
    path("login/", lazy_view("accounts.views.login_view"), name="login"),
    path("verify-otp/", lazy_view("accounts.views.verify_otp_view"), name="verify_otp"),
    path("logout/", lazy_view("accounts.views.logout_view"), name="logout"),
    path("dashboard/", lazy_view("accounts.views.dashboard"), name="dashboard"),
    path("dashboard/admin-action/", lazy_view("accounts.views.admin_dashboard_action"), name="admin_dashboard_action"),
    path("leads/<int:lead_id>/crm/", lazy_view("accounts.views.lead_workspace"), name="lead_workspace"),
    path("leads/<int:lead_id>/crm/action/", lazy_view("accounts.views.lead_workspace_action"), name="lead_workspace_action"),
    path("properties/<int:property_id>/workspace/", lazy_view("accounts.views.property_workspace"), name="property_workspace"),
    path("deals/<int:deal_id>/workspace/", lazy_view("accounts.views.deal_workspace"), name="deal_workspace"),
    path("agents/<int:agent_id>/workspace/", lazy_view("accounts.views.agent_workspace"), name="agent_workspace"),
    path("reports/workspace/", lazy_view("accounts.views.reports_workspace"), name="reports_workspace"),
    path("settings/workspace/", lazy_view("accounts.views.settings_workspace"), name="settings_workspace"),
    path("wallet/workspace/", lazy_view("accounts.views.wallet_workspace"), name="wallet_workspace"),
    path("wallet/workspace/spin/", csrf_exempt(lazy_view("accounts.views.wallet_spin_api")) if (getattr(settings, "DESKTOP_MODE", False) or getattr(settings, "RUNNING_RUNSERVER", False)) else lazy_view("accounts.views.wallet_spin_api"), name="wallet_spin_api"),
    path("wallet/workspace/scratch/reveal/", csrf_exempt(lazy_view("accounts.views.wallet_scratch_reveal_api")) if (getattr(settings, "DESKTOP_MODE", False) or getattr(settings, "RUNNING_RUNSERVER", False)) else lazy_view("accounts.views.wallet_scratch_reveal_api"), name="wallet_scratch_reveal_api"),
    path("wallet/workspace/scratch/claim/", csrf_exempt(lazy_view("accounts.views.wallet_scratch_claim_api")) if (getattr(settings, "DESKTOP_MODE", False) or getattr(settings, "RUNNING_RUNSERVER", False)) else lazy_view("accounts.views.wallet_scratch_claim_api"), name="wallet_scratch_claim_api"),
    path(
        "wallet/workspace/action/",
        csrf_exempt(lazy_view("accounts.views.wallet_workspace_action"))
        if (getattr(settings, "DESKTOP_MODE", False) or getattr(settings, "RUNNING_RUNSERVER", False))
        else lazy_view("accounts.views.wallet_workspace_action"),
        name="wallet_workspace_action",
    ),
    path("role-dashboard/", lazy_view("accounts.views.role_dashboard"), name="role_dashboard"),
    path("collector-dashboard/", lazy_view("accounts.views.collector_dashboard"), name="collector_dashboard"),
    path("edit-profile/", lazy_view("accounts.views.edit_profile"), name="edit_profile"),
    path("business-snapshot/", lazy_view("accounts.views.business_snapshot_view"), name="business_snapshot"),
    path("loyalty/", lazy_view("accounts.views.loyalty_dashboard"), name="loyalty_dashboard"),
    path("redeem-points/", lazy_view("accounts.views.redeem_points"), name="redeem_points"),
    # Ledger/party views
    path("ledger/", lazy_view("accounts.views.ledger_list"), name="ledger_list"),
    path("party/<int:party_id>/ledger/", lazy_view("accounts.views.party_ledger"), name="party_ledger"),
    path("party/<int:party_id>/ledger/pdf/", lazy_view("accounts.views.party_ledger_pdf"), name="party_ledger_pdf"),
    path("party/<int:party_id>/ledger/load-more/", lazy_view("accounts.views.party_ledger_load_more"), name="party_ledger_load_more"),
    # Expenses
    path("expenses/", lazy_view("accounts.views.expense_list"), name="expense_list"),
    path("expenses/create/", lazy_view("accounts.views.create_expense"), name="expense_create"),
    # Stubs for optional features referenced in templates
    path("ledger/ui/", upgrade_redirect, name="ledger_ui"),
    path("loyalty/upgrade/", upgrade_redirect, name="membership_upgrade"),
    path("expenses/<int:pk>/", upgrade_redirect, name="expense_view"),
    path("expenses/<int:pk>/edit/", upgrade_redirect, name="expense_edit"),
    path("expenses/<int:pk>/delete/", upgrade_redirect, name="expense_delete"),
]

