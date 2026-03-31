from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SchemeMatcherAPIView, SchemeViewSet, UserSchemeMatchViewSet

router = DefaultRouter()
router.register("catalog", SchemeViewSet, basename="schemes")
router.register("matches", UserSchemeMatchViewSet, basename="scheme-matches")

urlpatterns = [
    path("match/", SchemeMatcherAPIView.as_view(), name="scheme-match"),
    path("", include(router.urls)),
]

