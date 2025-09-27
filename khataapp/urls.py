from django.urls import path
from . import views

urlpatterns = [
    path("credit-report/", views.credit_report_view, name="credit_report"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/update-plan/", views.update_plan, name="update_plan"),
    path("my-credits/", views.my_credits, name="my_credits"),
]
