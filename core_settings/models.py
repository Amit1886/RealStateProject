from django.db import models

class UISettings(models.Model):
    # 🎨 COLORS
    primary_color = models.CharField(max_length=20, default="#4f46e5")
    secondary_color = models.CharField(max_length=20, default="#0ea5e9")
    success_color = models.CharField(max_length=20, default="#16a34a")
    danger_color = models.CharField(max_length=20, default="#dc2626")

    # 🌙 THEME
    theme_mode = models.CharField(
        max_length=20,
        choices=[("light","Light"),("dark","Dark")],
        default="light"
    )

    # 📐 LAYOUT
    sidebar_position = models.CharField(
        max_length=20,
        choices=[("left","Left"),("right","Right")],
        default="left"
    )

    sidebar_collapsed = models.BooleanField(default=False)

    # 🧭 NAVIGATION
    show_dashboard = models.BooleanField(default=True)
    show_party = models.BooleanField(default=True)
    show_transaction = models.BooleanField(default=True)
    show_commerce = models.BooleanField(default=True)
    show_reports = models.BooleanField(default=True)
    show_settings = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "UI / Theme Settings"


class SaaSSettings(models.Model):
    enable_multi_company = models.BooleanField(default=False)
    enable_multi_user = models.BooleanField(default=True)

    enable_subscription = models.BooleanField(default=True)
    enable_trial = models.BooleanField(default=True)
    trial_days = models.PositiveIntegerField(default=7)

    enable_audit_logs = models.BooleanField(default=True)
    enable_api_access = models.BooleanField(default=False)

    def __str__(self):
        return "SaaS Settings"


class CompanySettings(models.Model):
    company_name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        verbose_name = "Company Setting"
        verbose_name_plural = "Company Settings"

    def __str__(self):
        return self.company_name


class AppSettings(models.Model):
    # 🏢 Company
    company_name = models.CharField(max_length=200)
    currency_symbol = models.CharField(max_length=10, default="₹")
    financial_year_start = models.DateField()

    # 🔐 System
    maintenance_mode = models.BooleanField(default=False)
    enable_notifications = models.BooleanField(default=True)
    enable_chat = models.BooleanField(default=True)

    # 👤 Users
    allow_user_signup = models.BooleanField(default=True)
    allow_social_login = models.BooleanField(default=True)

    # 📊 Dashboard
    show_profit_loss = models.BooleanField(default=True)
    show_daily_summary = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Global App Settings"


class ModuleSettings(models.Model):
    MODULE_CHOICES = [
        ("party", "Party"),
        ("transaction", "Transaction"),
        ("commerce", "Commerce"),
        ("billing", "Billing"),
        ("stock", "Stock"),
        ("warehouse", "Warehouse"),
        ("payment", "Payment"),
        ("subscription", "Subscription"),
    ]

    module = models.CharField(max_length=50, choices=MODULE_CHOICES, unique=True)

    enabled = models.BooleanField(default=True)

    settings = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.module.title()} Settings"


class FeatureSettings(models.Model):
    FEATURE_CHOICES = [
        ("otp", "OTP System"),
        ("emi", "EMI"),
        ("gst", "GST"),
        ("chat", "Chat"),
        ("payment_gateway", "Payment Gateway"),
        ("notification", "Notifications"),
        ("daily_summary", "Daily Summary"),
    ]

    feature = models.CharField(max_length=50, choices=FEATURE_CHOICES, unique=True)

    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.feature.title()} Feature"
