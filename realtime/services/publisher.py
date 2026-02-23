from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from realtime.models import RealtimeEvent


def publish_event(stream_name: str, event_type: str, payload: dict):
    RealtimeEvent.objects.create(channel=stream_name, event_type=event_type, payload=payload)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"stream_{stream_name}",
        {"type": "broadcast", "payload": {"event_type": event_type, "payload": payload}},
    )
