from django.contrib import admin

from reviews.models import AgentRating, Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "property", "customer", "rating", "approved", "created_at"]
    list_filter = ["approved", "rating", "created_at"]
    search_fields = ["property__title", "customer__user__email", "review_text"]


@admin.register(AgentRating)
class AgentRatingAdmin(admin.ModelAdmin):
    list_display = ["id", "agent", "customer", "rating", "created_at"]
    list_filter = ["rating", "created_at"]
    search_fields = ["agent__name", "customer__user__email", "review_text"]
