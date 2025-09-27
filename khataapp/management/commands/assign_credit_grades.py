# khataapp/management/commands/assign_credit_grades.py
from django.core.management.base import BaseCommand
from khataapp.models import Party
from khataapp.utils.credit_grade import compute_grade_for_party

class Command(BaseCommand):
    help = "Recalculate and assign credit grade for all parties."

    def handle(self, *args, **options):
        updated = 0
        for p in Party.objects.all():
            new_grade = compute_grade_for_party(p)
            if p.credit_grade != new_grade:
                p.credit_grade = new_grade
                p.save(update_fields=['credit_grade'])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"✅ Credit grades updated: {updated}"))