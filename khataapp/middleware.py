from django.shortcuts import redirect
from django.urls import reverse


class RestrictAdminMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # --------------------------------
        # 🚨 OTP Firewall (highest priority)
        # --------------------------------
        if request.user.is_authenticated and not request.user.is_active:
            # Allow only OTP pages
            if not request.path.startswith("/accounts/verify-otp") and not request.path.startswith("/accounts/logout"):
                return redirect(reverse("accounts:verify_otp"))

        # --------------------------------
        # Admin access protection
        # --------------------------------
        if request.path.startswith('/admin/') and request.user.is_authenticated:
            if not request.user.is_superuser:
                return redirect(reverse('billing:commerce_dashboard'))

        if request.path.startswith('/superadmin/') and request.user.is_authenticated:
            if not request.user.is_superuser:
                return redirect(reverse('billing:commerce_dashboard'))

        return self.get_response(request)
