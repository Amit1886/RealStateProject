from django.urls import path

from .views import (
    EmitEventAPI,
    ExecutionListAPI,
    FeatureToggleListAPI,
    FeatureToggleUpdateAPI,
    RuleListAPI,
)

urlpatterns = [
    path("feature-flags/", FeatureToggleListAPI.as_view(), name="feature_flags"),
    path("feature-flags/<int:pk>/", FeatureToggleUpdateAPI.as_view(), name="feature_flag_update"),
    path("rules/", RuleListAPI.as_view(), name="rules"),
    path("events/emit/", EmitEventAPI.as_view(), name="emit_event"),
    path("executions/", ExecutionListAPI.as_view(), name="executions"),
]
