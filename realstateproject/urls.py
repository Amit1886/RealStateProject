# khatapro/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.views.static import serve as django_static_serve
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView
from saas_core.auth import TenantTokenObtainPairView
from realstateproject.lazy_views import lazy_view
from core_settings.health import healthcheck
from django.contrib.staticfiles.views import serve as staticfiles_serve
from django.urls import reverse, NoReverseMatch
from django.urls import path, include

# Fallback upgrade redirect for disabled modules (commerce/khataapp/etc.)
def upgrade_redirect(request, *args, **kwargs):
    try:
        upgrade_url = reverse("billing:upgrade_plan")
    except Exception:
        upgrade_url = "/"
    return HttpResponseRedirect(upgrade_url)

# Global fallbacks for common invoice/payment routes referenced without namespace
root_stub_patterns = [
    path("invoices/", upgrade_redirect, name="invoice_list"),
    path("vouchers/", upgrade_redirect, name="voucher_list"),
    path("payments/", upgrade_redirect, name="payment_list"),
]

# Stub URL patterns for disabled modules to avoid NoReverseMatch in templates.
commerce_stub_patterns = [
    path("add-order/", upgrade_redirect, name="add_order"),
    path("sales-voucher/quick-create/", upgrade_redirect, name="sales_voucher_quick_create"),
    path("add-product/", upgrade_redirect, name="add_product"),
    path("add-payment/", upgrade_redirect, name="add_payment"),
    path("add-invoice/", upgrade_redirect, name="add_invoice"),
    path("invoices/", upgrade_redirect, name="invoice_list"),
    path("vouchers/", upgrade_redirect, name="voucher_list"),
    path("payments/", upgrade_redirect, name="payment_list"),
    path("quotation/create/", upgrade_redirect, name="quotation_create"),
    path("quotation/list/", upgrade_redirect, name="quotation_list"),
    path("orders/", upgrade_redirect, name="order_list"),
    path("invoice/<int:pk>/", upgrade_redirect, name="invoice_view"),
]

khataapp_stub_patterns = [
    path("add-transaction/", upgrade_redirect, name="add_transaction"),
    path("add-party/", upgrade_redirect, name="add_party"),
    path("transactions/", upgrade_redirect, name="transaction_list"),
    path("transactions/<int:pk>/", upgrade_redirect, name="transaction_view"),
    path("transactions/<int:pk>/edit/", upgrade_redirect, name="transaction_edit"),
    path("transactions/<int:pk>/delete/", upgrade_redirect, name="transaction_delete"),
    path("parties/", upgrade_redirect, name="party_list"),
    path("agents/", upgrade_redirect, name="field_agent_list"),
]

central_engine_stub_patterns = [
    path("", upgrade_redirect, name="dashboard"),
    path("rewards-wallet/", upgrade_redirect, name="rewards_wallet"),
    path("referrals/", upgrade_redirect, name="referral_center"),
    path("loyalty-offers/", upgrade_redirect, name="loyalty_offers"),
    path("payment-earnings/", upgrade_redirect, name="payment_earnings"),
    path("tasks/", upgrade_redirect, name="task_center"),
    path("tasks/complete/", upgrade_redirect, name="task_complete"),
    path("analytics/", upgrade_redirect, name="analytics_snapshot"),
    path("feature-unlock/", upgrade_redirect, name="feature_unlock_panel"),
    path("profit-preview/", upgrade_redirect, name="profit_preview"),
    path("admin/control-center/", upgrade_redirect, name="admin_control_center"),
    path("admin/logs/", upgrade_redirect, name="admin_logs"),
]

smart_khata_stub_patterns = [
    path("credit-score/", upgrade_redirect, name="credit_score_dashboard"),
    path("reminder-logs/", upgrade_redirect, name="reminder_logs"),
    path("reminder-activity/", upgrade_redirect, name="report_reminder_activity"),
    path("late-payments/", upgrade_redirect, name="report_late_payments"),
    path("high-risk-customers/", upgrade_redirect, name="report_high_risk_customers"),
    path("ranking/", upgrade_redirect, name="report_credit_ranking"),
    path("reminder-settings/", upgrade_redirect, name="khata_reminder_settings"),
    path("customers/", upgrade_redirect, name="customer_list"),
    path("customers/<int:pk>/", upgrade_redirect, name="customer_profile"),
]

