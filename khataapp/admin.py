# khataapp/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from .models import ReportSchedule, Party, Transaction, CompanySettings, UserProfile
from .forms import TransactionForm
import requests
from django.http import FileResponse
from .utils.credit_report import generate_credit_report_pdf, generate_credit_report_pdf_for_party
from .models import CreditSettings, CreditAccount, CreditEntry, EMI, Penalty

# ---------------- Party ----------------
@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'mobile', 'party_type', 'email', 'is_premium',
        'created_at', 'credit_grade_badge', 'balance_display', 'whatsapp_status', 'sms_status',
        'payment_link_display', 'download_report_button'
    )
    list_filter = ('party_type', 'is_premium', 'credit_grade')
    search_fields = ('name', 'mobile', 'upi_id', 'whatsapp_number', 'sms_number')
    readonly_fields = ('payment_link_display', 'balance_display')

    actions = ['download_credit_report']

    def whatsapp_status(self, obj):
        return "✅ Active" if obj.whatsapp_number else "❌ No WhatsApp"
    whatsapp_status.short_description = "WhatsApp"

    def sms_status(self, obj):
        return "✅ Active" if obj.sms_number else "❌ No SMS"
    sms_status.short_description = "SMS"

    def payment_link_display(self, obj):
        link = obj.get_payment_link()
        if link.startswith("http"):
            return format_html('<a href="{}" target="_blank">{}</a>', link, "Pay Now")
        return link
    payment_link_display.short_description = "Payment Link"

    def balance_display(self, obj):
        return f"₹{obj.total_credit() - obj.total_debit()}"
    balance_display.short_description = "Balance"

    def credit_grade_badge(self, obj):
        color = {
            'A+': '#0ea5e9',
            'A': '#16a34a',
            'B': '#22c55e',
            'C': '#f59e0b',
            'D': '#ef4444',
            '-': '#6b7280',
        }.get(obj.credit_grade or '-', '#6b7280')
        return format_html(
            '<span style="padding:2px 8px;border-radius:9999px;color:white;background:{};font-weight:600;">{}</span>',
            color, obj.credit_grade or '-'
        )
    credit_grade_badge.short_description = "Credit Grade"

    # ---------------- Admin Actions ----------------
    def download_credit_report(self, request, queryset):
        pdf_buffer = generate_credit_report_pdf()
        return FileResponse(pdf_buffer, as_attachment=True, filename="credit_report.pdf")
    download_credit_report.short_description = "Download Grade-wise Credit Report"

    def download_report_button(self, obj):
        return format_html(
            '<a class="button" href="{}">📄 PDF</a>',
            f"/admin/khataapp/party/{obj.id}/download-report/"
        )
    download_report_button.short_description = "Credit Report"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:party_id>/download-report/",
                self.admin_site.admin_view(self.download_report_view),
                name="party_download_report"
            ),
        ]
        return custom_urls + urls

    def download_report_view(self, request, party_id):
        party = Party.objects.get(id=party_id)
        pdf_buffer = generate_credit_report_pdf_for_party(party)
        return FileResponse(pdf_buffer, as_attachment=True, filename=f"{party.name}_credit_report.pdf")


# ---------------- ReportSchedule ----------------
@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ('send_date', 'send_time', 'is_active')
    list_filter = ('is_active',)


