from channels.generic.websocket import AsyncJsonWebsocketConsumer


class StreamConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.stream_name = self.scope["url_route"]["kwargs"]["stream_name"]
        self.group_name = f"stream_{self.stream_name}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "broadcast",
                "payload": content,
            },
        )

    async def broadcast(self, event):
        await self.send_json(event["payload"])
