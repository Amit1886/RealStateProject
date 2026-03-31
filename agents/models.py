from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Agent(models.Model):
    """
    Lightweight agent profile that sits on top of the existing auth User.
    Stores serviceable PIN codes and performance snapshots used by the lead router.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agent_profile",
    )
    company = models.ForeignKey(
        "core_settings.CompanySettings",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agents",
    )
    name = models.CharField(max_length=160, blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    license_number = models.CharField(max_length=80, blank=True, default="", db_index=True)
    profile_image = models.ImageField(upload_to="agent_profiles/", null=True, blank=True)
    address = models.TextField(blank=True, default="")
    country = models.CharField(max_length=120, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    district = models.CharField(max_length=120, blank=True, default="")
    state = models.CharField(max_length=120, blank=True, default="")
    tehsil = models.CharField(max_length=120, blank=True, default="")
    village = models.CharField(max_length=120, blank=True, default="")
    pin_code = models.CharField(max_length=12, blank=True, default="", db_index=True)
    experience_years = models.PositiveIntegerField(default=0)

    class Specialization(models.TextChoices):
        RESIDENTIAL = "residential", "Residential"
        COMMERCIAL = "commercial", "Commercial"
        PLOTS = "plots", "Plots"

    specialization = models.CharField(max_length=20, choices=Specialization.choices, default=Specialization.RESIDENTIAL)
    kyc_verified = models.BooleanField(default=False, db_index=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0.00"))
    performance_score = models.PositiveIntegerField(default=0, db_index=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("2.00"))
    total_sales = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_visits = models.PositiveIntegerField(default=0)
    last_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_updated_at = models.DateTimeField(null=True, blank=True)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    assigned_location = models.JSONField(default=dict, blank=True)
    current_location = models.JSONField(default=dict, blank=True)
    last_ping_at = models.DateTimeField(null=True, blank=True)
    under_review = models.BooleanField(default=False, help_text="Flagged by fraud engine; payouts may be blocked")
    kyc_document = models.FileField(upload_to="agent_kyc/", null=True, blank=True)
    kyc_status = models.CharField(
        max_length=20,
        default="pending",
        choices=(("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected")),
        db_index=True,
    )
    kyc_verified_at = models.DateTimeField(null=True, blank=True, db_index=True)

    pincodes = models.JSONField(
        default=list,
        blank=True,
        help_text="List of PIN/ZIP codes the agent services (strings).",
    )
    service_areas = models.ManyToManyField(
        "location.Pincode",
        related_name="agents",
        blank=True,
        help_text="Optional normalized mapping to location.Pincode rows.",
    )
    parent_agent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_agents",
        help_text="Team hierarchy (parent/manager agent).",
    )
    mlm_level = models.PositiveIntegerField(default=0, help_text="Cached MLM depth level")

    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SUSPENDED = "suspended", "Suspended"

    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
    )
    franchise_name = models.CharField(max_length=160, blank=True, default="")

    is_active = models.BooleanField(default=True, db_index=True)
    performance = models.JSONField(default=dict, blank=True)
    last_assigned_at = models.DateTimeField(null=True, blank=True)
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    risk_level = models.CharField(
        max_length=16,
        default="low",
        choices=(("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")),
    )
    is_blocked = models.BooleanField(default=False)
    frozen_wallet = models.BooleanField(default=False, help_text="If true, payouts are withheld")
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_logout_at = models.DateTimeField(null=True, blank=True)
    avg_response_time_seconds = models.PositiveIntegerField(default=0)
    activity_log = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["approval_status", "is_active"]),
            models.Index(fields=["state", "district", "pin_code"]),
            models.Index(fields=["license_number"]),
            models.Index(fields=["performance_score", "is_active"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self) -> str:
        return self.name or getattr(self.user, "username", f"Agent {self.pk}")

    # ----------------- Helpers -----------------
    def all_pincodes(self) -> set[str]:
        codes = {str(c).strip() for c in (self.pincodes or []) if str(c).strip()}
        if self.pin_code:
            codes.add(str(self.pin_code).strip())
        for pincode in self.service_areas.all():
            if getattr(pincode, "code", None):
                codes.add(str(pincode.code))
        for coverage in self.coverage_areas.all():
            if getattr(coverage, "pin_code", None):
                codes.add(str(coverage.pin_code).strip())
        return codes

    def bump_last_assigned(self):
        self.last_assigned_at = timezone.now()
        self.save(update_fields=["last_assigned_at", "updated_at"])

    def record_closure(self, amount: Decimal | float | int = 0):
        perf = self.performance or {}
        perf["closed_leads"] = int(perf.get("closed_leads", 0)) + 1
        perf["revenue"] = float(Decimal(str(perf.get("revenue", 0))) + Decimal(str(amount or 0)))
        self.performance = perf
        self.total_sales = Decimal(str(self.total_sales)) + Decimal(str(amount or 0))
        self.save(update_fields=["performance", "total_sales", "updated_at"])

    def record_visit(self):
        self.total_visits = (self.total_visits or 0) + 1
        self.save(update_fields=["total_visits", "updated_at"])


class AgentLocationLog(models.Model):
    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="location_logs")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["agent", "timestamp"])]

    def __str__(self):
        return f"{self.agent_id} @ {self.timestamp}"


class AgentRiskProfile(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    agent = models.OneToOneField("agents.Agent", on_delete=models.CASCADE, related_name="risk_profile")
    risk_score = models.PositiveIntegerField(default=0)
    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices, default=RiskLevel.LOW)
    last_evaluated = models.DateTimeField(null=True, blank=True)
    notes = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.agent_id}:{self.risk_score}"


class AgentActivityLog(models.Model):
    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="activity_logs")
    action = models.CharField(max_length=80, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["agent", "action", "created_at"])]


class AgentSession(models.Model):
    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="sessions")
    login_at = models.DateTimeField(auto_now_add=True)
    logout_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-login_at"]
        indexes = [models.Index(fields=["agent", "login_at"])]


class AgentPerformanceSnapshot(models.Model):
    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="performance_snapshots")
    date = models.DateField(db_index=True)
    leads_assigned = models.PositiveIntegerField(default=0)
    leads_closed = models.PositiveIntegerField(default=0)
    total_leads = models.PositiveIntegerField(default=0)
    closed_leads = models.PositiveIntegerField(default=0)
    closing_ratio = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    visits = models.PositiveIntegerField(default=0)
    risk_score = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        unique_together = [("agent", "date")]


class AgentTransfer(models.Model):
    class TransferType(models.TextChoices):
        LEADS = "leads", "Leads"
        DEALS = "deals", "Deals"
        BOTH = "both", "Both"

    old_agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="transfers_out")
    new_agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="transfers_in")
    transferred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_transfers_performed",
    )
    transfer_type = models.CharField(max_length=20, choices=TransferType.choices, default=TransferType.BOTH, db_index=True)
    reason = models.CharField(max_length=255, blank=True, default="")
    reassigned_leads = models.PositiveIntegerField(default=0)
    reassigned_deals = models.PositiveIntegerField(default=0)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["old_agent", "new_agent", "created_at"]),
            models.Index(fields=["transfer_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.old_agent_id}->{self.new_agent_id}:{self.transfer_type}"


class AgentCoverageArea(models.Model):
    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="coverage_areas")
    country = models.CharField(max_length=120, blank=True, default="")
    state = models.CharField(max_length=120, blank=True, default="", db_index=True)
    district = models.CharField(max_length=120, blank=True, default="", db_index=True)
    tehsil = models.CharField(max_length=120, blank=True, default="")
    village = models.CharField(max_length=120, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="", db_index=True)
    pin_code = models.CharField(max_length=12, blank=True, default="", db_index=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "state", "district", "city", "pin_code"]
        indexes = [
            models.Index(fields=["agent", "is_active"]),
            models.Index(fields=["pin_code", "is_active"]),
            models.Index(fields=["district", "is_active"]),
            models.Index(fields=["state", "is_active"]),
        ]

    def __str__(self):
        label = self.pin_code or self.city or self.district or self.state or f"Coverage {self.pk}"
        return f"{self.agent_id}:{label}"


class AgentVerification(models.Model):
    class DocumentType(models.TextChoices):
        LICENSE = "license", "License"
        PAN = "pan", "PAN"
        AADHAAR = "aadhaar", "Aadhaar"
        AGREEMENT = "agreement", "Agreement"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="verifications")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices, default=DocumentType.OTHER, db_index=True)
    document_file = models.FileField(upload_to="agent_verifications/")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    remarks = models.CharField(max_length=255, blank=True, default="")
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_verifications_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agent", "status", "created_at"]),
            models.Index(fields=["document_type", "status"]),
        ]

    def __str__(self):
        return f"{self.agent_id}:{self.document_type}:{self.status}"


# Register additional models in this app
from .wallet import AgentWallet, WalletTransaction  # noqa: F401,E402
