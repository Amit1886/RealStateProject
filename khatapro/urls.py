# khatapro/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.shortcuts import render
from khataapp.views import submit_contact

# Import billing and commerce views for specific routes
from billing import views as billing_views
from commerce import views as commerce_views

def landing(request):
    return render(request, "core/landing.html")

def privacy(request):
    return render(request, "core/privacy.html")

def terms(request):
    return render(request, "core/terms.html")


urlpatterns = [
    # ---------------- Mobile APP ----------------
    path("api/", include("mobileapi.urls")),
    path("api/whatsapp/order-inbox/", commerce_views.api_whatsapp_order_inbox, name="api_whatsapp_order_inbox"),
    path("api/orders/live-feed/", commerce_views.api_orders_live_feed, name="api_orders_live_feed"),
    # ---------------- Admin Addons (must come before admin.site.urls) ----------------
    path("superadmin/chatbot/", include("chatbot.urls")),
    # ---------------- Admin ----------------
    path('superadmin/', admin.site.urls),  # ✅ New admin URL

    # ---------------- KhataApp (homepage, parties, transactions, reports) ----------------
    path("app/", include("khataapp.urls")),
    path("", landing, name="landing"),   # 👈 HOME PAGE
    path("privacy-policy/", privacy),
    path("terms/", terms),
    
    # ---------------- Reports ----------------
    path('reports/', include(('reports.urls', 'reports'), namespace='reports')),


    # ---------------- Accounts (login, signup, dashboard, OTP, etc.) ----------------
    path('accounts/', include('accounts.urls', namespace='accounts')),

    # ---------------- Billing / Subscription Plans ----------------
    path("billing/", include(("billing.urls", "billing"), namespace="billing")),

    # ---------------- Commerce (orders, products, inventory, etc.) ----------------
    path('commerce/', include('commerce.urls', namespace='commerce')),

    # ---------------- Social Login (Google, Facebook via social_django) ----------------
    path('accounts/', include('allauth.urls')),

    # ---------------- Logout (default Django auth view) ----------------
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # ---------------- Direct choose-plan routes (optional, can override) ----------------
    path("billing/choose-plan/", billing_views.choose_plan, name="billing_choose_plan"),
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.ico")),
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

    # ---------------- Contact Form Home Page Landing Page  ----------------
    path("contact/submit/", submit_contact, name="contact_submit"),

    # ---------------- Core Settings (Dashboard, Permissions, Plan Management) ----------------
    path("settings/", include(("core_settings.urls", "core_settings"), namespace="core_settings")),
]

# ---------------- Media and static files serving (only in DEBUG mode) ----------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
