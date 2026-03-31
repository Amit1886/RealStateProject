from rest_framework import serializers

from .models import Article, ArticleRead, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ArticleSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(source="category", queryset=Category.objects.all(), write_only=True, required=False, allow_null=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "category",
            "category_id",
            "title",
            "slug",
            "excerpt",
            "body",
            "tags",
            "related_city",
            "related_property_type",
            "is_published",
            "published_at",
        ]


class ArticleReadSerializer(serializers.ModelSerializer):
    article = ArticleSerializer(read_only=True)
    article_id = serializers.PrimaryKeyRelatedField(source="article", queryset=Article.objects.all(), write_only=True)

    class Meta:
        model = ArticleRead
        fields = ["id", "article", "article_id", "created_at"]
        read_only_fields = ["created_at"]

