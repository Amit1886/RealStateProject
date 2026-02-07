from django.db import models
from django.conf import settings
from django.db.models import Q

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


# -----------------------------
# Unified Settings Center Models
# -----------------------------

class SettingCategory(models.Model):
    slug = models.SlugField(max_length=80, unique=True)
    label = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "label"]

    def __str__(self):
        return self.label


class SettingDefinition(models.Model):
    DATA_TYPES = [
        ("string", "String"),
        ("text", "Text"),
        ("number", "Number"),
        ("boolean", "Boolean"),
        ("select", "Select"),
        ("json", "JSON"),
        ("date", "Date"),
    ]

    SCOPE_CHOICES = [
        ("global", "Global"),
        ("user", "User"),
    ]

    category = models.ForeignKey(SettingCategory, on_delete=models.CASCADE, related_name="definitions")
    key = models.SlugField(max_length=120, unique=True)
    label = models.CharField(max_length=160)
    help_text = models.CharField(max_length=255, blank=True)
    data_type = models.CharField(max_length=20, choices=DATA_TYPES, default="string")
    default_value = models.JSONField(default=dict, blank=True)
    options = models.JSONField(default=list, blank=True)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default="global")
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "label"]

    def __str__(self):
        return self.label


class SettingValue(models.Model):
    definition = models.ForeignKey(SettingDefinition, on_delete=models.CASCADE, related_name="values")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="settings_values",
    )
    value = models.JSONField(default=dict, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="settings_updates",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["definition", "owner"],
                condition=Q(owner__isnull=False),
                name="unique_setting_value_owner",
            ),
            models.UniqueConstraint(
                fields=["definition"],
                condition=Q(owner__isnull=True),
                name="unique_setting_value_global",
            ),
        ]

    def __str__(self):
        owner = self.owner.username if self.owner else "global"
        return f"{self.definition.key} ({owner})"


class SettingHistory(models.Model):
    definition = models.ForeignKey(SettingDefinition, on_delete=models.CASCADE, related_name="history")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="settings_history",
    )
    previous_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="settings_history_updates",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        owner = self.owner.username if self.owner else "global"
        return f"{self.definition.key} change ({owner})"


class SettingPermission(models.Model):
    ROLE_CHOICES = [
        ("super_admin", "Super Admin"),
        ("admin", "Admin"),
        ("manager", "Manager"),
        ("user", "User"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    category = models.ForeignKey(SettingCategory, on_delete=models.CASCADE, related_name="permissions")
    can_view = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=True)
    hidden = models.BooleanField(default=False)

    class Meta:
        unique_together = ("role", "category")

    def __str__(self):
        return f"{self.role} -> {self.category.slug}"
