from __future__ import annotations

from django.db import models


class Review(models.Model):
    property = models.ForeignKey("leads.Property", on_delete=models.CASCADE, related_name="reviews")
    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE, related_name="property_reviews")
    rating = models.PositiveSmallIntegerField(default=5)
    review_text = models.TextField(blank=True, default="")
    approved = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("property", "customer")]
        indexes = [
            models.Index(fields=["property", "approved", "created_at"]),
            models.Index(fields=["customer", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.property_id}:{self.rating}"


class AgentRating(models.Model):
    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="ratings")
    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE, related_name="agent_ratings")
    rating = models.PositiveSmallIntegerField(default=5)
    review_text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("agent", "customer")]
        indexes = [
            models.Index(fields=["agent", "created_at"]),
            models.Index(fields=["customer", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.agent_id}:{self.rating}"