# ---------------- Transaction ----------------
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    form = TransactionForm

    list_display = (
        "party", "txn_type", "amount", "date", "notes",
        "receipt_link", "send_whatsapp_button", "send_sms_button"
    )
    search_fields = ("party__name",)
    list_filter = ("txn_type", "date")
    fields = ('party', 'txn_type', 'amount', 'notes', 'receipt')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("send-whatsapp/<int:txn_id>/", self.admin_site.admin_view(self.send_whatsapp), name="send_whatsapp"),
            path("send-sms/<int:txn_id>/", self.admin_site.admin_view(self.send_sms), name="send_sms"),
        ]
        return custom_urls + urls

    def receipt_link(self, obj):
        if obj.receipt:
            return format_html('<a href="{}" target="_blank">📎 View</a>', obj.receipt.url)
        return "❌ No File"
    receipt_link.short_description = "Receipt"

    def send_whatsapp_button(self, obj):
        return format_html(
            '<a class="button" href="{}">📲 WhatsApp</a>',
            f"/admin/khataapp/transaction/send-whatsapp/{obj.id}/"
        )
    send_whatsapp_button.short_description = "WhatsApp"

    def send_sms_button(self, obj):
        return format_html(
            '<a class="button" href="{}">📩 SMS</a>',
            f"/admin/khataapp/transaction/send-sms/{obj.id}/"
        )
    send_sms_button.short_description = "SMS"

    def send_whatsapp(self, request, txn_id):
        txn = Transaction.objects.get(id=txn_id)
        party = txn.party
        settings = CompanySettings.objects.first()

        if not settings or not settings.whatsapp_api_key:
            messages.error(request, "❌ Missing WhatsApp API key in CompanySettings.")
            return redirect("/admin/khataapp/transaction/")

        message = f"{txn.txn_type.upper()} ALERT\n\nParty: {party.name}\nAmount: ₹{txn.amount}\nDate: {txn.date}\nNote: {txn.notes or ''}"
        try:
            from khataapp.utils.whatsapp_utils import send_whatsapp_message
            if party.whatsapp_number:
                send_whatsapp_message(party.whatsapp_number.lstrip("+"), message)
                messages.success(request, f"✅ WhatsApp sent to {party.name}")
            else:
                messages.error(request, "❌ Party WhatsApp number missing.")
        except Exception as e:
            messages.error(request, f"❌ WhatsApp error: {e}")

        return redirect("/admin/khataapp/transaction/")

    def send_sms(self, request, txn_id):
        txn = Transaction.objects.get(id=txn_id)
        party = txn.party
        settings = CompanySettings.objects.first()

        if not settings or not settings.sms_api_key or not party.sms_number:
            messages.error(request, "❌ Missing SMS config/number.")
            return redirect("/admin/khataapp/transaction/")

        message = f"{txn.txn_type.upper()} - ₹{txn.amount} | {txn.date} | {txn.notes or ''}"
        try:
            url = (
                f"https://www.fast2sms.com/dev/bulkV2?"
                f"authorization={settings.sms_api_key}"
                f"&route=q"
                f"&message={message}"
                f"&language=english"
                f"&flash=0"
                f"&numbers={party.sms_number}"
            )
            requests.get(url, headers={"cache-control": "no-cache"}, timeout=20)
            messages.success(request, f"✅ SMS sent to {party.name}")
        except Exception as e:
            messages.error(request, f"❌ SMS error: {e}")

        return redirect("/admin/khataapp/transaction/")


# ---------------- CompanySettings ----------------
@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'enable_auto_whatsapp', 'enable_monthly_email',
                    'whatsapp_number')
    list_editable = ('enable_auto_whatsapp', 'enable_monthly_email')


# ---------------- UserProfile ----------------
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "business_name", "mobile_number", "created_from")
    list_filter = ("plan", "created_from")
    search_fields = ("user__username", "business_name", "mobile_number")

# --- append near end of file ---
@admin.register(CreditSettings)
class CreditSettingsAdmin(admin.ModelAdmin):
    list_display = ("penalty_rate_percent", "apply_after_days", "created_at")


@admin.register(CreditAccount)
class CreditAccountAdmin(admin.ModelAdmin):
    list_display = ("party", "credit_limit", "outstanding", "available", "updated_at")
    search_fields = ("party__name",)
    actions = ["recalculate_available"]

    def recalculate_available(self, request, queryset):
        for acc in queryset:
            acc.save()  # save() recalculates available
        self.message_user(request, "Recalculated available for selected accounts.")
    recalculate_available.short_description = "Recalculate available for selected accounts"


@admin.register(CreditEntry)
class CreditEntryAdmin(admin.ModelAdmin):
    list_display = ("account", "amount", "remaining", "due_date", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("account__party__name",)


@admin.register(EMI)
class EMIAdmin(admin.ModelAdmin):
    list_display = ("credit_entry", "amount", "due_date", "paid", "paid_on")
    list_filter = ("paid", "due_date")
    actions = ["mark_emis_paid"]

    def mark_emis_paid(self, request, queryset):
        for emi in queryset:
            emi.mark_paid()
        self.message_user(request, "Selected EMIs marked as paid.")
    mark_emis_paid.short_description = "Mark selected EMIs as paid"


@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display = ("credit_entry", "penalty_amount", "days_overdue", "applied_at")
    search_fields = ("credit_entry__account__party__name",)
