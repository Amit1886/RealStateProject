from django.db import models
from rest_framework import permissions, viewsets

from customers.models import Customer
from reviews.models import AgentRating, Review
from reviews.serializers import AgentRatingSerializer, ReviewSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related("property", "customer", "customer__user")
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(models.Q(approved=True) | models.Q(customer__user=user)).distinct()

    def perform_create(self, serializer):
        user = self.request.user
        customer, _ = Customer.objects.get_or_create(
            user=user,
            defaults={"company": getattr(user, "company", None)},
        )
        serializer.save(customer=customer)


class AgentRatingViewSet(viewsets.ModelViewSet):
    queryset = AgentRating.objects.select_related("agent", "customer", "customer__user")
    serializer_class = AgentRatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(models.Q(customer__user=user) | models.Q(agent__user=user)).distinct()

    def perform_create(self, serializer):
        user = self.request.user
        customer, _ = Customer.objects.get_or_create(
            user=user,
            defaults={"company": getattr(user, "company", None)},
        )
        serializer.save(customer=customer)