ledger_stub_patterns = [
    path("stock-transfers/", upgrade_redirect, name="stock_transfer_list"),
    path("stock-transfers/new/", upgrade_redirect, name="stock_transfer_create"),
    path("stock-transfers/<int:pk>/", upgrade_redirect, name="stock_transfer_detail"),
    path("stock-transfers/<int:pk>/edit/", upgrade_redirect, name="stock_transfer_edit"),
    path("stock-transfers/<int:pk>/post/", upgrade_redirect, name="stock_transfer_post"),
    path("stock-transfers/<int:pk>/cancel/", upgrade_redirect, name="stock_transfer_cancel"),
    path("journal-vouchers/", upgrade_redirect, name="journal_voucher_list"),
    path("journal-vouchers/new/", upgrade_redirect, name="journal_voucher_create"),
    path("journal-vouchers/<int:pk>/", upgrade_redirect, name="journal_voucher_detail"),
    path("journal-vouchers/<int:pk>/edit/", upgrade_redirect, name="journal_voucher_edit"),
    path("journal-vouchers/<int:pk>/post/", upgrade_redirect, name="journal_voucher_post"),
    path("journal-vouchers/<int:pk>/cancel/", upgrade_redirect, name="journal_voucher_cancel"),
    path("credit-notes/", upgrade_redirect, name="credit_note_list"),
    path("credit-notes/new/", upgrade_redirect, name="credit_note_create"),
    path("debit-notes/", upgrade_redirect, name="debit_note_list"),
    path("debit-notes/new/", upgrade_redirect, name="debit_note_create"),
    path("return-notes/<int:pk>/", upgrade_redirect, name="return_note_detail"),
    path("return-notes/<int:pk>/edit/", upgrade_redirect, name="return_note_edit"),
    path("return-notes/<int:pk>/post/", upgrade_redirect, name="return_note_post"),
    path("return-notes/<int:pk>/cancel/", upgrade_redirect, name="return_note_cancel"),
    path("receipts/<int:pk>/", upgrade_redirect, name="receipt"),
]

report_stub_patterns = [
    path("all-transactions/", upgrade_redirect, name="all_transactions"),
]

reports_stub_patterns = [
    path("all-transactions/", upgrade_redirect, name="all_transactions"),
    path("cash-book/", upgrade_redirect, name="cash_book"),
    path("vouchers/", upgrade_redirect, name="voucher_report"),
    path("sales/", upgrade_redirect, name="sales_report"),
    path("purchase/", upgrade_redirect, name="purchase_report"),
    path("quotations/", upgrade_redirect, name="quotation_report"),
    path("stock-summary/", upgrade_redirect, name="stock_summary"),
    path("low-stock/", upgrade_redirect, name="low_stock"),
    path("party-ledger/", upgrade_redirect, name="party_ledger"),
    path("outstanding/", upgrade_redirect, name="outstanding"),
    path("profit-loss/", upgrade_redirect, name="profit_loss"),
    path("day-book/", upgrade_redirect, name="day_book"),
    path("trial-balance/", upgrade_redirect, name="erp_trial_balance"),
    path("account-summary/", upgrade_redirect, name="account_summary"),
    path("interest/", upgrade_redirect, name="interest_calculation"),
    path("inventory/books/", upgrade_redirect, name="inventory_books"),
    path("inventory/summary/", upgrade_redirect, name="inventory_summary"),
    path("gst/", upgrade_redirect, name="gst_report"),
    path("mis/", upgrade_redirect, name="mis_report"),
    path("checklists/", upgrade_redirect, name="checklist_list"),
    path("checklists/<int:pk>/", upgrade_redirect, name="checklist_detail"),
    path("checklists/<int:checklist_id>/<int:item_id>/toggle/", upgrade_redirect, name="checklist_item_toggle"),
    path("queries/", upgrade_redirect, name="query_list"),
    path("queries/new/", upgrade_redirect, name="query_create"),
    path("queries/<int:pk>/", upgrade_redirect, name="query_detail"),
]

