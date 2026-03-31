from rest_framework import serializers

from .models import Bank, LoanApplication, LoanProduct
from .services import build_application_snapshot


class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = [
            "id",
            "name",
            "slug",
            "website",
            "support_email",
            "support_phone",
            "active",
        ]


class LoanProductSerializer(serializers.ModelSerializer):
    bank = BankSerializer(read_only=True)
    bank_id = serializers.PrimaryKeyRelatedField(source="bank", queryset=Bank.objects.all(), write_only=True)

    class Meta:
        model = LoanProduct
        fields = [
            "id",
            "bank",
            "bank_id",
            "name",
            "slug",
            "property_type",
            "interest_rate",
            "loan_amount",
            "tenure_years",
            "emi_estimate",
            "min_income_required",
            "active",
        ]


class LoanApplicationSerializer(serializers.ModelSerializer):
    loan_product = LoanProductSerializer(read_only=True)
    loan_product_id = serializers.PrimaryKeyRelatedField(
        source="loan_product",
        queryset=LoanProduct.objects.select_related("bank").all(),
        write_only=True,
    )

    class Meta:
        model = LoanApplication
        fields = [
            "id",
            "property",
            "loan_product",
            "loan_product_id",
            "requested_amount",
            "tenure_years",
            "monthly_income",
            "existing_emi",
            "emi_estimate",
            "eligibility_ratio",
            "status",
            "notes",
            "created_at",
        ]
        read_only_fields = ["emi_estimate", "eligibility_ratio", "status", "created_at"]

    def create(self, validated_data):
        loan_product = validated_data["loan_product"]
        snapshot = build_application_snapshot(
            requested_amount=validated_data["requested_amount"],
            interest_rate=loan_product.interest_rate,
            tenure_years=validated_data["tenure_years"],
            monthly_income=validated_data.get("monthly_income"),
            existing_emi=validated_data.get("existing_emi"),
        )
        validated_data["emi_estimate"] = snapshot["emi_estimate"]
        validated_data["eligibility_ratio"] = snapshot["eligibility_ratio"]
        validated_data["status"] = snapshot["status"]
        return super().create(validated_data)


class LoanCalculatorSerializer(serializers.Serializer):
    principal = serializers.DecimalField(max_digits=14, decimal_places=2)
    annual_rate = serializers.DecimalField(max_digits=6, decimal_places=2)
    tenure_years = serializers.IntegerField(min_value=1, max_value=40)


class LoanEligibilitySerializer(serializers.Serializer):
    requested_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    interest_rate = serializers.DecimalField(max_digits=6, decimal_places=2)
    tenure_years = serializers.IntegerField(min_value=1, max_value=40)
    monthly_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    existing_emi = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default="0")

