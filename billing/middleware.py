# full path: /home/Khataapp/myproject/khatapro/billing/middleware.py

from django.shortcuts import redirect

class AdminAccessControlMiddleware:
    """
    Prevent non-staff users from accessing the Django admin.
    Staff users (is_staff=True) can access /admin/ normally.
    Non-staff users are redirected to the user dashboard.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # If request is for the admin area and user is not staff -> redirect
        if request.path.startswith('/admin/') and not request.user.is_staff:
            return redirect('/accounts/dashboard/')
        return self.get_response(request)
