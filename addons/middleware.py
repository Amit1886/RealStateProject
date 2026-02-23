from django.utils.deprecation import MiddlewareMixin

try:  # Ensure critical hotfixes apply even when addons flag is off.
    from addons.hotfixes.patches import accounts_dashboard  # noqa: F401
except Exception:  # pragma: no cover
    accounts_dashboard = None


class AddonsURLRoutingMiddleware(MiddlewareMixin):
    """Route /addons/* requests to the isolated addons urlconf."""

    addons_prefix = "/addons/"
    demo_prefix = "/demo/"
    addons_urlconf = "addons.urls"

    def process_request(self, request):
        if request.path.startswith(self.addons_prefix) or request.path.startswith(self.demo_prefix):
            request.urlconf = self.addons_urlconf
        return None
