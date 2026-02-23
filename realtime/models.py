from django.db import models


class RealtimeEvent(models.Model):
    channel = models.CharField(max_length=60, db_index=True)
    event_type = models.CharField(max_length=80)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["channel", "created_at"])]
