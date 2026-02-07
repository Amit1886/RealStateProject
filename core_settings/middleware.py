from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from billing.services import user_has_feature


class FeatureGateMiddleware(MiddlewareMixin):
    FEATURE_MAP = [
        ("/app/party/", "commerce.suppliers"),
        ("/app/transactions/", "billing.invoices"),
        ("/commerce/product", "commerce.inventory"),
        ("/commerce/orders", "commerce.orders"),
        ("/commerce/sales", "commerce.orders"),
        ("/commerce/purchase", "commerce.orders"),
        ("/reports/", "reports.advanced"),
        ("/settings/", "settings.advanced"),
        ("/chatbot/flows/", "chatbot.flows"),
    ]

    def process_request(self, request):
        if not request.user.is_authenticated:
            return None

        path = request.path
        upgrade_url = reverse("billing:upgrade_plan")

        for prefix, feature_key in self.FEATURE_MAP:
            if path.startswith(prefix):
                if not user_has_feature(request.user, feature_key):
                    return redirect(upgrade_url)
                break
        return None
