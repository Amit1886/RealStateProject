import logging

from rest_framework import decorators, permissions, response, viewsets
from rest_framework.views import APIView

from .models import AIQueryLog, CustomerRiskScore, DemandForecast, ProductDemandForecast, SalesmanScore
from .serializers import (
    AIQueryLogSerializer,
    CustomerRiskScoreSerializer,
    DemandForecastSerializer,
    ProductDemandForecastSerializer,
    SalesmanScoreSerializer,
)
from .services.credit_risk_engine import calculate_credit_risk_scores
from .services.forecast_engine import generate_demand_forecast
from .services.salesman_performance_engine import calculate_salesman_scores
from .services.business_ai import ask_business_ai

logger = logging.getLogger(__name__)


class AIQueryLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AIQueryLog.objects.select_related("user").all()
    serializer_class = AIQueryLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    @decorators.action(detail=False, methods=["post"])
    def ask(self, request):
        question = request.data.get("question", "")
        answer = ask_business_ai(question)
        log = AIQueryLog.objects.create(user=request.user, question=question, answer=answer)
        return response.Response(self.get_serializer(log).data)


class DemandForecastViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DemandForecast.objects.select_related("product").all()
    serializer_class = DemandForecastSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProductDemandForecastViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductDemandForecast.objects.select_related("product").all()
    serializer_class = ProductDemandForecastSerializer
    permission_classes = [permissions.IsAuthenticated]


class CustomerRiskScoreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomerRiskScore.objects.select_related("customer").all()
    serializer_class = CustomerRiskScoreSerializer
    permission_classes = [permissions.IsAuthenticated]


class SalesmanScoreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SalesmanScore.objects.select_related("salesman").all()
    serializer_class = SalesmanScoreSerializer
    permission_classes = [permissions.IsAuthenticated]


class ForecastInternalAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        run_flag = str(request.query_params.get("run", "")).lower() in {"1", "true", "yes"}
        data = {"status": "ok"}
        if run_flag:
            try:
                data["run_result"] = generate_demand_forecast(days=7, months=6)
            except Exception as exc:
                logger.exception("Forecast endpoint failure: %s", exc)
                data["run_result"] = {"status": "error", "message": str(exc)}

        items = ProductDemandForecast.objects.select_related("product").order_by("predicted_date", "product_id")[:500]
        data["results"] = ProductDemandForecastSerializer(items, many=True).data
        return response.Response(data)


class CreditRiskInternalAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        run_flag = str(request.query_params.get("run", "")).lower() in {"1", "true", "yes"}
        data = {"status": "ok"}
        if run_flag:
            try:
                data["run_result"] = calculate_credit_risk_scores()
            except Exception as exc:
                logger.exception("Credit risk endpoint failure: %s", exc)
                data["run_result"] = {"status": "error", "message": str(exc)}

        items = CustomerRiskScore.objects.select_related("customer").order_by("-last_calculated", "-risk_score")[:500]
        data["results"] = CustomerRiskScoreSerializer(items, many=True).data
        return response.Response(data)


class SalesmanScoreInternalAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        run_flag = str(request.query_params.get("run", "")).lower() in {"1", "true", "yes"}
        data = {"status": "ok"}
        if run_flag:
            try:
                data["run_result"] = calculate_salesman_scores()
            except Exception as exc:
                logger.exception("Salesman score endpoint failure: %s", exc)
                data["run_result"] = {"status": "error", "message": str(exc)}

        items = SalesmanScore.objects.select_related("salesman").order_by("-calculated_at", "-performance_score")[:500]
        data["results"] = SalesmanScoreSerializer(items, many=True).data
        return response.Response(data)
