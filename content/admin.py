from django.contrib import admin

from .models import Article, ArticleRead, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "related_city", "related_property_type", "is_published", "published_at")
    list_filter = ("is_published", "category")
    search_fields = ("title", "excerpt", "body")


@admin.register(ArticleRead)
class ArticleReadAdmin(admin.ModelAdmin):
    list_display = ("article", "user", "created_at")
    search_fields = ("article__title", "user__email")

