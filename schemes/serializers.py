from rest_framework import serializers

from .models import Scheme, UserSchemeMatch


class SchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scheme
        fields = [
            "id",
            "title",
            "slug",
            "summary",
            "description",
            "state",
            "district",
            "city",
            "income_limit",
            "ownership_status",
            "apply_url",
            "active",
        ]


class UserSchemeMatchSerializer(serializers.ModelSerializer):
    scheme = SchemeSerializer(read_only=True)
    scheme_id = serializers.PrimaryKeyRelatedField(source="scheme", queryset=Scheme.objects.all(), write_only=True, required=False)

    class Meta:
        model = UserSchemeMatch
        fields = [
            "id",
            "scheme",
            "scheme_id",
            "property",
            "income",
            "location",
            "ownership_status",
            "match_score",
            "status",
            "created_at",
        ]
        read_only_fields = ["match_score", "created_at"]


class SchemeMatcherSerializer(serializers.Serializer):
    income = serializers.DecimalField(max_digits=12, decimal_places=2)
    location = serializers.CharField(max_length=160)
    ownership_status = serializers.ChoiceField(choices=Scheme.OwnershipStatus.choices)
    property_id = serializers.IntegerField(required=False)

