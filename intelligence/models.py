from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models


class PropertyImportBatch(models.Model):
    class SourceType(models.TextChoices):
        PUBLIC = "public", "Public Source"
        PARTNER = "partner", "Partner Feed"
        INTERNAL = "internal", "Internal Feed"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    company = models.ForeignKey(
        "saas_core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="property_import_batches",
    )
    source_name = models.CharField(max_length=120, db_index=True)
    source_type = models.CharField(max_length=20, choices=SourceType.choices, default=SourceType.PARTNER, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    scheduled_for = models.DateTimeField(null=True, blank=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    fetched_count = models.PositiveIntegerField(default=0)
    inserted_count = models.PositiveIntegerField(default=0)
    duplicate_count = models.PositiveIntegerField(default=0)
    normalized_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status", "scheduled_for"]),
            models.Index(fields=["source_name", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.source_name}:{self.status}:{self.pk}"


class AggregatedProperty(models.Model):
    company = models.ForeignKey(
        "saas_core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="aggregated_properties",
    )
    import_batch = models.ForeignKey(
        PropertyImportBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="properties",
    )
    matched_property = models.ForeignKey(
        "leads.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="aggregated_records",
    )
    duplicate_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicates",
    )
    source = models.CharField(max_length=120, db_index=True)
    source_reference = models.CharField(max_length=160, blank=True, default="", db_index=True)
    title = models.CharField(max_length=200)
    normalized_title = models.CharField(max_length=200, blank=True, default="", db_index=True)
    location = models.CharField(max_length=200, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="", db_index=True)
    district = models.CharField(max_length=120, blank=True, default="", db_index=True)
    state = models.CharField(max_length=120, blank=True, default="", db_index=True)
    pin_code = models.CharField(max_length=12, blank=True, default="", db_index=True)
    price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    property_type = models.CharField(max_length=40, blank=True, default="", db_index=True)
    area_sqft = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    duplicate_key = models.CharField(max_length=200, blank=True, default="", db_index=True)
    is_duplicate = models.BooleanField(default=False, db_index=True)
    aggregated_property = models.BooleanField(default=True, db_index=True)
    import_date = models.DateTimeField(db_index=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    normalized_payload = models.JSONField(default=dict, blank=True)
    enrichment_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-import_date", "-created_at"]
        indexes = [
            models.Index(fields=["company", "duplicate_key"]),
            models.Index(fields=["city", "district", "state", "property_type"]),
            models.Index(fields=["source", "source_reference"]),
        ]

    def __str__(self) -> str:
        return f"{self.source}:{self.title}"


class DemandHeatmapSnapshot(models.Model):
    company = models.ForeignKey(
        "saas_core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="demand_heatmaps",
    )
    snapshot_date = models.DateField(db_index=True)
    city = models.CharField(max_length=120, blank=True, default="", db_index=True)
    district = models.CharField(max_length=120, blank=True, default="", db_index=True)
    search_count = models.PositiveIntegerField(default=0)
    lead_count = models.PositiveIntegerField(default=0)
    property_view_count = models.PositiveIntegerField(default=0)
    closed_deal_count = models.PositiveIntegerField(default=0)
    supply_count = models.PositiveIntegerField(default=0)
    demand_score = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    low_supply_score = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    hot_investment_score = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-snapshot_date", "-demand_score"]
        unique_together = [("company", "snapshot_date", "city", "district")]
        indexes = [
            models.Index(fields=["company", "snapshot_date"]),
            models.Index(fields=["city", "district", "snapshot_date"]),
        ]


class PriceTrendSnapshot(models.Model):
    company = models.ForeignKey(
        "saas_core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="price_trends",
    )
    snapshot_date = models.DateField(db_index=True)
    city = models.CharField(max_length=120, blank=True, default="", db_index=True)
    district = models.CharField(max_length=120, blank=True, default="", db_index=True)
    property_type = models.CharField(max_length=40, blank=True, default="", db_index=True)
    average_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    price_change_percent = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    historical_prices = models.JSONField(default=list, blank=True)
    sample_size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-snapshot_date", "-average_price"]
        unique_together = [("company", "snapshot_date", "city", "district", "property_type")]
        indexes = [
            models.Index(fields=["company", "snapshot_date"]),
            models.Index(fields=["city", "district", "property_type"]),
        ]


class InvestorProfile(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="investor_profile",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "saas_core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="investors",
    )
    name = models.CharField(max_length=160, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    investment_budget = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    preferred_cities = models.JSONField(default=list, blank=True)
    property_type_preferences = models.JSONField(default=list, blank=True)
    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices, default=RiskLevel.MEDIUM, db_index=True)
    min_roi_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("8.00"))
    active = models.BooleanField(default=True, db_index=True)
    alerts_enabled = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["company", "active", "risk_level"]),
            models.Index(fields=["investment_budget", "active"]),
        ]

    def __str__(self) -> str:
        return self.name or self.email or f"Investor {self.pk}"


