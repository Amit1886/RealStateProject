from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import ChatFAQ, ChatMessage, ChatbotFlow, ChatbotNode, ChatbotEdge, ChatbotAgent

@admin.register(ChatFAQ)
class ChatFAQAdmin(admin.ModelAdmin):
    list_display = ("keyword", "answer")

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = (
        "user_message",
        "is_replied_by_admin",
        "created_at"
    )
    readonly_fields = ("user_message", "created_at")


@admin.register(ChatbotFlow)
class ChatbotFlowAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at", "open_builder")
    list_filter = ("is_active",)

    def open_builder(self, obj):
        url = reverse("chatbot_flow_builder", args=[obj.id])
        return format_html('<a class="button" href="{}">Open Builder</a>', url)
    open_builder.short_description = "Flow Builder"


@admin.register(ChatbotNode)
class ChatbotNodeAdmin(admin.ModelAdmin):
    list_display = ("flow", "node_id", "node_type", "position_x", "position_y")
    list_filter = ("node_type",)
    search_fields = ("node_id",)


@admin.register(ChatbotEdge)
class ChatbotEdgeAdmin(admin.ModelAdmin):
    list_display = ("flow", "source_id", "target_id", "condition_text", "is_default")
    search_fields = ("source_id", "target_id", "condition_text")


@admin.register(ChatbotAgent)
class ChatbotAgentAdmin(admin.ModelAdmin):
    list_display = ("name", "channel", "owner", "default_flow", "is_active", "updated_at")
    list_filter = ("channel", "is_active")
    search_fields = ("name", "owner__email")
