import asyncio

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class SystemModeConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send_json(
            {
                "event_type": "system.mode.connected",
                "payload": {"connected": True},
            }
        )

        # Best-effort group subscription. If Redis/channel layer is down, do not block UI.
        try:
            if self.channel_layer is not None:
                await asyncio.wait_for(
                    self.channel_layer.group_add("system_mode", self.channel_name),
                    timeout=1.0,
                )
        except Exception:
            pass

    async def disconnect(self, close_code):
        try:
            if self.channel_layer is not None:
                await asyncio.wait_for(
                    self.channel_layer.group_discard("system_mode", self.channel_name),
                    timeout=1.0,
                )
        except Exception:
            pass

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def mode_changed(self, event):
        await self.send_json(event["event"])
