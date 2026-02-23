import random
from decimal import Decimal

from django.contrib.auth import get_user_model

from delivery.models import DeliveryAssignment


User = get_user_model()


def assign_partner(order, distance_km=0):
    partner = User.objects.filter(saas_profile__role="delivery_partner", is_active=True).order_by("id").first()
    otp = f"{random.randint(100000, 999999)}"
    payout = Decimal(distance_km) * Decimal("5.00")
    return DeliveryAssignment.objects.create(
        order=order,
        partner=partner,
        otp_code=otp,
        estimated_distance_km=Decimal(distance_km),
        payout_amount=payout,
    )
