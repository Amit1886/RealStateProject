from rest_framework import serializers

from leads.models import Lead
from .models import GroupVisit, GroupVisitAttendance, SiteVisit


class SiteVisitSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.name", read_only=True)
    agent_name = serializers.CharField(source="agent.name", read_only=True)

    class Meta:
        model = SiteVisit
        fields = [
            "id",
            "lead",
            "lead_name",
            "agent",
            "agent_name",
            "group_visit",
            "is_group_visit",
            "is_no_show",
            "visit_date",
            "location",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class GroupVisitAttendanceSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.name", read_only=True)

    class Meta:
        model = GroupVisitAttendance
        fields = ["id", "group_visit", "lead", "lead_name", "attendance_status", "checked_in_at", "remarks", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class GroupVisitSerializer(serializers.ModelSerializer):
    lead_names = serializers.SerializerMethodField()
    leads = serializers.PrimaryKeyRelatedField(queryset=Lead.objects.all(), many=True, required=False)

    class Meta:
        model = GroupVisit
        fields = ["id", "agent", "visit_date", "location", "leads", "lead_names", "notes", "created_by", "created_at", "updated_at"]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def get_lead_names(self, obj):
        return [lead.name or lead.mobile for lead in obj.leads.all()]

    def create(self, validated_data):
        leads = validated_data.pop("leads", [])
        request = self.context.get("request")
        group_visit = GroupVisit.objects.create(created_by=getattr(request, "user", None), **validated_data)
        for lead in leads:
            GroupVisitAttendance.objects.create(group_visit=group_visit, lead=lead)
        return group_visit

    def update(self, instance, validated_data):
        leads = validated_data.pop("leads", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if leads is not None:
            instance.attendance_rows.all().delete()
            for lead in leads:
                GroupVisitAttendance.objects.create(group_visit=instance, lead=lead)
        return instance
