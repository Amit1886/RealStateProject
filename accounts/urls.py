from django.urls import path, include
from . import views

app_name = "accounts"

urlpatterns = [
    # Authentication
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Profile
    path("complete-profile/", views.complete_profile, name="complete_profile"),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
    path("profile/", views.profile_view, name="profile"),

    # Dashboard
    path("dashboard/", views.dashboard_view, name="dashboard"),  # fixed name

    # Commerce app
    path("commerce/", include("commerce.urls")),  # fixed include

    # Plan Subscription
    path("subscribe/<int:plan_id>/", views.subscribe_plan, name="switch_plan"),
    path("start-payment/<int:plan_id>/", views.start_payment, name="start_payment"),
    path("payment-success/<int:plan_id>/", views.payment_success, name="payment_success"),
]
