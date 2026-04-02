from asgiref.sync import async_to_sync

try:
    from channels.layers import get_channel_layer
except ImportError:  # pragma: no cover - lightweight deployment fallback
    get_channel_layer = None

from realtime.models import RealtimeEvent


def publish_event(stream_name: str, event_type: str, payload: dict):
    RealtimeEvent.objects.create(channel=stream_name, event_type=event_type, payload=payload)
    if get_channel_layer is None:
        return
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f"stream_{stream_name}",
        {"type": "broadcast", "payload": {"event_type": event_type, "payload": payload}},
    )
