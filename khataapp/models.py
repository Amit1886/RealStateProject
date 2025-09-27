from django.db import models
from django.conf import settings
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from khataapp.utils.whatsapp_utils import send_whatsapp_message
from django.contrib.auth.models import Group
from django.utils import timezone
from django.contrib.auth.models import User
from billing.models import Plan
from decimal import Decimal
from solo.models import SingletonModel


# ---------------- Party Model ----------------
class Party(models.Model):
    PARTY_TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
    )

    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    gst = models.CharField(max_length=20, blank=True, null=True)   # <---
    address = models.TextField(blank=True, null=True)
    party_type = models.CharField(max_length=10, choices=PARTY_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    # 👇 Owner field (हर Party अपने user से जुड़ी रहेगी)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # ✅ Fixed: auth.User → settings.AUTH_USER_MODEL
        on_delete=models.CASCADE,
        related_name='my_parties',
        null=True, blank=True,
        help_text="Which user owns this party (for user-specific isolation)"
    )

    # Extra Fields
    upi_id = models.CharField(max_length=50, blank=True, null=True)
    bank_account_number = models.CharField(max_length=30, blank=True, null=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    is_premium = models.BooleanField(default=False)
    whatsapp_number = models.CharField(max_length=15, blank=True, null=True)
    sms_number = models.CharField(max_length=15, blank=True, null=True)

    # Credit Grade
    credit_grade = models.CharField(max_length=5, default='-', blank=True)

    def get_payment_link(self):
        if self.upi_id and self.is_premium:
            return f"https://upi-pay-link-generator.com/pay?upi={self.upi_id}&name={self.name.replace(' ', '%20')}&amount="
        return "Not available (Add UPI or upgrade to premium)"

    def total_credit(self):
        return self.transaction_set.filter(txn_type='credit').aggregate(Sum('amount'))['amount__sum'] or 0

    def total_debit(self):
        return self.transaction_set.filter(txn_type='debit').aggregate(Sum('amount'))['amount__sum'] or 0

    def balance(self):
        return self.total_credit() - self.total_debit()

    def __str__(self):
        return f"{self.name} ({self.party_type})"


# ---------------- Transaction Model ----------------
class Transaction(models.Model):
    party = models.ForeignKey("Party", on_delete=models.CASCADE)
    txn_type = models.CharField(max_length=10, choices=[("credit", "Credit"), ("debit", "Debit")])
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)

    receipt = models.ImageField(
        upload_to="receipts/",
        blank=True,
        null=True,
        help_text="Upload receipt slip (browse or capture from camera)"
    )

    def __str__(self):
        return f"{self.party.name} - {self.txn_type} - {self.amount}"


