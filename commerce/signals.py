from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Invoice
from ledger.utils import add_invoice_to_ledger

@receiver(post_save, sender=Invoice)
def create_invoice_ledger(sender, instance, created, **kwargs):
    if created:
        add_invoice_to_ledger(instance)
