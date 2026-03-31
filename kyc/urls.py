from django.urls import path
from realstateproject.lazy_views import lazy_view

app_name = "kyc"

urlpatterns = [
    path("profile/", lazy_view("kyc.views.dashboard"), name="dashboard"),
    path("review/<int:profile_id>/", lazy_view("kyc.views.review_profile"), name="review_profile"),
]
