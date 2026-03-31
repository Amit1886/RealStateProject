from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class LeadSource(models.Model):
    class Kind(models.TextChoices):
        FACEBOOK_ADS = "facebook_ads", "Facebook Ads"
        INSTAGRAM_ADS = "instagram_ads", "Instagram Ads"
        WEBSITE_FORM = "website_form", "Website Form"
        MANUAL = "manual", "Manual"
        CSV = "csv", "CSV Upload"
        WEB_SCRAPE = "web_scrape", "Web Scraping"
        API = "api", "API"
        WEBHOOK = "webhook", "Webhook"

    company = models.ForeignKey(
        "saas_core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="lead_sources",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, db_index=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.MANUAL, db_index=True)
    source_value = models.CharField(max_length=30, default="manual", db_index=True)
    webhook_secret = models.CharField(max_length=160, blank=True, default="")
    verify_token = models.CharField(max_length=160, blank=True, default="")
    endpoint_url = models.URLField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    auto_assign = models.BooleanField(default=True)
    default_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["slug", "is_active"]),
            models.Index(fields=["kind", "is_active"]),
        ]
        unique_together = [("company", "slug")]

    def __str__(self) -> str:
        return self.name


class Lead(models.Model):
    class CustomerType(models.TextChoices):
        BUYER = "buyer", "Buyer"
        INVESTOR = "investor", "Investor"
        RESELLER = "reseller", "Reseller"

    class Source(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        WHATSAPP_CHATBOT = "whatsapp_chatbot", "WhatsApp Chatbot"
        SMS = "sms", "SMS"
        EMAIL = "email", "Email"
        FACEBOOK = "facebook", "Facebook"
        FACEBOOK_ADS = "facebook_ads", "Facebook Ads"
        INSTAGRAM = "instagram", "Instagram"
        INSTAGRAM_ADS = "instagram_ads", "Instagram Ads"
        GOOGLE = "google", "Google"
        GOOGLE_ADS = "google_ads", "Google Ads"
        TELEGRAM = "telegram", "Telegram"
        YOUTUBE = "youtube", "YouTube"
        API = "api", "API"
        WEBSITE = "website", "Website"
        LANDING_PAGE = "landing_page", "Landing Page"
        MISSED_CALL = "missed_call", "Missed Call"
        REFERRAL = "referral", "Referral"
        MANUAL = "manual", "Manual"

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        FOLLOW_UP = "follow_up", "Follow Up"
        IN_PROGRESS = "in_progress", "In Progress"
        CONVERTED = "converted", "Converted"
        CLOSED = "closed", "Closed"
        HOT = "hot", "Hot"
        WARM = "warm", "Warm"
        COLD = "cold", "Cold"
        QUALIFIED = "qualified", "Qualified"
        WON = "won", "Won"
        LOST = "lost", "Lost"
        INACTIVE = "inactive", "Inactive"

    class Stage(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        FOLLOW_UP = "follow_up", "Follow Up"
        INTERESTED = "interested", "Interested"
        VISIT_SCHEDULED = "visit_scheduled", "Visit Scheduled"
        QUALIFIED = "qualified", "Qualified"
        SITE_VISIT = "site_visit", "Site Visit"
        VISIT = "visit", "Visit Scheduled"
        NEGOTIATION = "negotiation", "Negotiation"
        CONVERTED = "converted", "Converted"
        CLOSED = "closed", "Closed"
        DEAL_CLOSED = "deal_closed", "Deal Closed"
        LOST_LEAD = "lost_lead", "Lost Lead"

    class InterestType(models.TextChoices):
        BUY = "buy", "Buy"
        SELL = "sell", "Sell"
        RENT = "rent", "Rent"

    company = models.ForeignKey(
        "saas_core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="leads",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads_created",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads_assigned",
        db_index=True,
    )
    source_config = models.ForeignKey(
        "leads.LeadSource",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )
    assigned_agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
        db_index=True,
    )
    interested_property = models.ForeignKey(
        "leads.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inquiries",
    )
    converted_customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="originated_leads",
    )
    duplicate_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicates",
    )

    name = models.CharField(max_length=160, blank=True, default="")
    mobile = models.CharField(max_length=20, blank=True, default="", db_index=True)
    email = models.EmailField(blank=True, default="")
    deal_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.NEW, db_index=True)
    interest_type = models.CharField(max_length=10, choices=InterestType.choices, default=InterestType.BUY, db_index=True)
    property_type = models.CharField(max_length=40, blank=True, default="")
    budget = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    preferred_location = models.CharField(max_length=160, blank=True, default="")
    geo_location = models.JSONField(default=dict, blank=True, help_text="Lat/Lng if captured from maps or forms")
    lead_score = models.PositiveIntegerField(default=0, db_index=True, help_text="0-100 AI score")
    customer_type = models.CharField(max_length=20, choices=CustomerType.choices, default=CustomerType.BUYER, db_index=True)
    reliability_score = models.PositiveIntegerField(default=100, db_index=True)
    no_show_count = models.PositiveIntegerField(default=0)

    class Temperature(models.TextChoices):
        HOT = "hot", "Hot"
        WARM = "warm", "Warm"
        COLD = "cold", "Cold"

    temperature = models.CharField(max_length=10, choices=Temperature.choices, default=Temperature.WARM, db_index=True)
    preferred_property_type = models.CharField(max_length=40, blank=True, default="")
    preferred_bedrooms = models.PositiveIntegerField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    country = models.CharField(max_length=120, blank=True, default="")
    state = models.CharField(max_length=120, blank=True, default="", db_index=True)
    district = models.CharField(max_length=120, blank=True, default="", db_index=True)
    tehsil = models.CharField(max_length=120, blank=True, default="")
    village = models.CharField(max_length=120, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="", db_index=True)
    notes = models.TextField(blank=True, default="")

    source = models.CharField(max_length=30, choices=Source.choices, default=Source.MANUAL, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    score = models.IntegerField(default=0, db_index=True)

    pincode_text = models.CharField(max_length=12, blank=True, default="")
    pincode = models.ForeignKey(
        "location.Pincode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )
    metadata = models.JSONField(default=dict, blank=True)
    distribution_level = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=(
            ("pin_code", "Pin Code"),
            ("district", "District"),
            ("state", "State"),
            ("city", "City"),
            ("manual", "Manual"),
            ("fallback", "Fallback"),
        ),
    )
    distribution_reason = models.CharField(max_length=200, blank=True, default="")
    assigned_at = models.DateTimeField(null=True, blank=True)
    agent_first_response_at = models.DateTimeField(null=True, blank=True)
    last_reassigned_at = models.DateTimeField(null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_duplicate = models.BooleanField(default=False, db_index=True)
    duplicate_reason = models.CharField(max_length=160, blank=True, default="")
    is_locked = models.BooleanField(default=False, db_index=True)
    locked_by = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locked_leads",
    )
    locked_at = models.DateTimeField(null=True, blank=True, db_index=True)
    lock_reason = models.CharField(max_length=255, blank=True, default="")

    next_followup_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_followup_at = models.DateTimeField(null=True, blank=True)
    followup_channel = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=(("whatsapp", "WhatsApp"), ("email", "Email"), ("sms", "SMS")),
    )
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    stage_updated_at = models.DateTimeField(null=True, blank=True, db_index=True)
    stage_deadline = models.DateTimeField(null=True, blank=True, db_index=True)
    is_overdue = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status", "created_at"]),
            models.Index(fields=["company", "assigned_to", "status"]),
            models.Index(fields=["company", "assigned_agent", "status"]),
            models.Index(fields=["mobile"]),
            models.Index(fields=["pincode_text", "district", "state"]),
            models.Index(fields=["stage", "created_at"]),
            models.Index(fields=["is_duplicate", "created_at"]),
            models.Index(fields=["converted_customer", "converted_at"]),
        ]

    def touch_contacted(self):
        self.last_contacted_at = timezone.now()
        self.save(update_fields=["last_contacted_at", "updated_at"])

    def record_no_show(self, penalty: int = 10):
        self.no_show_count = (self.no_show_count or 0) + 1
        self.reliability_score = max(0, int(self.reliability_score or 0) - max(0, int(penalty or 0)))
        self.save(update_fields=["no_show_count", "reliability_score", "updated_at"])

    def mark_status(self, status: str, actor=None, note: str = ""):
        previous_status = self.status
        self.status = status
        self.stage_updated_at = timezone.now()
        if status == self.Status.CONTACTED:
            self.last_contacted_at = timezone.now()
            if self.stage == self.Stage.NEW:
                self.stage = self.Stage.CONTACTED
        elif status == self.Status.FOLLOW_UP:
            self.stage = self.Stage.FOLLOW_UP
        elif status == self.Status.CONVERTED:
            self.stage = self.Stage.CONVERTED
            if not self.converted_at:
                self.converted_at = timezone.now()
        elif status == self.Status.CLOSED:
            self.stage = self.Stage.DEAL_CLOSED
        elif status == self.Status.LOST:
            self.stage = self.Stage.LOST_LEAD
        self.save(update_fields=["status", "stage", "last_contacted_at", "converted_at", "stage_updated_at", "updated_at"])
        LeadActivity.objects.create(
            lead=self,
            actor=actor,
            activity_type="status_change",
            note=(note or "")[:300],
            payload={"from": previous_status, "to": status},
        )

    def __str__(self) -> str:
        return f"{self.name or self.mobile} ({self.status})"


