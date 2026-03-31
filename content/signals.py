from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ArticleRead
from .services import capture_content_lead


@receiver(post_save, sender=ArticleRead)
def create_lead_on_article_read(sender, instance: ArticleRead, created: bool, **kwargs):
    if created:
        capture_content_lead(article=instance.article, user=instance.user)