ai_insights_stub_patterns = [
    path("", upgrade_redirect, name="dashboard"),
]

ai_ocr_stub_patterns = [
    path("", upgrade_redirect, name="dashboard"),
]

whatsapp_stub_patterns = [
    path("", upgrade_redirect, name="dashboard"),
    path("control-center/", upgrade_redirect, name="control_center"),
]

portal_stub_patterns = [
    path("suppliers/", upgrade_redirect, name="manage_suppliers"),
    path("customers/", upgrade_redirect, name="manage_customers"),
    path("password/change/", upgrade_redirect, name="change_password"),
    path("suppliers/dashboard/", upgrade_redirect, name="supplier_dashboard"),
    path("customers/dashboard/", upgrade_redirect, name="customer_dashboard"),
]

procurement_stub_patterns = [
    path("supplier-price-comparison/", upgrade_redirect, name="supplier_price_comparison"),
    path("supplier-product-mapping/", upgrade_redirect, name="supplier_product_mapping"),
]

bank_import_stub_patterns = [
    path("import/", upgrade_redirect, name="import"),
]

core_settings_stub_patterns = [
    path("center/", lazy_view("core_settings.views.settings_center"), name="settings_center"),
    path("feature-controls/", lazy_view("core_settings.views.feature_control_tower"), name="feature_control_tower"),
    path("plans/", lazy_view("core_settings.views.plan_permissions_view"), name="plan_permissions"),
    path("user-overrides/", lazy_view("core_settings.views.user_feature_overrides_view"), name="user_feature_overrides"),
    path("permissions/", lazy_view("core_settings.views.user_permissions_view"), name="user_permissions"),
    path("", lazy_view("core_settings.views.settings_dashboard"), name="dashboard"),
    path("api/settings/all/", lazy_view("core_settings.views.api_settings_all"), name="api_settings_all"),
    path("api/settings/update/", lazy_view("core_settings.views.api_settings_update"), name="api_settings_update"),
]

smart_bi_stub_patterns = [
    path("business-health/", upgrade_redirect, name="business_health_dashboard"),
    path("duplicate-invoices/", upgrade_redirect, name="duplicate_invoice_report"),
    path("festival-campaigns/", upgrade_redirect, name="festival_campaign_list"),
    # Extra Smart BI links referenced from sidebar/templates
    path("festival-sales/", upgrade_redirect, name="festival_sales_report"),
    path("duplicate-invoices/settings/", upgrade_redirect, name="duplicate_invoice_settings"),
]

def landing(request):
    # Landing page download button (public): show only if a published bundle exists.
    desktop_download_url = ""
    desktop_download_label = ""
    android_download_url = ""
    android_download_label = ""
    try:
        from core_settings.models import DesktopRelease

        rel = DesktopRelease.objects.filter(pk=1).first()
        if rel and rel.is_published:
            if rel.windows_exe:
                desktop_download_url = reverse("desktop-release-public-download")
                desktop_download_label = f"Download Desktop ({rel.version})"
            if getattr(rel, "android_apk", None):
                android_download_url = reverse("android-release-public-download")
                android_download_label = f"Download APK ({rel.version})"
    except Exception:
        desktop_download_url = ""
        desktop_download_label = ""
        android_download_url = ""
        android_download_label = ""

    if getattr(settings, "DESKTOP_MODE", False):
        return render(
            request,
            "core/desktop_splash.html",
            {"desktop_app_version": getattr(settings, "DESKTOP_APP_VERSION", "0.0.0")},
        )
    return render(
        request,
        "core/landing.html",
        {
            "desktop_app_version": getattr(settings, "DESKTOP_APP_VERSION", "0.0.0"),
            "desktop_download_url": desktop_download_url,
            "desktop_download_label": desktop_download_label or "Download Desktop App",
            "android_download_url": android_download_url,
            "android_download_label": android_download_label or "Download Android APK",
        },
    )

def privacy(request):
    return render(request, "core/privacy.html")

