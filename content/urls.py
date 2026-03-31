from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ArticleReadViewSet, ArticleViewSet, CategoryViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="content-categories")
router.register("articles", ArticleViewSet, basename="content-articles")
router.register("reads", ArticleReadViewSet, basename="content-reads")

urlpatterns = [
    path("", include(router.urls)),
]

