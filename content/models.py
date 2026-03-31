from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from saas_core.models import Company


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Article(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="articles",
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="articles")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles_authored",
    )
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    excerpt = models.CharField(max_length=320, blank=True, default="")
    body = models.TextField()
    tags = models.JSONField(default=list, blank=True)
    related_city = models.CharField(max_length=120, blank=True, default="", db_index=True)
    related_property_type = models.CharField(max_length=40, blank=True, default="", db_index=True)
    is_published = models.BooleanField(default=True, db_index=True)
    published_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["company", "is_published"]),
            models.Index(fields=["related_city", "related_property_type"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:240]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class ArticleRead(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="reads")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="article_reads",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["article", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

