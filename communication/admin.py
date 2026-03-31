from django.contrib import admin

from communication.models import EmailLog, MessageLog, SMSLog


@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = ["id", "message_type", "sender", "receiver", "lead", "status", "created_at"]
    list_filter = ["message_type", "status", "company"]
    search_fields = ["sender__email", "receiver__email", "message", "provider_ref"]


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ["id", "recipient", "subject", "status", "company", "created_at"]
    list_filter = ["status", "company"]
    search_fields = ["recipient", "subject", "provider_ref"]


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ["id", "phone", "status", "company", "created_at"]
    list_filter = ["status", "company"]
    search_fields = ["phone", "provider_ref"]
