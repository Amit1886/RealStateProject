from django.contrib import admin
from .models import ChatFAQ, ChatMessage

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
