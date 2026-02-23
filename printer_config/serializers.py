from django.utils.text import slugify
from rest_framework import serializers

from .models import (
    PrintRenderLog,
    PrintTemplate,
    PrinterConfig,
    PrinterTestLog,
    TemplatePlanAccess,
    UserPrintTemplate,
)


class PrinterConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrinterConfig
        fields = "__all__"


class PrinterTestLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrinterTestLog
        fields = "__all__"


class TemplatePlanAccessSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = TemplatePlanAccess
        fields = "__all__"


class PrintTemplateSerializer(serializers.ModelSerializer):
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)
    approved_by_email = serializers.CharField(source="approved_by.email", read_only=True)
    plan_access = TemplatePlanAccessSerializer(many=True, read_only=True)

    class Meta:
        model = PrintTemplate
        fields = "__all__"
        read_only_fields = ("created_by", "approved_by")

    def validate(self, attrs):
        name = attrs.get("name") or getattr(self.instance, "name", "")
        slug = attrs.get("slug") or getattr(self.instance, "slug", "")
        if not slug and name:
            attrs["slug"] = slugify(name)
        return attrs


class UserPrintTemplateSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = UserPrintTemplate
        fields = "__all__"
        read_only_fields = ("user",)


class PrintRenderLogSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)
    user_template_name = serializers.CharField(source="user_template.name", read_only=True)

    class Meta:
        model = PrintRenderLog
        fields = "__all__"
