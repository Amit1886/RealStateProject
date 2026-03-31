from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PropertyVerificationViewSet, VerificationDocumentViewSet

router = DefaultRouter()
router.register("requests", PropertyVerificationViewSet, basename="property-verification")
router.register("documents", VerificationDocumentViewSet, basename="verification-documents")

urlpatterns = [
    path("", include(router.urls)),
]

