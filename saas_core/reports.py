from decimal import Decimal
from django.db.models import Sum, Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from leads.models import Lead
from deals.models import Deal
from deals.models_commission import Commission
from saas_core.api import IsCompanyMember


class SummaryReportView(APIView):
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request):
        company = getattr(request, "company", None)

        lead_qs = Lead.objects.all()
        deal_qs = Deal.objects.all()
        commission_qs = Commission.objects.all()

        if company:
            lead_qs = lead_qs.filter(company=company)
            deal_qs = deal_qs.filter(company=company)
            commission_qs = commission_qs.filter(company=company)

        leads_total = lead_qs.count()
        leads_new = lead_qs.filter(status=Lead.Status.NEW).count() if hasattr(Lead, "Status") else 0

        deals_open = deal_qs.exclude(status=Deal.Status.WON).count() if hasattr(Deal, "Status") else deal_qs.count()
        deals_won = deal_qs.filter(status=Deal.Status.WON).count() if hasattr(Deal, "Status") else 0

        revenue = deal_qs.filter(status=Deal.Status.WON).aggregate(total=Sum("deal_amount"))["total"] or Decimal("0.00")
        commission_total = commission_qs.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")

        return Response(
            {
                "leads_total": leads_total,
                "leads_new": leads_new,
                "deals_open": deals_open,
                "deals_won": deals_won,
                "revenue": revenue,
                "commission_total": commission_total,
            }
        )
