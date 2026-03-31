from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import SaaSRole
from customers.models import Customer


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_customer_profile(sender, instance, created, **kwargs):
    if not created:
        return
    if getattr(instance, "role", "") != SaaSRole.CUSTOMER:
        return
    Customer.objects.get_or_create(
        user=instance,
        defaults={
            "company": getattr(instance, "company", None),
            "preferred_location": "",
            "preferred_budget": None,
            "property_type": "",
            "city": "",
            "district": "",
            "state": "",
            "pin_code": "",
        },
    )
