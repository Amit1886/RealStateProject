from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PropertyVerification
from .services import apply_verified_badge


@receiver(post_save, sender=PropertyVerification)
def sync_verification_badge(sender, instance: PropertyVerification, **kwargs):
    if instance.status == PropertyVerification.Status.APPROVED:
        apply_verified_badge(instance.property, verified=True)
    elif instance.status == PropertyVerification.Status.REJECTED:
        apply_verified_badge(instance.property, verified=False)

