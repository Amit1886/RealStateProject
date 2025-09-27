from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
import random


def _gen_otp():
    """Generate 6-digit numeric OTP"""
    return str(random.randint(100000, 999999))


# ----------------- User -----------------
class User(AbstractUser):
    username = models.CharField(max_length=150, unique=False, blank=True, null=True)
    mobile = models.CharField(max_length=15, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)

    email_verified = models.BooleanField(default=False)
    mobile_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"   # Login using email by default
    REQUIRED_FIELDS = ["username", "mobile"]

    def __str__(self):
        return self.username or self.email or str(self.mobile)


# ----------------- Plan -----------------
class Plan(models.Model):
    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    is_free = models.BooleanField(default=False, help_text="Free plan assign hoga signup pe")
    features = models.TextField(blank=True, null=True, help_text="Add one feature per line")

    def feature_list(self):
        """Return features as list"""
        return [f.strip() for f in self.features.splitlines() if f.strip()]

    def __str__(self):
        return f"{self.name} ({'Free' if self.is_free else '₹'+str(self.price)})"


# ----------------- OTP -----------------
class OTP(models.Model):
    PURPOSES = (
        ("signup", "Signup"),
        ("login", "Login"),
        ("password_reset", "Password Reset"),
        ("verify_email", "Verify Email"),
        ("verify_mobile", "Verify Mobile"),
        ("mobile_verification", "Mobile Verification"),  # For Google/social login
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSES)
    sent_to_email = models.EmailField(blank=True, null=True)
    sent_to_mobile = models.CharField(max_length=15, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified = models.BooleanField(default=False)
    resend_count = models.PositiveIntegerField(default=0)

    @classmethod
    def create_for(cls, user, purpose, email=None, mobile=None, minutes=10):
        """Create and return new OTP"""
        return cls.objects.create(
            user=user,
            code=_gen_otp(),
            purpose=purpose,
            sent_to_email=email,
            sent_to_mobile=mobile,
            expires_at=timezone.now() + timedelta(minutes=minutes),
        )

    def is_valid(self, code):
        """Check if OTP is valid"""
        return (
            not self.verified
            and self.code == code
            and timezone.now() <= self.expires_at
        )

    def mark_verified(self):
        """Mark OTP as used/verified"""
        self.verified = True
        self.save(update_fields=["verified"])

    def __str__(self):
        return f"OTP {self.code} for {self.user} ({self.purpose})"


# ----------------- UserProfile -----------------
class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,   # ✅ yeh change hai
        on_delete=models.CASCADE,
        related_name="accounts_profile"
    )
    mobile = models.CharField(max_length=15, blank=True, null=True)
    otp_verified = models.BooleanField(default=False)
    plan = models.CharField(
        max_length=20,
        choices=[("free", "Free"), ("basic", "Basic"), ("premium", "Premium")],
        default="free"
    )

    def __str__(self):
        return self.user.username
