from django.db import models

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