class LeadActivity(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="activities")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    activity_type = models.CharField(max_length=40, default="note", db_index=True)
    note = models.TextField(blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["lead", "created_at"])]


class LeadAssignmentLog(models.Model):
    class AssignmentType(models.TextChoices):
        AUTO = "auto", "Auto"
        MANUAL = "manual", "Manual"
        REASSIGN = "reassign", "Reassign"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="assignment_logs")
    agent = models.ForeignKey("agents.Agent", on_delete=models.SET_NULL, null=True, blank=True, related_name="assignment_logs")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    assignment_type = models.CharField(max_length=20, choices=AssignmentType.choices, default=AssignmentType.AUTO)
    matched_on = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=(
            ("pin_code", "Pin Code"),
            ("district", "District"),
            ("state", "State"),
            ("city", "City"),
            ("manual", "Manual"),
            ("fallback", "Fallback"),
        ),
    )
    note = models.CharField(max_length=300, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["lead", "created_at"]), models.Index(fields=["agent", "created_at"])]


class LeadAssignment(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="assignments")
    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="lead_assignments")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    assignment_type = models.CharField(max_length=20, choices=LeadAssignmentLog.AssignmentType.choices, default=LeadAssignmentLog.AssignmentType.AUTO)
    matched_on = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=(
            ("pin_code", "Pin Code"),
            ("district", "District"),
            ("tehsil", "Tehsil"),
            ("village", "Village"),
            ("state", "State"),
            ("city", "City"),
            ("manual", "Manual"),
            ("fallback", "Fallback"),
            ("nearest", "Nearest"),
        ),
    )
    reason = models.CharField(max_length=300, blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    response_due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    first_contact_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lead", "is_active"]),
            models.Index(fields=["agent", "is_active"]),
            models.Index(fields=["response_due_at", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.lead_id}->{self.agent_id}"


class LeadImportBatch(models.Model):
    class ImportType(models.TextChoices):
        CSV = "csv", "CSV Upload"
        WEBHOOK = "webhook", "Webhook"
        API = "api", "API"
        WEB_SCRAPE = "web_scrape", "Web Scrape"
        MANUAL = "manual", "Manual"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    company = models.ForeignKey("saas_core.Company", on_delete=models.CASCADE, null=True, blank=True, related_name="lead_import_batches")
    source = models.ForeignKey(LeadSource, on_delete=models.SET_NULL, null=True, blank=True, related_name="import_batches")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="lead_import_batches")
    import_type = models.CharField(max_length=20, choices=ImportType.choices, default=ImportType.MANUAL, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    file = models.FileField(upload_to="lead_imports/", null=True, blank=True)
    external_reference = models.CharField(max_length=160, blank=True, default="", db_index=True)
    source_name = models.CharField(max_length=120, blank=True, default="")
    total_rows = models.PositiveIntegerField(default=0)
    processed_rows = models.PositiveIntegerField(default=0)
    created_leads = models.PositiveIntegerField(default=0)
    duplicate_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    error_report = models.JSONField(default=list, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status", "created_at"]),
            models.Index(fields=["import_type", "status"]),
            models.Index(fields=["external_reference"]),
        ]

    def __str__(self) -> str:
        return f"{self.import_type}:{self.status}:{self.pk}"


# ---------- Property & Marketplace ----------


class Builder(models.Model):
    name = models.CharField(max_length=160)
    company_name = models.CharField(max_length=200, blank=True, default="")
    registration_number = models.CharField(max_length=120, blank=True, default="", db_index=True)
    contact = models.CharField(max_length=50, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    website = models.URLField(blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="", db_index=True)
    verified = models.BooleanField(default=False)
    company = models.ForeignKey("saas_core.Company", on_delete=models.CASCADE, null=True, blank=True, related_name="builders")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["company_name", "city"]),
            models.Index(fields=["registration_number"]),
        ]

    def __str__(self):
        return self.company_name or self.name


class Property(models.Model):
    class ListingType(models.TextChoices):
        SALE = "sale", "Sale"
        RENT = "rent", "Rent"
        LEASE = "lease", "Lease"

    class Type(models.TextChoices):
        HOUSE = "house", "House"
        FLAT = "flat", "Flat"
        APARTMENT = "apartment", "Apartment"
        VILLA = "villa", "Villa"
        LAND = "land", "Land"
        PLOT = "plot", "Plot"
        COMMERCIAL = "commercial", "Commercial"
        OFFICE = "office", "Office"
        SHOP = "shop", "Shop"
        WAREHOUSE = "warehouse", "Warehouse"

    class Furnishing(models.TextChoices):
        UNFURNISHED = "unfurnished", "Unfurnished"
        SEMI_FURNISHED = "semi_furnished", "Semi Furnished"
        FURNISHED = "furnished", "Furnished"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ACTIVE = "active", "Active"
        SOLD = "sold", "Sold"
        RENTED = "rented", "Rented"

    title = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=14, decimal_places=2)
    city = models.CharField(max_length=120)
    location = models.CharField(max_length=160, blank=True, default="")
    district = models.CharField(max_length=120, blank=True, default="", db_index=True)
    state = models.CharField(max_length=120, blank=True, default="", db_index=True)
    country = models.CharField(max_length=120, blank=True, default="")
    tehsil = models.CharField(max_length=120, blank=True, default="")
    village = models.CharField(max_length=120, blank=True, default="")
    pin_code = models.CharField(max_length=12, blank=True, default="", db_index=True)
    property_type = models.CharField(max_length=20, choices=Type.choices, default=Type.APARTMENT)
    listing_type = models.CharField(max_length=12, choices=ListingType.choices, default=ListingType.SALE)
    area_sqft = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    bedrooms = models.PositiveIntegerField(null=True, blank=True)
    bathrooms = models.PositiveIntegerField(null=True, blank=True)
    balcony = models.PositiveIntegerField(default=0)
    parking = models.PositiveIntegerField(default=0)
    furnishing = models.CharField(max_length=20, choices=Furnishing.choices, default=Furnishing.UNFURNISHED)
    description = models.TextField(blank=True, default="")
    video_url = models.URLField(blank=True, default="")
    video_file = models.FileField(upload_to="property_videos/", null=True, blank=True)
    builder = models.ForeignKey(Builder, on_delete=models.SET_NULL, null=True, blank=True, related_name="properties")
    company = models.ForeignKey("saas_core.Company", on_delete=models.CASCADE, null=True, blank=True, related_name="properties")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="properties_owned")
    assigned_agent = models.ForeignKey("agents.Agent", on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_properties")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_APPROVAL, db_index=True)
    aggregated_property = models.BooleanField(default=False, db_index=True)
    data_source = models.CharField(max_length=120, blank=True, default="", db_index=True)
    import_date = models.DateTimeField(null=True, blank=True, db_index=True)
    source_reference = models.CharField(max_length=160, blank=True, default="", db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status", "created_at"]),
            models.Index(fields=["status", "listing_type", "property_type"]),
            models.Index(fields=["city", "district", "state"]),
            models.Index(fields=["pin_code", "status"]),
            models.Index(fields=["assigned_agent", "status"]),
            models.Index(fields=["aggregated_property", "data_source"]),
            models.Index(fields=["source_reference"]),
        ]

    def __str__(self):
        return self.title


class PropertyProject(models.Model):
    class LaunchStatus(models.TextChoices):
        PRELAUNCH = "prelaunch", "Prelaunch"
        LIVE = "live", "Live"
        SOLDOUT = "soldout", "Sold Out"

    builder = models.ForeignKey(Builder, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=200)
    location = models.CharField(max_length=160)
    city = models.CharField(max_length=120, blank=True, default="", db_index=True)
    price_range = models.CharField(max_length=120, blank=True, default="")
    starting_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    max_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    property_types = models.JSONField(default=list, blank=True)
    construction_status = models.CharField(max_length=40, blank=True, default="", db_index=True)
    completion_date = models.DateField(null=True, blank=True, db_index=True)
    pre_launch = models.BooleanField(default=False, db_index=True)
    launch_date = models.DateField(null=True, blank=True, db_index=True)
    pre_launch_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    launch_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=LaunchStatus.choices, default=LaunchStatus.PRELAUNCH, db_index=True)
    roi_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    description = models.TextField(blank=True, default="")
    approved = models.BooleanField(default=False)
    company = models.ForeignKey("saas_core.Company", on_delete=models.CASCADE, null=True, blank=True, related_name="property_projects")
    leads = models.ManyToManyField(Lead, related_name="project_launches", blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["city", "approved"]),
            models.Index(fields=["construction_status", "completion_date"]),
            models.Index(fields=["pre_launch", "approved"]),
        ]

    def __str__(self):
        return self.title


