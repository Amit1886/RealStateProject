# khatapro/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

# Import billing and commerce views for specific routes
from billing import views as billing_views
from commerce import views as commerce_views

urlpatterns = [
    # ---------------- Admin ----------------
    path("admin/", admin.site.urls),

    # ---------------- KhataApp (main features: homepage, parties, transactions, reports) ----------------
    path("", include("khataapp.urls")),

    # ---------------- Accounts (login, signup, dashboard, OTP, etc.) ----------------
    path("accounts/", include("accounts.urls")),

    # ---------------- Billing / Subscription Plans ----------------
     path("billing/", include("billing.urls", namespace="billing")),

    # ---------------- Commerce (orders, products, inventory, etc.) ----------------
    path("commerce/", include("commerce.urls")),

    # ---------------- Social Login (Google, Facebook via social_django) ----------------
    path("oauth/", include("social_django.urls", namespace="social")),

    # ---------------- Logout (default Django auth view) ----------------
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # ---------------- Direct choose-plan routes (optional, can override) ----------------
    path("billing/choose-plan/", billing_views.choose_plan, name="billing_choose_plan"),
]

# ---------------- Media and static files serving (only in DEBUG mode) ----------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
