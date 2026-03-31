from django.urls import include, path
from rest_framework.routers import DefaultRouter

from reviews.views import AgentRatingViewSet, ReviewViewSet

router = DefaultRouter()
router.register("property-reviews", ReviewViewSet, basename="reviews-property")
router.register("agent-ratings", AgentRatingViewSet, basename="reviews-agent")

urlpatterns = [path("", include(router.urls))]
