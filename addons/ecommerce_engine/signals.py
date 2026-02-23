from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from addons.ecommerce_engine.models import StorefrontOrder
from addons.ecommerce_engine.tasks import sync_storefront_order_to_billing


@receiver(post_save, sender=StorefrontOrder)
def storefront_order_paid_sync(sender, instance, created, **kwargs):
    if instance.payment_status == StorefrontOrder.PaymentStatus.PAID and not instance.synced_to_billing:
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            sync_storefront_order_to_billing(instance.id)
        else:
            sync_storefront_order_to_billing.delay(instance.id)
