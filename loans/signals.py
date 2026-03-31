from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import LoanApplication


@receiver(post_save, sender=LoanApplication)
def sync_loan_badges(sender, instance: LoanApplication, **kwargs):
    property_obj = instance.property
    if not property_obj:
        return
    metadata = property_obj.metadata or {}
    badges = list(metadata.get("badges") or [])
    if instance.status in {LoanApplication.Status.ELIGIBLE, LoanApplication.Status.APPROVED}:
        if "loan_eligible" not in badges:
            badges.append("loan_eligible")
    else:
        badges = [badge for badge in badges if badge != "loan_eligible"]
    metadata["badges"] = badges
    if property_obj.metadata != metadata:
        property_obj.metadata = metadata
        property_obj.save(update_fields=["metadata", "updated_at"])

