# khatapro/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.shortcuts import render
from khataapp.views import submit_contact
from core_settings import views



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
    # ---------------- Admin ----------------
    path('superadmin/', admin.site.urls),  # ✅ New admin URL

    # ---------------- KhataApp (homepage, parties, transactions, reports) ----------------
    path("app/", include("khataapp.urls")),
    path("", landing, name="landing"),   # 👈 HOME PAGE
    path("privacy-policy/", privacy),
    path("terms/", terms),


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
    path("chatbot/", include("chatbot.urls")),

    # ---------------- Contact Form Home Page Landing Page  ----------------
    path("contact/submit/", submit_contact, name="contact_submit"),

    # ---------------- Core Setting   ----------------
    path("settings/", views.settings_dashboard, name="settings"),
]

# ---------------- Media and static files serving (only in DEBUG mode) ----------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