# ---------------- Company Settings ----------------
class CompanySettings(models.Model):
    company_name = models.CharField(max_length=100, default='My Business')

    # WhatsApp & SMS
    whatsapp_api_key = models.CharField(max_length=255, blank=True, null=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    sms_api_key = models.CharField(max_length=255, blank=True, null=True)
    sms_sender_number = models.CharField(max_length=20, blank=True, null=True)

    enable_auto_whatsapp = models.BooleanField(default=True)
    enable_monthly_email = models.BooleanField(default=True)

    def __str__(self):
        return self.company_name


# ---------------- Offline Message (for fallback) ----------------
class OfflineMessage(models.Model):
    CHANNEL_CHOICES = (
        ("whatsapp", "WhatsApp"),
        ("sms", "SMS"),
    )

    party = models.ForeignKey("Party", on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=20, default="pending", help_text="pending/sent/failed")
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
    send_date = models.DateField(help_text="कब report भेजनी है")
    send_time = models.TimeField(help_text="किस time पर भेजनी है")
    is_active = models.BooleanField(default=True, help_text="ON/OFF करना है या नहीं")

    def __str__(self):
        return f"Report on {self.send_date} at {self.send_time}"


# ---------------- User Profile ----------------
class UserProfile(models.Model):
    SIGNUP_SOURCE = (
        ("signup", "User Signup"),
        ("admin", "Created by Admin"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,   # ✅ yeh change hai
        on_delete=models.CASCADE,
        related_name="khata_profile"
    )



    # ✅ Plan ko billing.Plan se link
    plan = models.ForeignKey(
        Plan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Profile fields
    full_name = models.CharField(max_length=255, blank=True)
    mobile_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    business_name = models.CharField(max_length=255, blank=True)
    business_type = models.CharField(max_length=100, blank=True)
    gst_number = models.CharField(max_length=50, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)

    created_from = models.CharField(
        max_length=20,
        choices=SIGNUP_SOURCE,
        default="signup"
    )

    def __str__(self):
        return f"{self.user.username} - {self.business_name or 'No Business'}"

class CreditSettings(SingletonModel):   # <-- change models.Model to SingletonModel
    """
    Admin-configurable settings for credit/penalty behavior.
    """
    penalty_rate_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("1.00"),
        help_text="Penalty percent PER DAY applied on overdue EMI amount."
    )
    apply_after_days = models.PositiveIntegerField(
        default=1,
        help_text="Start applying penalty after this many days past due date."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Credit Settings"
        verbose_name_plural = "Credit Settings"

    def __str__(self):
        return "Credit Settings"


class CreditAccount(models.Model):
    """
    One credit-account per Party. Holds credit_limit, outstanding, available.
    """
    party = models.OneToOneField("Party", on_delete=models.CASCADE, related_name="credit_account")
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    outstanding = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    available = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        default_permissions = ('add', 'change', 'delete')  # 'view' remove
        permissions = [
            ("approve_credit", "Can approve credit"),
        ]

    def __str__(self):
        return f"{self.party.name} - Limit ₹{self.credit_limit} / Outstanding ₹{self.outstanding}"

    def save(self, *args, **kwargs):
        # recalc available
        self.credit_limit = self.credit_limit or Decimal("0.00")
        self.outstanding = self.outstanding or Decimal("0.00")
        self.available = (self.credit_limit - self.outstanding)
        if self.available < Decimal("0.00"):
            self.available = Decimal("0.00")
        super().save(*args, **kwargs)

    def allocate_credit(self, amount):
        """Called when credit is given to party."""
        amount = Decimal(amount)
        self.outstanding += amount
        self.save()

    def repay_amount(self, amount):
        """Called when payment reduces outstanding."""
        amount = Decimal(amount)
        self.outstanding -= amount
        if self.outstanding < Decimal("0.00"):
            self.outstanding = Decimal("0.00")
        self.save()


class CreditEntry(models.Model):
    """
    Ledger entry for credit given (is_credit=True) or repayment (is_credit=False).
    If it's credit, remaining starts as amount and decreases as repayments/EMIs get paid.
    """
    account = models.ForeignKey(CreditAccount, on_delete=models.CASCADE, related_name="entries")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    remaining = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_credit = models.BooleanField(default=True)
    transaction = models.ForeignKey("Transaction", on_delete=models.SET_NULL, null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=(("open","Open"),("overdue","Overdue"),("repaid","Repaid")), default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [("manage_creditentry", "Can manage credit entries")]

    def __str__(self):
        return f"{self.account.party.name} - Entry ₹{self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        if self.remaining is None:
            self.remaining = self.amount
        super().save(*args, **kwargs)

    def apply_payment(self, amount):
        """Apply a payment amount to this entry (partial/full). Returns applied amount."""
        amount = Decimal(amount)
        to_apply = min(self.remaining, amount)
        self.remaining -= to_apply
        if self.remaining <= Decimal("0.00"):
            self.remaining = Decimal("0.00")
            self.status = "repaid"
        self.save()
        # update account outstanding
        self.account.repay_amount(to_apply)
        return to_apply


class EMI(models.Model):
    credit_entry = models.ForeignKey(CreditEntry, on_delete=models.CASCADE, related_name="emis")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    paid = models.BooleanField(default=False)
    paid_on = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [("manage_emi","Can manage EMIs")]

    def __str__(self):
        return f"EMI ₹{self.amount} for {self.credit_entry.account.party.name} due {self.due_date}"

    def mark_paid(self, paid_at=None):
        if not self.paid:
            self.paid = True
            self.paid_on = paid_at or timezone.now()
            self.save()
            # apply to credit entry
            self.credit_entry.apply_payment(self.amount)


class Penalty(models.Model):
    credit_entry = models.ForeignKey(CreditEntry, on_delete=models.CASCADE, related_name="penalties")
    penalty_amount = models.DecimalField(max_digits=12, decimal_places=2)
    days_overdue = models.IntegerField(default=0)
    applied_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        permissions = [("manage_penalty","Can manage penalties")]

    def __str__(self):
        return f"Penalty ₹{self.penalty_amount} for {self.credit_entry.account.party.name}"

    def apply_penalty(self):
        # add penalty to account outstanding
        self.credit_entry.account.outstanding += self.penalty_amount
        self.credit_entry.account.save()

