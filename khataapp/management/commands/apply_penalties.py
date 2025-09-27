from django.core.management.base import BaseCommand
from django.utils.timezone import now
from decimal import Decimal
from khataapp.models import EMI, CreditSettings, Penalty

class Command(BaseCommand):
    help = "Apply penalties for overdue EMIs based on CreditSettings."

    def handle(self, *args, **options):
        today = now().date()
        settings = CreditSettings.get_solo()
        overdue_emis = EMI.objects.filter(status="pending", due_date__lt=today)

        for emi in overdue_emis:
            days_overdue = (today - emi.due_date).days
            penalty_amt = (emi.amount * Decimal(settings.penalty_rate) / Decimal(100)) * days_overdue

            # Create penalty record
            Penalty.objects.create(
                party=emi.entry.party,
                emi=emi,
                amount=penalty_amt,
                reason=f"Overdue {days_overdue} days"
            )

            # Update EMI penalty field
            emi.penalty_amount += penalty_amt
            emi.save(update_fields=["penalty_amount"])

            self.stdout.write(
                self.style.SUCCESS(
                    f"Applied penalty {penalty_amt} to EMI {emi.id} (Party {emi.entry.party.name})"
                )
            )
