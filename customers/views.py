from django.db import models
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from customers.models import Customer, CustomerPreference
from customers.serializers import CustomerPreferenceSerializer, CustomerSerializer
from leads.models import Lead, Property
from leads.serializers import LeadSerializer, PropertySerializer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.select_related("user", "company").prefetch_related("preferences")
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        if (getattr(user, "role", "") or "").strip().lower() == "customer":
            return qs.filter(user=user)
        company = getattr(user, "company", None)
        return qs.filter(
            models.Q(user=user)
            | models.Q(company=company, company__isnull=False)
        )

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            serializer.save(company=serializer.validated_data.get("company") or getattr(user, "company", None))
            return
        serializer.save(user=user, company=getattr(user, "company", None))

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        customer = self.get_queryset().filter(user=request.user).first()
        if not customer:
            return Response({"detail": "customer profile not found"}, status=404)

        active_lead = (
            Lead.objects.filter(converted_customer=customer)
            .order_by("-converted_at", "-updated_at")
            .select_related("assigned_agent", "converted_customer")
            .first()
        )
        nearby_qs = Property.objects.exclude(status=Property.Status.REJECTED)
        location_filters = models.Q()
        if customer.pin_code:
            location_filters |= models.Q(pin_code=customer.pin_code)
        if customer.city:
            location_filters |= models.Q(city__iexact=customer.city)
        if customer.district:
            location_filters |= models.Q(district__iexact=customer.district)
        if customer.state:
            location_filters |= models.Q(state__iexact=customer.state)
        if location_filters:
            nearby_qs = nearby_qs.filter(location_filters)

        return Response(
            {
                "customer": CustomerSerializer(customer, context={"request": request}).data,
                "lead": LeadSerializer(active_lead, context={"request": request}).data if active_lead else None,
                "assigned_agent": {
                    "id": getattr(customer.assigned_agent, "id", None),
                    "name": getattr(customer.assigned_agent, "name", ""),
                    "phone": getattr(customer.assigned_agent, "phone", ""),
                }
                if customer.assigned_agent_id
                else None,
                "nearby_properties": PropertySerializer(nearby_qs[:8], many=True, context={"request": request}).data,
            }
        )


class CustomerPreferenceViewSet(viewsets.ModelViewSet):
    queryset = CustomerPreference.objects.select_related("customer", "customer__user")
    serializer_class = CustomerPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(customer__user=user)

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            serializer.save()
            return
        customer, _ = Customer.objects.get_or_create(
            user=user,
            defaults={"company": getattr(user, "company", None)},
        )
        serializer.save(customer=customer)
