from django.contrib import admin

from .models import AIQueryLog, CustomerRiskScore, DemandForecast, ProductDemandForecast, SalesmanScore


class ReadOnlyAIAdmin(admin.ModelAdmin):
    readonly_fields = ()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AIQueryLog)
class AIQueryLogAdmin(ReadOnlyAIAdmin):
    list_display = ("id", "user", "question", "created_at")
    search_fields = ("question", "answer", "user__email")
    readonly_fields = ("user", "question", "answer", "metadata", "created_at")


@admin.register(DemandForecast)
class DemandForecastAdmin(ReadOnlyAIAdmin):
    list_display = ("product", "forecast_date", "predicted_qty", "model_version", "generated_at")
    list_filter = ("model_version", "forecast_date")
    search_fields = ("product__name",)
    readonly_fields = ("product", "forecast_date", "predicted_qty", "confidence", "model_version", "generated_at")


@admin.register(ProductDemandForecast)
class ProductDemandForecastAdmin(ReadOnlyAIAdmin):
    list_display = ("product", "predicted_date", "predicted_quantity", "created_at")
    list_filter = ("predicted_date",)
    search_fields = ("product__name",)
    readonly_fields = ("product", "predicted_date", "predicted_quantity", "created_at")


@admin.register(CustomerRiskScore)
class CustomerRiskScoreAdmin(ReadOnlyAIAdmin):
    list_display = ("customer", "risk_score", "risk_level", "last_calculated")
    list_filter = ("risk_level",)
    search_fields = ("customer__email", "customer__username", "customer__first_name", "customer__last_name")
    readonly_fields = ("customer", "risk_score", "risk_level", "last_calculated")


@admin.register(SalesmanScore)
class SalesmanScoreAdmin(ReadOnlyAIAdmin):
    list_display = ("salesman", "performance_score", "risk_flag", "calculated_at")
    list_filter = ("risk_flag",)
    search_fields = ("salesman__email", "salesman__username", "salesman__first_name", "salesman__last_name")
    readonly_fields = ("salesman", "performance_score", "risk_flag", "calculated_at")