def terms(request):
    return render(request, "core/terms.html")


urlpatterns = [
    path("health/", healthcheck, name="healthcheck"),
    # ---------------- Mobile APP ----------------
    # path("api/", include("mobileapi.urls")),
    # path("api/", include("system_mode.urls")),
    # Disabled legacy APIs not used in real-estate build
    # path("api/", include("procurement.api_urls")),
    # path("api/", include("smart_khata.api_urls")),
    # path("api/", include("smart_bi.api_urls")),
    # path("api/", include("khataapp.core_engine.api_urls")),
    # path("api/whatsapp/order-inbox/", commerce_views.api_whatsapp_order_inbox, name="api_whatsapp_order_inbox"),
    path("api/whatsapp/accounting/webhook/", lazy_view("whatsapp.views.whatsapp_accounting_webhook"), name="whatsapp_accounting_webhook"),
    path("api/whatsapp/webhook/", lazy_view("whatsapp.views.whatsapp_unified_webhook"), name="whatsapp_unified_webhook"),
    path("api/whatsapp/meta/<uuid:account_id>/webhook/", lazy_view("whatsapp.webhooks.whatsapp_meta_webhook"), name="whatsapp_meta_webhook"),
    path("api/whatsapp/gateway/<uuid:account_id>/inbound/", lazy_view("whatsapp.webhooks.whatsapp_gateway_inbound_webhook"), name="whatsapp_gateway_inbound_webhook"),
    path("api/voice/command/", lazy_view("voice.views.api_voice_command"), name="api_voice_command"),
    # path("api/orders/live-feed/", commerce_views.api_orders_live_feed, name="api_orders_live_feed"),

    # ---------------- API Docs & Auth ----------------
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="api-schema"), name="api-redoc"),
    path("api/auth/login/", TenantTokenObtainPairView.as_view(), name="api-login"),
    path("api/auth/token/", TenantTokenObtainPairView.as_view(), name="jwt-token"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="jwt-refresh"),
    path("api/assign/geo/", lazy_view("leads.views.LeadGeoAssignAPIView"), name="api-assign-geo"),
    path("api/photo-to-lead/", lazy_view("leads.views.PhotoToLeadAPIView"), name="api-photo-to-lead"),
    path("api/lead/lock/", lazy_view("leads.views.LeadLockAPIView"), name="api-lead-lock"),
    path("api/lead/unlock/", lazy_view("leads.views.LeadUnlockAPIView"), name="api-lead-unlock"),
    path("api/leaderboard/", lazy_view("crm.views.LeaderboardAPIView"), name="api-leaderboard"),
    path("api/agent/stats/", lazy_view("crm.views.AgentStatsAPIView"), name="api-agent-stats"),
    path("api/invoice/create/", lazy_view("billing.api_views.InvoiceCreateAPIView"), name="api-invoice-create"),
    path("api/payment/link/", lazy_view("payments.views.PaymentLinkAPIView"), name="api-payment-link"),
    path("api/payment/webhook/", lazy_view("payments.views.webhook_any"), name="api-payment-webhook"),
    path("api/v1/", include(("saas_core.api_urls", "saas_core"), namespace="saas_core_api")),

    # ---------------- Universal SaaS APIs ----------------
    path("api/v1/users/", include("users.urls")),
    path("api/v1/customers/", include("customers.urls")),
    path("api/v1/location/", include("location.urls")),
    path("api/v1/hierarchy/", include("hierarchy.urls")),
    path("api/v1/leads/", include("leads.urls")),
    path("api/v1/marketing/", include("marketing.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
    path("api/v1/communication/", include("communication.urls")),
    path("api/v1/intelligence/", include("intelligence.urls")),
    path("api/v1/loans/", include("loans.urls")),
    path("api/v1/verification/", include("verification.urls")),
    path("api/v1/schemes/", include("schemes.urls")),
    path("api/v1/content/", include("content.urls")),
    path("api/v1/fraud/", include("fraud_detection.urls")),
    path("api/v1/integrations/", include("api_integrations.urls")),
    path("api/v1/wallet/", include("wallet.urls")),
    path("api/v1/payments/", include("payments.api_urls")),
    path("api/v1/kyc/", include("kyc.api_urls")),
    path("api/v1/billing/", include("billing.api_urls")),
    path("api/v1/crm/", include("crm.urls")),
    path("api/v1/voice/", include("voice.api_urls")),
    path("api/v1/reviews/", include("reviews.urls")),
    path("api/v1/subscription/", include("subscription.urls")),
    # path("api/v1/performance/", include("performance.urls")),
    # Disabled legacy commerce stack
    # path("api/v1/pos/", include("pos.urls")),
    # path("api/v1/printers/", include("printer_config.urls")),
    # path("api/v1/scanners/", include("scanner_config.urls")),
    # path("api/v1/warehouses/", include("warehouse.urls")),
    # path("api/v1/whatsapp/", include("whatsapp.api_urls")),
    # path("api/v1/orders/", include("orders.urls")),
    # path("api/v1/commission/", include("commission.urls")),
    # path("api/v1/payments/", include("payments.urls")),
    # path("api/v1/analytics/", include("analytics.urls")),
    # path("api/v1/ai/", include("ai_engine.urls")),
    # path("api/v1/realtime/", include("realtime.urls")),
    path("api/v1/agents/", include("agents.urls")),
    path("api/v1/payouts/", include("payouts.urls")),
    path("api/v1/rewards/", include("rewards.urls")),
    path("api/v1/visits/", include("visits.urls")),
    path("api/v1/deals/", include("deals.urls")),
    # ---------------- Desktop Releases (Cloud -> Desktop) ----------------
    path("api/v1/desktop/releases/latest/", lazy_view("core_settings.desktop_release_views.latest_desktop_release_api"), name="desktop-release-latest"),
    path("api/v1/desktop/releases/download/", lazy_view("core_settings.desktop_release_views.download_desktop_release"), name="desktop-release-download"),
    path("download/desktop/", lazy_view("core_settings.desktop_release_views.public_download_desktop_release"), name="desktop-release-public-download"),
    # ---------------- Android APK Releases (Cloud -> Mobile) ----------------
    path("api/v1/android/releases/latest/", lazy_view("core_settings.desktop_release_views.latest_android_release_api"), name="android-release-latest"),
    path("api/v1/android/releases/download/", lazy_view("core_settings.desktop_release_views.download_android_release"), name="android-release-download"),
    path("download/apk/", lazy_view("core_settings.desktop_release_views.public_download_android_release"), name="android-release-public-download"),

    # ---------------- POS UI ----------------
    # path("pos/ui/", POSView.as_view(), name="pos-ui"),
    # # Sales aliases disabled
    # path("sales/order/create/", commerce_views.add_order, name="sales_order_create_root"),
    # # Admin addons disabled
    # path("superadmin/chatbot/", include("chatbot.urls")),
    # ---------------- Admin ----------------
    path('superadmin/', admin.site.urls),  # ✅ New admin URL

    # ---------------- KhataApp (homepage, parties, transactions, reports) ----------------
    # path("app/khata/", include(("smart_khata.urls", "smart_khata"), namespace="smart_khata")),
    # path("app/engine/", include(("khataapp.core_engine.urls", "central_engine"), namespace="central_engine")),
    # path("app/", include("khataapp.urls")),
    path("", landing, name="landing"),   # 👈 HOME PAGE
    path("privacy-policy/", privacy),
    path("terms/", terms),
    
    # ---------------- Accounts (login/signup/dashboard) ----------------
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("billing/", include(("billing.urls", "billing"), namespace="billing")),
    path("payments/", include(("payments.urls", "payments"), namespace="payments")),
    path("kyc/", include(("kyc.urls", "kyc"), namespace="kyc")),
    # Root fallbacks (non-namespaced)
    *root_stub_patterns,
    # Fallback stubs so dashboard links resolve even when modules are disabled
    path("commerce/", include((commerce_stub_patterns, "commerce"), namespace="commerce")),
    path("khataapp/", include((khataapp_stub_patterns, "khataapp"), namespace="khataapp")),
    path("engine/", include((central_engine_stub_patterns, "central_engine"), namespace="central_engine")),
    path("app/khata/", include((smart_khata_stub_patterns, "smart_khata"), namespace="smart_khata")),
    path("ledger/", include((ledger_stub_patterns, "ledger"), namespace="ledger")),
    path("report/", include((report_stub_patterns, "report"), namespace="report")),
    path("reports/", include((reports_stub_patterns, "reports"), namespace="reports")),
    path("ai-tools/insights/", include((ai_insights_stub_patterns, "ai_insights"), namespace="ai_insights")),
    path("ai-tools/ocr/", include((ai_ocr_stub_patterns, "ai_ocr"), namespace="ai_ocr")),
    path("ai-tools/whatsapp/", include((whatsapp_stub_patterns, "whatsapp"), namespace="whatsapp")),
    path("portal/", include((portal_stub_patterns, "portal"), namespace="portal")),
    path("procurement/", include((procurement_stub_patterns, "procurement"), namespace="procurement")),
    path("bank-import/", include((bank_import_stub_patterns, "bank_import"), namespace="bank_import")),
    path("core-settings/", include((core_settings_stub_patterns, "core_settings"), namespace="core_settings")),
    path("smart-bi/", include((smart_bi_stub_patterns, "smart_bi"), namespace="smart_bi")),
    # Legacy alias used by older redirects (avoid NoReverseMatch for "dashboard")
    path(
        "dashboard/",
        RedirectView.as_view(pattern_name="accounts:dashboard", permanent=False),
        name="dashboard",
    ),

    # ---------------- Social Login (Google, Facebook via social_django) ----------------
    path('accounts/', include('allauth.urls')),

    # ---------------- Logout (default Django auth view) ----------------
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path("favicon.ico", RedirectView.as_view(url="/static/img/favicon.ico")),
    path("chatbot/flows/", RedirectView.as_view(url="/superadmin/chatbot/flows/", permanent=True)),
    path(
        "chatbot/flows/<int:flow_id>/builder/",
        RedirectView.as_view(pattern_name="chatbot_flow_builder", permanent=True),
    ),
    path(
        "chatbot/flows/create/",
        RedirectView.as_view(pattern_name="chatbot_flow_create", permanent=True),
    ),
    path(
        "chatbot/flows/<int:flow_id>/save/",
        RedirectView.as_view(pattern_name="chatbot_flow_save", permanent=True),
    ),
    path("superadmin/chatbot/", include("chatbot.urls")),
    path("chatbot/", RedirectView.as_view(url="/superadmin/chatbot/", permanent=True)),

    # ---------------- AI Tools & Automation ----------------
    # path("ai-tools/insights/", include(("ai_insights.urls", "ai_insights"), namespace="ai_insights")),
    # path("ai-tools/ocr/", include(("ai_ocr.urls", "ai_ocr"), namespace="ai_ocr")),
    path("ai-tools/voice/", include(("voice.urls", "voice"), namespace="voice")),
    # path("ai-tools/whatsapp/", include(("whatsapp.urls", "whatsapp"), namespace="whatsapp")),
    path("ai-tools/alerts/", include(("validation.urls", "validation"), namespace="validation")),

    # Short alias requested: WhatsApp Setup Wizard in Django dashboard
    path("whatsapp/setup/", lazy_view("whatsapp.setup_views.whatsapp_setup_wizard"), name="whatsapp_setup_wizard_alias"),
    path("whatsapp/", include("whatsapp_gateway.urls")),
]

# ---------------- Media and static files serving (local/dev + Desktop Mode) ----------------
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", django_static_serve, {"document_root": settings.MEDIA_ROOT}),
]
if getattr(settings, "SERVE_STATICFILES", False):
    # Use staticfiles finders so assets can be served from:
    # - %LOCALAPPDATA%\JaisTechKhataBook\static (desktop persisted)
    # - bundled _MEIPASS/static (PyInstaller)
    # - app static directories (installed apps)
    urlpatterns += [
        re_path(r"^static/(?P<path>.*)$", staticfiles_serve, {"insecure": True}),
    ]
