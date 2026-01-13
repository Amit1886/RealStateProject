# accounts/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta
import random
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum
from django.utils.text import slugify
from decimal import Decimal


class LedgerEntry(models.Model):
    # ---- SOURCE TYPES (for tracking) ----
    ENTRY_SOURCE = (
        ('manual', 'Manual Entry'),
        ('order', 'Order Billing'),
        ('payment', 'Payment Received'),
        ('invoice', 'Subscription Invoice'),
    )

    # ---- TRANSACTION TYPES ----
    TXN_TYPES = (
        ('debit', 'Debit'),
        ('credit', 'Credit'),
    )

    # ---- LINK TO CREDIT ACCOUNT (owner=user stored on CreditAccount) ----
    # NOTE: temporary allow null so migration can run if rows already exist.
    account = models.ForeignKey(
        "khataapp.CreditAccount",
        on_delete=models.CASCADE,
        related_name="ledger_entries",
        null=True,      # first add as nullable, later make non-nullable after populating
        blank=True
    )

    # ---- PARTY LINK ----
    party = models.ForeignKey(
        "khataapp.Party",
        on_delete=models.CASCADE,
        related_name="ledger_entries"
    )

    # ---- AMOUNT ----
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    txn_type = models.CharField(max_length=10, choices=TXN_TYPES)

    # ---- OPTIONAL BILLING FIELDS ----
    invoice_no = models.CharField(max_length=50, blank=True, null=True)
    description = models.CharField(max_length=250, blank=True, null=True)

    # ---- BUSY/TALLY FIELDS ----
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # ---- NOTES ----
    notes = models.TextField(blank=True, null=True)

    # ---- SOURCE TRACKING ----
    source = models.CharField(max_length=20, choices=ENTRY_SOURCE, default='manual')
    source_id = models.PositiveIntegerField(null=True, blank=True)

    # ---- DATES ----
    date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'id']

    def save(self, *args, **kwargs):
        # auto fill credit/debit from txn_type
        if self.txn_type == "credit":
            self.credit = self.amount
            self.debit = 0
        else:
            self.debit = self.amount
            self.credit = 0

        super().save(*args, **kwargs)
        # update running balance for this (account, party) pair
        self.update_running_balance()

    def update_running_balance(self):
        # Use account to calculate running balance (account may be null temporarily)
        if not self.account:
            return

        entries = LedgerEntry.objects.filter(
            account=self.account,
            party=self.party
        ).order_by("date", "id")

        running = 0
        for e in entries:
            running += (e.credit - e.debit)
            if e.balance != running:
                e.balance = running
                e.save(update_fields=["balance"])

    def __str__(self):
        return f"{self.party.name} – {self.txn_type.upper()} ₹{self.amount}"

@property
def total_parties(self):
    from khataapp.models import Party
    return Party.objects.filter(owner=self.user).count()

@property
def total_transactions(self):
    from khataapp.models import Transaction
    return Transaction.objects.filter(party__owner=self.user).count()



# ----------------- OTP GENERATOR -----------------
def _gen_otp():
    """Generate a 6-digit random OTP"""
    return str(random.randint(100000, 999999))


# ----------------- CUSTOM USER MODEL -----------------
class User(AbstractUser):
    username = models.CharField(max_length=150, blank=True, null=True)
    mobile = models.CharField(max_length=15, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True)

    email_verified = models.BooleanField(default=False)
    mobile_verified = models.BooleanField(default=False)
    is_social_login = models.BooleanField(default=False)
    is_otp_verified = models.BooleanField(default=False)


    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_set",
        blank=True,
        help_text="Groups this user belongs to.",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions_set",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )

    USERNAME_FIELD = "email"  # login by email
    REQUIRED_FIELDS = ["username", "mobile"]

    def __str__(self):
        return self.username or self.email or str(self.mobile)


# ----------------- OTP MODEL -----------------
class OTP(models.Model):
    PURPOSES = (
        ("signup", "Signup"),
        ("login", "Login"),
        ("password_reset", "Password Reset"),
        ("verify_email", "Verify Email"),
        ("verify_mobile", "Verify Mobile"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="otps"
    )
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSES)
    sent_to_email = models.EmailField(blank=True, null=True)
    sent_to_mobile = models.CharField(max_length=15, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified = models.BooleanField(default=False)
    resend_count = models.PositiveIntegerField(default=0)

    @classmethod
    def create_for(cls, user, purpose="signup", email=None, mobile=None, minutes=10):
        """Safely create OTP"""
        if not user.pk:
            raise ValueError("User must be saved before creating OTP")
        return cls.objects.create(
            user=user,
            code=_gen_otp(),
            purpose=purpose,
            sent_to_email=email,
            sent_to_mobile=mobile,
            expires_at=timezone.now() + timedelta(minutes=minutes),
        )

    def is_valid(self, code):
        return not self.verified and self.code == code and timezone.now() <= self.expires_at

    def mark_verified(self):
        self.verified = True
        self.save(update_fields=["verified"])

    def __str__(self):
        return f"OTP {self.code} for {self.user} ({self.purpose})"


# ----------------- USER PROFILE MODEL -----------------
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company = models.CharField(max_length=255, blank=True, null=True)  # add this

    full_name = models.CharField(max_length=150)
    mobile = models.CharField(max_length=15)

    business_name = models.CharField(max_length=150, blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    gst_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    plan = models.ForeignKey(
        "billing.Plan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='account_userprofiles'
    )

    def __str__(self):
        return self.user.username


# ----------------- AUTO CREATE PROFILE ON USER CREATION -----------------
@receiver(post_save, sender=User)
def create_staff_profile(sender, instance, created, **kwargs):
    # Disabled – handled by khataapp
    pass

class DailySummary(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    total_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_transactions = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} - {self.date}"


class BusinessSnapshot(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_snapshots"
    )
    date = models.DateField(db_index=True)

    # SALES
    sales_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    sales_orders = models.PositiveIntegerField(default=0)

    # PURCHASE
    purchase_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    purchase_orders = models.PositiveIntegerField(default=0)

    # PAYMENTS
    payment_received = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_given = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # PARTY BALANCES
    receivable_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payable_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_position = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    profit_loss = models.DecimalField(
    max_digits=12,
    decimal_places=2,
    default=0
)

    # COUNTS
    total_parties = models.PositiveIntegerField(default=0)
    total_transactions = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user} | Snapshot | {self.date}"

# ----------------- Expences Model -----------------
class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Expense(models.Model):
    expense_number = models.CharField(max_length=20, unique=True)
    expense_date = models.DateField()

    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    description = models.TextField(blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.expense_number} - ₹{self.amount_paid}"
