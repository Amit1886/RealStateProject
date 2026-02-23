from rest_framework import serializers

from .models import AIQueryLog, CustomerRiskScore, DemandForecast, ProductDemandForecast, SalesmanScore


class AIQueryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIQueryLog
        fields = "__all__"


class DemandForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandForecast
        fields = "__all__"


class ProductDemandForecastSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = ProductDemandForecast
        fields = "__all__"


class CustomerRiskScoreSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomerRiskScore
        fields = "__all__"

    def get_customer_name(self, obj):
        return obj.customer.get_full_name() or obj.customer.email


class SalesmanScoreSerializer(serializers.ModelSerializer):
    salesman_name = serializers.SerializerMethodField()

    class Meta:
        model = SalesmanScore
        fields = "__all__"

    def get_salesman_name(self, obj):
        return obj.salesman.get_full_name() or obj.salesman.email
