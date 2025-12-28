# ~/myproject/khatapro/khataapp/models.py

from django.db import models
from django.conf import settings
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
from solo.models import SingletonModel
from django.contrib.auth import get_user_model
from khataapp.utils.whatsapp_utils import send_whatsapp_message

User = get_user_model()



# ---------------- PARTY MODEL ----------------
class Party(models.Model):
    PARTY_TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='my_parties',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    gst = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    party_type = models.CharField(max_length=10, choices=PARTY_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional Business Details
    upi_id = models.CharField(max_length=50, blank=True, null=True)
    bank_account_number = models.CharField(max_length=30, blank=True, null=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    is_premium = models.BooleanField(default=False)

    # Extra Communication Details
    whatsapp_number = models.CharField(max_length=15, blank=True, null=True)
    sms_number = models.CharField(max_length=15, blank=True, null=True)

    # Credit Rating
    credit_grade = models.CharField(max_length=5, default='-', blank=True)

    # Helper / Computed Fields
    def get_payment_link(self):
        """Return a dynamic payment link if UPI & premium."""
        if self.upi_id and self.is_premium:
            name_encoded = self.name.replace(' ', '%20')
            return f"https://upi-pay-link-generator.com/pay?upi={self.upi_id}&name={name_encoded}&amount="
        return "Not available (Add UPI or upgrade to premium)"

    def total_credit(self):
        """Sum of all credit transactions for this party."""
        return self.transactions.filter(txn_type='credit').aggregate(total=Sum('amount'))['total'] or 0

    def total_debit(self):
        """Sum of all debit transactions for this party."""
        return self.transactions.filter(txn_type='debit').aggregate(total=Sum('amount'))['total'] or 0

    def balance(self):
        """Net balance (Credit - Debit)."""
        return self.total_credit() - self.total_debit()

    def __str__(self):
        return f"{self.name} ({self.party_type})"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Parties"


# ---------------- TRANSACTION MODEL ----------------
class Transaction(models.Model):

    TXN_TYPE_CHOICES = [
        ("credit", "Credit"),
        ("debit", "Debit"),
    ]

    TXN_MODE_CHOICES = [
        ("cash", "Cash"),
        ("online", "Online"),
        ("upi", "UPI"),
        ("bank", "Bank Transfer"),
        ("cheque", "Cheque"),
    ]

    GST_TYPE_CHOICES = [
        ("gst", "GST"),
        ("nongst", "Non GST"),
    ]

    party = models.ForeignKey(
        "khataapp.Party",
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    txn_type = models.CharField(max_length=10, choices=TXN_TYPE_CHOICES)
    txn_mode = models.CharField(max_length=20, choices=TXN_MODE_CHOICES, default="cash")

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    date = models.DateField()   # Manual date selection

    notes = models.TextField(blank=True, null=True)

    receipt = models.ImageField(upload_to="receipts/", blank=True, null=True)

    order = models.ForeignKey(
        "commerce.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_transactions"
    )

    payment = models.ForeignKey(
        "commerce.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_transactions"
    )

    voucher = models.ForeignKey(
        "commerce.SalesVoucher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions"
    )

    invoice = models.ForeignKey(
        "commerce.Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions"
    )

    gst_type = models.CharField(
        max_length=10,
        choices=GST_TYPE_CHOICES,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.party.name} - {self.txn_type.capitalize()} - ₹{self.amount}"

    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Transactions"

# ✅ ---------------- Product Model ----------------
class Product(models.Model):
    """Simple product model for commerce compatibility"""
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.IntegerField(default=0)
    sku = models.CharField(max_length=50, blank=True, null=True, unique=True)
    description = models.TextField(blank=True, null=True)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_products', null=True, blank=True)

    def __str__(self):
        return self.name


# ---------------- Company Settings ----------------
class CompanySettings(models.Model):
    company_name = models.CharField(max_length=100, default='My Business')
    default_plan = models.ForeignKey("billing.Plan", on_delete=models.SET_NULL, null=True, blank=True)
    whatsapp_api_key = models.CharField(max_length=255, blank=True, null=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    sms_api_key = models.CharField(max_length=255, blank=True, null=True)
    sms_sender_number = models.CharField(max_length=20, blank=True, null=True)
    enable_auto_whatsapp = models.BooleanField(default=True)
    enable_monthly_email = models.BooleanField(default=True)
    def __str__(self):
        return self.company_name


# ---------------- Offline Message ----------------
class OfflineMessage(models.Model):
    CHANNEL_CHOICES = (("whatsapp", "WhatsApp"), ("sms", "SMS"))
    party = models.ForeignKey("Party", on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"[{self.channel}] {self.message[:30]}... ({self.status})"


# ---------- Credit Grade Logic ----------
def compute_credit_grade(party: Party) -> str:
    totals = Transaction.objects.filter(party=party).values('txn_type').annotate(total=Sum('amount'))
    total_credit = sum(row['total'] for row in totals if row['txn_type'] == 'credit') or 0
    total_debit = sum(row['total'] for row in totals if row['txn_type'] == 'debit') or 0
    if total_credit == 0 and total_debit == 0:
        return 'D'
    ratio = (float(total_debit) / float(total_credit)) * 100 if total_credit > 0 else 0.0
    if ratio >= 90:
        return 'A+'
    elif ratio >= 70:
        return 'A'
    elif ratio >= 50:
        return 'B'
    elif ratio >= 30:
        return 'C'
    else:
        return 'D'


@receiver(post_save, sender=Transaction)
def update_party_grade_and_notify(sender, instance: Transaction, created, **kwargs):
    party = instance.party
    new_grade = compute_credit_grade(party)
    if party.credit_grade != new_grade:
        party.credit_grade = new_grade
        party.save(update_fields=['credit_grade'])
    if created and party.whatsapp_number:
        settings_obj = CompanySettings.objects.first()
        if settings_obj and settings_obj.enable_auto_whatsapp:
            msg = f"🧾 New {instance.txn_type.upper()} of ₹{instance.amount} added for {party.name}. Current grade: {party.credit_grade}"
            send_whatsapp_message(party.whatsapp_number.lstrip('+'), msg)


# ---------------- Report Schedule ----------------
class ReportSchedule(models.Model):
    send_date = models.DateField()
    send_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"Report on {self.send_date} at {self.send_time}"


# ---------------- User Profile ----------------
class UserProfile(models.Model):
    SIGNUP_SOURCE = (("signup", "User Signup"), ("admin", "Created by Admin"))
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="khata_profile")
    plan = models.ForeignKey("billing.Plan", on_delete=models.SET_NULL, null=True, blank=True, related_name='khata_userprofiles')
    full_name = models.CharField(max_length=255, blank=True)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True)
    business_name = models.CharField(max_length=255, blank=True)
    business_type = models.CharField(max_length=100, blank=True)
    gst_number = models.CharField(max_length=50, blank=True, null=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    upi_id = models.CharField(max_length=100, blank=True, null=True)
    bank_name = models.CharField(max_length=150, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    created_from = models.CharField(max_length=20, choices=SIGNUP_SOURCE, default="signup")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.user.username} - {self.business_name or 'No Business'}"


# ---------------- Credit & Loan Models ----------------

class CreditSettings(models.Model):
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    penalty_rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    apply_after_days = models.PositiveIntegerField(default=0)
    allow_partial_payment = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Credit Settings (Interest: {self.interest_rate}%, Penalty: {self.penalty_rate_percent}%)"


class CreditAccount(models.Model):
    party = models.ForeignKey("khataapp.Party", on_delete=models.CASCADE, related_name="credit_accounts")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    outstanding = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def owner(self):
        return self.party.owner   # IMPORTANT

    @property
    def available(self):
        return self.credit_limit - self.outstanding

    def __str__(self):
        return f"{self.party.name} - {self.credit_limit}"


class CreditEntry(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
    )

    account = models.ForeignKey(
        CreditAccount,
        on_delete=models.CASCADE,
        related_name="entries"
    )

    txn_type = models.CharField(max_length=10, choices=(("credit", "Credit"), ("debit", "Debit")))
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    remaining = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    due_date = models.DateField(blank=True, null=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def party(self):
        return self.account.party

    @property
    def owner(self):
        return self.account.party.owner

    def __str__(self):
        return f"{self.account.party.name} - {self.txn_type} {self.amount}"


class EMI(models.Model):
    entry = models.ForeignKey(
        CreditEntry,
        on_delete=models.CASCADE,
        related_name="emis"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()

    paid = models.BooleanField(default=False)
    paid_on = models.DateField(blank=True, null=True)

    @property
    def party(self):
        return self.entry.account.party

    @property
    def owner(self):
        return self.entry.account.party.owner

    def mark_paid(self):
        self.paid = True
        self.paid_on = timezone.now().date()
        self.save()

    def __str__(self):
        return f"EMI of {self.amount} for {self.entry}"


class Penalty(models.Model):
    entry = models.ForeignKey(
        CreditEntry,
        on_delete=models.CASCADE,
        related_name="penalties"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255)
    applied_at = models.DateTimeField(auto_now_add=True)

    @property
    def party(self):
        return self.entry.account.party

    @property
    def owner(self):
        return self.entry.account.party.owner

    def __str__(self):
        return f"Penalty {self.amount} - {self.reason}"
