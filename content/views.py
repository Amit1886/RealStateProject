from django.db import models
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Article, ArticleRead, Category
from .serializers import ArticleReadSerializer, ArticleSerializer, CategorySerializer
from .services import recommend_properties_for_article


class _AdminWriteOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff))


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [_AdminWriteOrReadOnly]
    queryset = Category.objects.all()


class ArticleViewSet(viewsets.ModelViewSet):
    serializer_class = ArticleSerializer
    permission_classes = [_AdminWriteOrReadOnly]
    queryset = Article.objects.select_related("category", "author")

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        company = getattr(user, "company", None)
        if not user.is_superuser:
            qs = qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
        if not (user.is_staff or user.is_superuser):
            qs = qs.filter(is_published=True)
        if category := self.request.query_params.get("category"):
            qs = qs.filter(category__slug=category)
        if search := self.request.query_params.get("search"):
            qs = qs.filter(models.Q(title__icontains=search) | models.Q(excerpt__icontains=search))
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, company=getattr(self.request.user, "company", None))

    @action(detail=True, methods=["get"])
    def recommended_properties(self, request, pk=None):
        article = self.get_object()
        properties = recommend_properties_for_article(article, user=request.user)
        data = [
            {
                "id": item.id,
                "title": item.title,
                "city": item.city,
                "price": str(item.price),
                "property_type": item.property_type,
            }
            for item in properties
        ]
        return Response(data)


class ArticleReadViewSet(viewsets.ModelViewSet):
    serializer_class = ArticleReadSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ArticleRead.objects.select_related("article", "user")

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return qs
        return qs.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