class InvestorMatch(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        NOTIFIED = "notified", "Notified"
        VIEWED = "viewed", "Viewed"
        CONVERTED = "converted", "Converted"
        DISMISSED = "dismissed", "Dismissed"

    investor = models.ForeignKey(InvestorProfile, on_delete=models.CASCADE, related_name="matches")
    property = models.ForeignKey("leads.Property", on_delete=models.CASCADE, null=True, blank=True, related_name="investor_matches")
    project = models.ForeignKey("leads.PropertyProject", on_delete=models.CASCADE, null=True, blank=True, related_name="investor_matches")
    score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"), db_index=True)
    expected_roi_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    match_reason = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    notified_at = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-score", "-created_at"]
        indexes = [
            models.Index(fields=["investor", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]


class PropertyAlertSubscription(models.Model):
    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE, related_name="alert_subscriptions")
    company = models.ForeignKey(
        "saas_core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="property_alert_subscriptions",
    )
    preferred_location = models.CharField(max_length=160, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="", db_index=True)
    district = models.CharField(max_length=120, blank=True, default="", db_index=True)
    state = models.CharField(max_length=120, blank=True, default="", db_index=True)
    pin_code = models.CharField(max_length=12, blank=True, default="", db_index=True)
    property_type = models.CharField(max_length=40, blank=True, default="", db_index=True)
    min_budget = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    max_budget = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    channels = models.JSONField(default=list, blank=True, help_text="email/sms/whatsapp/in_app")
    trigger_types = models.JSONField(default=list, blank=True, help_text="new_property/price_drop/similar_property/builder_launch")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["city", "district", "property_type"]),
        ]


class PremiumLeadListing(models.Model):
    class Category(models.TextChoices):
        EXCLUSIVE = "exclusive", "Exclusive"
        HOT = "hot", "Hot"
        VERIFIED = "verified", "Verified"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        SOLD = "sold", "Sold"
        EXPIRED = "expired", "Expired"

    company = models.ForeignKey(
        "saas_core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="premium_lead_listings",
    )
    lead = models.OneToOneField("leads.Lead", on_delete=models.CASCADE, related_name="premium_listing")
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="premium_leads_listed",
    )
    buyer_agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="premium_leads_purchased",
    )
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.HOT, db_index=True)
    price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    description = models.CharField(max_length=255, blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status", "category"]),
            models.Index(fields=["status", "expires_at"]),
        ]


class LeadPurchase(models.Model):
    listing = models.ForeignKey(PremiumLeadListing, on_delete=models.CASCADE, related_name="purchases")
    lead = models.ForeignKey("leads.Lead", on_delete=models.CASCADE, related_name="lead_purchases")
    buyer_agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="lead_purchases")
    wallet_transaction_ref = models.CharField(max_length=120, blank=True, default="")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    purchased_at = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-purchased_at"]
        indexes = [models.Index(fields=["buyer_agent", "purchased_at"])]


class RealEstateDocument(models.Model):
    class DocumentType(models.TextChoices):
        SALE_AGREEMENT = "sale_agreement", "Sale Agreement"
        PROPERTY_DOCUMENT = "property_document", "Property Document"
        IDENTITY_VERIFICATION = "identity_verification", "Identity Verification"
        DEAL_CONTRACT = "deal_contract", "Deal Contract"
        OTHER = "other", "Other"

    class AccessScope(models.TextChoices):
        ADMIN = "admin", "Admin Only"
        AGENT = "agent", "Agent Access"
        CUSTOMER = "customer", "Customer Access"
        SHARED = "shared", "Shared"

    company = models.ForeignKey(
        "saas_core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="real_estate_documents",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="real_estate_documents_uploaded",
    )
    property = models.ForeignKey("leads.Property", on_delete=models.CASCADE, null=True, blank=True, related_name="documents")
    lead = models.ForeignKey("leads.Lead", on_delete=models.CASCADE, null=True, blank=True, related_name="secure_documents")
    deal = models.ForeignKey("deals.Deal", on_delete=models.CASCADE, null=True, blank=True, related_name="documents")
    builder = models.ForeignKey("leads.Builder", on_delete=models.CASCADE, null=True, blank=True, related_name="documents")
    project = models.ForeignKey("leads.PropertyProject", on_delete=models.CASCADE, null=True, blank=True, related_name="documents")
    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, null=True, blank=True, related_name="documents")
    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE, null=True, blank=True, related_name="documents")
    document_type = models.CharField(max_length=30, choices=DocumentType.choices, default=DocumentType.OTHER, db_index=True)
    access_scope = models.CharField(max_length=20, choices=AccessScope.choices, default=AccessScope.ADMIN, db_index=True)
    title = models.CharField(max_length=160, blank=True, default="")
    file = models.FileField(upload_to="real_estate_documents/")
    encrypted = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "document_type", "created_at"]),
            models.Index(fields=["access_scope", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.title or f"Document {self.pk}"
