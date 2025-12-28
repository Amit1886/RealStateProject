# ~/myproject/khatapro/khataapp/middleware.py

from django.shortcuts import redirect
from django.urls import reverse

class RestrictAdminMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # If user tries to access old admin URL
        if request.path.startswith('/admin/') and request.user.is_authenticated:
            # If not a superuser → redirect to commerce dashboard
            if not request.user.is_superuser:
                return redirect(reverse('billing:commerce_dashboard'))
        
        # If a staff user or normal user tries to access superadmin (optional block)
        if request.path.startswith('/superadmin/') and request.user.is_authenticated:
            if not request.user.is_superuser:
                return redirect(reverse('billing:commerce_dashboard'))

        return self.get_response(request)
