from rest_framework import serializers

from .models import RealtimeEvent


class RealtimeEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealtimeEvent
        fields = "__all__"
