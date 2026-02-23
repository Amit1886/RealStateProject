from rest_framework import serializers

from .models import SystemMode


class SystemModeSerializer(serializers.ModelSerializer):
    updated_by_email = serializers.EmailField(source="updated_by.email", read_only=True)

    class Meta:
        model = SystemMode
        fields = [
            "current_mode",
            "is_locked",
            "updated_by",
            "updated_by_email",
            "updated_at",
        ]
        read_only_fields = ["updated_by", "updated_at", "updated_by_email"]


class ChangeSystemModeSerializer(serializers.Serializer):
    current_mode = serializers.ChoiceField(choices=SystemMode.Mode.choices, required=False)
    is_locked = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if "current_mode" not in attrs and "is_locked" not in attrs:
            raise serializers.ValidationError("Provide at least one of current_mode or is_locked.")
        return attrs
