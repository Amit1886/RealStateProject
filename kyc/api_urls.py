from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import KYCDocumentViewSet, KYCProfileViewSet

router = DefaultRouter()
router.register("profiles", KYCProfileViewSet, basename="kyc-profiles")
router.register("documents", KYCDocumentViewSet, basename="kyc-documents")

urlpatterns = [path("", include(router.urls))]

