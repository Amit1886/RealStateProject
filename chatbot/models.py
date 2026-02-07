from django.db import models
from django.conf import settings

class ChatFAQ(models.Model):
    keyword = models.CharField(max_length=200)
    answer = models.TextField()

    def __str__(self):
        return self.keyword


class ChatMessage(models.Model):
    user_message = models.TextField()
    bot_reply = models.TextField(blank=True)
    admin_reply = models.TextField(blank=True, null=True)
    is_replied_by_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user_message[:50]


# ---------------- Flow Builder ----------------
class ChatbotFlow(models.Model):
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ("can_manage_flows", "Can manage chatbot flows"),
        ]

    def __str__(self):
        return self.name


class ChatbotNode(models.Model):
    NODE_TYPES = (
        ("start", "Start"),
        ("message", "Message"),
        ("condition", "Condition"),
        ("action", "Action"),
        ("end", "End"),
    )

    flow = models.ForeignKey(ChatbotFlow, on_delete=models.CASCADE, related_name="nodes")
    node_id = models.CharField(max_length=80)
    node_type = models.CharField(max_length=20, choices=NODE_TYPES)
    data = models.JSONField(default=dict, blank=True)
    position_x = models.IntegerField(default=40)
    position_y = models.IntegerField(default=40)

    class Meta:
        unique_together = ("flow", "node_id")

    def __str__(self):
        return f"{self.flow.name} - {self.node_type} ({self.node_id})"


class ChatbotEdge(models.Model):
    flow = models.ForeignKey(ChatbotFlow, on_delete=models.CASCADE, related_name="edges")
    source_id = models.CharField(max_length=80)
    target_id = models.CharField(max_length=80)
    condition_text = models.CharField(max_length=200, blank=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.flow.name}: {self.source_id} -> {self.target_id}"


# ---------------- Chatbot Agent ----------------
class ChatbotAgent(models.Model):
    CHANNEL_CHOICES = (
        ("whatsapp", "WhatsApp"),
        ("web", "Web"),
        ("api", "API"),
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chatbot_agents",
        null=True,
        blank=True
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, null=True)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="whatsapp")
    default_flow = models.ForeignKey(
        ChatbotFlow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agents"
    )
    greeting_text = models.TextField(blank=True, null=True)
    fallback_text = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.channel})"
