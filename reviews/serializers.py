from rest_framework import serializers

from reviews.models import AgentRating, Review


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.user.get_full_name", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "property",
            "customer",
            "customer_name",
            "rating",
            "review_text",
            "approved",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["customer", "created_at", "updated_at"]


class AgentRatingSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.user.get_full_name", read_only=True)

    class Meta:
        model = AgentRating
        fields = [
            "id",
            "agent",
            "customer",
            "customer_name",
            "rating",
            "review_text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["customer", "created_at", "updated_at"]