class ProjectPhase(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        HOLD = "hold", "On Hold"

    project = models.ForeignKey(PropertyProject, on_delete=models.CASCADE, related_name="phases")
    name = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED, db_index=True)
    properties = models.ManyToManyField("Property", blank=True, related_name="project_phases")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "id"]
        indexes = [
            models.Index(fields=["project", "status", "start_date"]),
            models.Index(fields=["name", "status"]),
        ]

    def __str__(self):
        return f"{self.project_id}:{self.name}"


class PropertyView(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="views")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["property", "timestamp"])]


class PropertyMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="media")
    media_type = models.CharField(max_length=10, choices=MediaType.choices, default=MediaType.IMAGE)
    file = models.FileField(upload_to="property_media/", null=True, blank=True)
    external_url = models.URLField(blank=True, default="")
    caption = models.CharField(max_length=160, blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [models.Index(fields=["property", "media_type", "sort_order"])]


class PropertyLocation(models.Model):
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name="location_detail")
    address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="", db_index=True)
    district = models.CharField(max_length=120, blank=True, default="", db_index=True)
    state = models.CharField(max_length=120, blank=True, default="", db_index=True)
    pin_code = models.CharField(max_length=12, blank=True, default="", db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["city", "district", "state"]),
            models.Index(fields=["pin_code", "updated_at"]),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        updates = {}
        if self.property.location != self.address:
            updates["location"] = self.address
        if self.property.city != self.city:
            updates["city"] = self.city
        if self.property.district != self.district:
            updates["district"] = self.district
        if self.property.state != self.state:
            updates["state"] = self.state
        if self.property.pin_code != self.pin_code:
            updates["pin_code"] = self.pin_code
        if self.property.latitude != self.latitude:
            updates["latitude"] = self.latitude
        if self.property.longitude != self.longitude:
            updates["longitude"] = self.longitude
        if updates:
            for field, value in updates.items():
                setattr(self.property, field, value)
            self.property.save(update_fields=[*updates.keys(), "updated_at"])

    def __str__(self):
        return f"{self.property_id}:{self.city or self.pin_code}"


