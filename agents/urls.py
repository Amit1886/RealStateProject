from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AgentCoverageAreaViewSet, AgentVerificationViewSet, AgentViewSet

router = DefaultRouter()
router.register("agents", AgentViewSet, basename="agents")
router.register("coverage-areas", AgentCoverageAreaViewSet, basename="agent-coverage-areas")
router.register("verifications", AgentVerificationViewSet, basename="agent-verifications")

urlpatterns = [
    path("register/", AgentViewSet.as_view({"post": "create"}), name="agent-register"),
    path("", include(router.urls)),
]
