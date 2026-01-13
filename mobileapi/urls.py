from django.urls import path
from .views import app_home
from .views import login_api

urlpatterns = [
    path("home/", app_home),
    path('login/', login_api),
    path("", app_home, name="api_home"),
]
