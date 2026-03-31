from rest_framework import serializers

from customers.models import Customer, CustomerPreference


class CustomerPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerPreference
        fields = [
            "id",
            "customer",
            "property_type",
            "bedrooms",
            "budget_min",
            "budget_max",
            "city",
            "district",
            "state",
            "is_active",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class CustomerSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    assigned_agent_name = serializers.CharField(source="assigned_agent.name", read_only=True)
    preferences = CustomerPreferenceSerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "user",
            "user_email",
            "user_name",
            "company",
            "assigned_agent",
            "assigned_agent_name",
            "buyer_type",
            "preferred_location",
            "preferred_budget",
            "property_type",
            "avatar",
            "address",
            "city",
            "district",
            "state",
            "pin_code",
            "metadata",
            "preferences",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