class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="property_images/", null=True, blank=True)
    image_url = models.URLField(blank=True, default="")
    caption = models.CharField(max_length=160, blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [models.Index(fields=["property", "is_primary", "sort_order"])]

    def __str__(self):
        return f"{self.property_id}:image:{self.pk}"


class PropertyVideo(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="videos")
    video = models.FileField(upload_to="property_videos/", null=True, blank=True)
    video_url = models.URLField(blank=True, default="")
    caption = models.CharField(max_length=160, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["property", "created_at"])]

    def __str__(self):
        return f"{self.property_id}:video:{self.pk}"


class PropertyFeature(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="features")
    feature_name = models.CharField(max_length=120, db_index=True)
    feature_value = models.CharField(max_length=160, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["feature_name", "id"]
        indexes = [models.Index(fields=["property", "feature_name"])]

    def __str__(self):
        return f"{self.property_id}:{self.feature_name}"


class PropertyWishlist(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="wishlist_entries")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="property_wishlist")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("property", "user")]
        indexes = [models.Index(fields=["user", "created_at"])]


class FollowUp(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        CALL = "call", "Call"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="followups")
    message = models.TextField()
    followup_date = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.WHATSAPP, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    processed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["followup_date"]


class LeadDocument(models.Model):
    class DocType(models.TextChoices):
        KYC = "kyc", "KYC"
        AGREEMENT = "agreement", "Agreement"
        OTHER = "other", "Other"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=20, choices=DocType.choices, default=DocType.OTHER)
    title = models.CharField(max_length=160, blank=True, default="")
    file = models.FileField(upload_to="lead_documents/")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["lead", "doc_type", "created_at"])]


class Agreement(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="agreements")
    title = models.CharField(max_length=200)
    pdf_file = models.FileField(upload_to="agreements/", null=True, blank=True)
    status = models.CharField(max_length=20, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
