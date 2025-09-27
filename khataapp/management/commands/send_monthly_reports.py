# khataapp/management/commands/send_monthly_reports.py
from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from django.conf import settings
from khataapp.models import Party, Transaction, CompanySettings, ReportSchedule
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.utils import timezone
from datetime import datetime  # <-- Added

class Command(BaseCommand):
    help = "Send monthly PDF reports to admin email at scheduled time"

    def handle(self, *args, **options):
        # Step 1: Check if schedule is active
        schedule = ReportSchedule.objects.filter(is_active=True).first()
        if not schedule:
            self.stdout.write(self.style.WARNING("No active schedule found."))
            return

        # Step 2: Match current date/time with schedule
        now = timezone.localtime()
        if schedule.send_date != now.date() or schedule.send_time.hour != now.hour:
            self.stdout.write(self.style.WARNING("Not scheduled time yet."))
            return

        # Step 3: Check if monthly email is enabled
        cs = CompanySettings.objects.first()
        if not cs or not cs.enable_monthly_email:
            self.stdout.write(self.style.WARNING("Monthly email disabled or settings missing."))
            return

        # Step 4: Generate PDF report
        buf = BytesIO()
        p = canvas.Canvas(buf, pagesize=A4)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(40, 800, "Monthly Report - KhataPro")
        p.setFont("Helvetica", 11)

        y = 770
        for party in Party.objects.order_by('name')[:50]:
            credits = Transaction.objects.filter(party=party, txn_type='credit').count()
            debits = Transaction.objects.filter(party=party, txn_type='debit').count()
            line = f"{party.name} [{party.credit_grade}]  Credits: {credits}  Debits: {debits}"
            p.drawString(40, y, line)
            y -= 16
            if y < 80:
                p.showPage()
                y = 800

        p.showPage()
        p.save()
        pdf_data = buf.getvalue()
        buf.close()

        # Step 5: Send Email
        subject = "KhataPro - Monthly Report"
        body = "Attached monthly summary."
        msg = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.DEFAULT_FROM_EMAIL])
        msg.attach("monthly_report.pdf", pdf_data, "application/pdf")
        msg.send()

        self.stdout.write(self.style.SUCCESS("✅ Monthly report emailed successfully."))