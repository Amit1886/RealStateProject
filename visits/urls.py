from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import GroupVisitAttendanceViewSet, GroupVisitViewSet, SiteVisitViewSet

router = DefaultRouter()
router.register("visits", SiteVisitViewSet, basename="visits")
router.register("group-visits", GroupVisitViewSet, basename="group-visits")
router.register("group-visit-attendance", GroupVisitAttendanceViewSet, basename="group-visit-attendance")

urlpatterns = [path("", include(router.urls))]
