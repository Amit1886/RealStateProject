from django.urls import path

from .views import HealthAPI

urlpatterns = [
    path("health/", HealthAPI.as_view(), name="health"),
]

