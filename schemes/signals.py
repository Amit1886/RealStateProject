from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserSchemeMatch


@receiver(post_save, sender=UserSchemeMatch)
def sync_scheme_badge(sender, instance: UserSchemeMatch, **kwargs):
    if not instance.property:
        return
    metadata = instance.property.metadata or {}
    badges = list(metadata.get("badges") or [])
    if instance.status in {UserSchemeMatch.Status.MATCHED, UserSchemeMatch.Status.SAVED, UserSchemeMatch.Status.APPLIED}:
        if "govt_scheme_eligible" not in badges:
            badges.append("govt_scheme_eligible")
    metadata["badges"] = badges
    if instance.property.metadata != metadata:
        instance.property.metadata = metadata
        instance.property.save(update_fields=["metadata", "updated_at"])

