from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from .models import Company


class CompanyResolverMiddleware(MiddlewareMixin):
    """
    Resolve tenant company per request.
    - First tries header `X-Company-ID`
    - Then subdomain (not implemented here, placeholder)
    - Falls back to user's company after authentication.
    """

    def process_request(self, request):
        company = None

        company_id = request.META.get("HTTP_X_COMPANY_ID")
        if company_id:
            company = Company.objects.filter(id=company_id, active=True).first()

        if not company and request.user and request.user.is_authenticated:
            company = getattr(request.user, "company", None)

        if not company:
            # Soft fail: allow landing/login; block protected areas via views/permissions.
            request.company = None
            return None

        request.company = company
        return None
