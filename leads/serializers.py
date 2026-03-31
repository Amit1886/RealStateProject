from rest_framework import serializers

from .models import (
    Agreement,
    Builder,
    FollowUp,
    Lead,
    LeadActivity,
    LeadAssignment,
    LeadAssignmentLog,
    LeadImportBatch,
    LeadDocument,
    LeadSource,
    Property,
    PropertyFeature,
    PropertyImage,
    PropertyLocation,
    PropertyMedia,
    PropertyVideo,
    PropertyProject,
    PropertyView,
    PropertyWishlist,
)


class LeadSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSource
        fields = [
            "id",
            "company",
            "name",
            "slug",
            "kind",
            "source_value",
            "webhook_secret",
            "verify_token",
            "endpoint_url",
            "is_active",
            "auto_assign",
            "default_metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class LeadActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.get_full_name", read_only=True)

    class Meta:
        model = LeadActivity
        fields = ["id", "lead", "actor", "actor_name", "activity_type", "note", "payload", "created_at"]
        read_only_fields = ["created_at"]


class LeadAssignmentLogSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source="agent.name", read_only=True)

    class Meta:
        model = LeadAssignmentLog
        fields = [
            "id",
            "lead",
            "agent",
            "agent_name",
            "assigned_by",
            "assignment_type",
            "matched_on",
            "note",
            "payload",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class LeadAssignmentSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source="agent.name", read_only=True)
    agent_phone = serializers.CharField(source="agent.phone", read_only=True)

    class Meta:
        model = LeadAssignment
        fields = [
            "id",
            "lead",
            "agent",
            "agent_name",
            "agent_phone",
            "assigned_by",
            "assignment_type",
            "matched_on",
            "reason",
            "is_active",
            "response_due_at",
            "first_contact_at",
            "released_at",
            "payload",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class LeadSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source="mobile")
    assigned_agent_name = serializers.CharField(source="assigned_agent.name", read_only=True)
    assigned_agent_phone = serializers.CharField(source="assigned_agent.phone", read_only=True)
    locked_by_name = serializers.CharField(source="locked_by.name", read_only=True)
    source_name = serializers.CharField(source="source_config.name", read_only=True)
    converted_customer_name = serializers.CharField(source="converted_customer.user.get_full_name", read_only=True)
    active_assignment = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            "id",
            "company",
            "created_by",
            "assigned_to",
            "source_config",
            "source_name",
            "assigned_agent",
            "assigned_agent_name",
            "assigned_agent_phone",
            "interested_property",
            "converted_customer",
            "converted_customer_name",
            "duplicate_of",
            "name",
            "mobile",
            "phone",
            "email",
            "source",
            "status",
            "stage",
            "interest_type",
            "deal_value",
            "property_type",
            "budget",
            "preferred_location",
            "geo_location",
            "score",
            "lead_score",
            "customer_type",
            "reliability_score",
            "no_show_count",
            "temperature",
            "country",
            "state",
            "district",
            "tehsil",
            "village",
            "city",
            "pincode_text",
            "pincode",
            "notes",
            "metadata",
            "is_duplicate",
            "duplicate_reason",
            "is_locked",
            "locked_by",
            "locked_by_name",
            "locked_at",
            "lock_reason",
            "distribution_level",
            "distribution_reason",
            "assigned_at",
            "agent_first_response_at",
            "last_reassigned_at",
            "converted_at",
            "next_followup_at",
            "last_followup_at",
            "followup_channel",
            "last_contacted_at",
            "stage_updated_at",
            "stage_deadline",
            "is_overdue",
            "active_assignment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "last_contacted_at"]

    def get_active_assignment(self, obj):
        assignment = getattr(obj, "assignments", None)
        if hasattr(assignment, "all"):
            assignment = assignment.filter(is_active=True).order_by("-created_at").first()
        else:
            assignment = None
        if not assignment:
            return None
        return LeadAssignmentSerializer(assignment, context=self.context).data


class BuilderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Builder
        fields = [
            "id",
            "name",
            "company_name",
            "registration_number",
            "contact",
            "contact_email",
            "website",
            "city",
            "verified",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class PropertyMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyMedia
        fields = ["id", "property", "media_type", "file", "external_url", "caption", "sort_order", "created_at"]
        read_only_fields = ["created_at"]


class PropertyLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyLocation
        fields = [
            "id",
            "property",
            "address",
            "city",
            "district",
            "state",
            "pin_code",
            "latitude",
            "longitude",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ["id", "property", "image", "image_url", "caption", "sort_order", "is_primary", "created_at"]
        read_only_fields = ["created_at"]


class PropertyVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyVideo
        fields = ["id", "property", "video", "video_url", "caption", "created_at"]
        read_only_fields = ["created_at"]


class PropertyFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyFeature
        fields = ["id", "property", "feature_name", "feature_value", "created_at"]
        read_only_fields = ["created_at"]


class PropertySerializer(serializers.ModelSerializer):
    builder_name = serializers.CharField(source="builder.name", read_only=True)
    assigned_agent_name = serializers.CharField(source="assigned_agent.name", read_only=True)
    media = PropertyMediaSerializer(many=True, read_only=True)
    location_detail = PropertyLocationSerializer(read_only=True)
    images = PropertyImageSerializer(many=True, read_only=True)
    videos = PropertyVideoSerializer(many=True, read_only=True)
    features = PropertyFeatureSerializer(many=True, read_only=True)
    wishlist_count = serializers.SerializerMethodField()
    is_wishlisted = serializers.SerializerMethodField()
    whatsapp_link = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            "id",
            "title",
            "price",
            "listing_type",
            "city",
            "location",
            "district",
            "state",
            "country",
            "tehsil",
            "village",
            "pin_code",
            "property_type",
            "area_sqft",
            "bedrooms",
            "bathrooms",
            "balcony",
            "parking",
            "furnishing",
            "description",
            "video_url",
            "video_file",
            "builder",
            "builder_name",
            "owner",
            "assigned_agent",
            "assigned_agent_name",
            "latitude",
            "longitude",
            "status",
            "aggregated_property",
            "data_source",
            "import_date",
            "source_reference",
            "metadata",
            "media",
            "location_detail",
            "images",
            "videos",
            "features",
            "wishlist_count",
            "is_wishlisted",
            "whatsapp_link",
            "approved_at",
            "updated_at",
            "created_at",
        ]
        read_only_fields = ["approved_at", "updated_at", "created_at"]

    def get_is_wishlisted(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return obj.wishlist_entries.filter(user=user).exists()

    def get_wishlist_count(self, obj):
        return obj.wishlist_entries.count()

    def get_whatsapp_link(self, obj):
        request = self.context.get("request")
        role = (getattr(getattr(request, "user", None), "role", "") or "").strip().lower()
        if role == "customer":
            phone = getattr(getattr(obj, "assigned_agent", None), "phone", "")
        else:
            phone = getattr(getattr(obj, "assigned_agent", None), "phone", "") or getattr(getattr(obj, "owner", None), "mobile", "")
        digits = "".join(ch for ch in phone if ch.isdigit())
        if not digits:
            return ""
        return f"https://wa.me/{digits}"


class PropertyProjectSerializer(serializers.ModelSerializer):
    builder_name = serializers.CharField(source="builder.name", read_only=True)

    class Meta:
        model = PropertyProject
        fields = [
            "id",
            "builder",
            "builder_name",
            "title",
            "location",
            "city",
            "price_range",
            "starting_price",
            "max_price",
            "property_types",
            "construction_status",
            "completion_date",
            "pre_launch",
            "launch_date",
            "pre_launch_price",
            "launch_price",
            "status",
            "leads",
            "roi_percent",
            "description",
            "approved",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class PropertyViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyView
        fields = ["id", "property", "user", "timestamp"]
        read_only_fields = ["timestamp"]


class PropertyWishlistSerializer(serializers.ModelSerializer):
    property_detail = PropertySerializer(source="property", read_only=True)

    class Meta:
        model = PropertyWishlist
        fields = ["id", "property", "property_detail", "user", "created_at"]
        read_only_fields = ["created_at"]


class FollowUpLeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUp
        fields = [
            "id",
            "lead",
            "message",
            "followup_date",
            "status",
            "channel",
            "attempts",
            "processed_at",
            "last_error",
            "created_at",
        ]
        read_only_fields = ["created_at", "status", "attempts", "processed_at", "last_error"]


class LeadDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadDocument
        fields = ["id", "lead", "doc_type", "title", "file", "uploaded_by", "created_at"]
        read_only_fields = ["uploaded_by", "created_at"]


class AgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agreement
        fields = ["id", "lead", "title", "pdf_file", "status", "created_at"]
        read_only_fields = ["created_at"]


class LeadImportBatchSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source="source.name", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = LeadImportBatch
        fields = [
            "id",
            "company",
            "source",
            "source_display",
            "created_by",
            "created_by_email",
            "import_type",
            "status",
            "file",
            "external_reference",
            "source_name",
            "total_rows",
            "processed_rows",
            "created_leads",
            "duplicate_rows",
            "failed_rows",
            "error_report",
            "payload",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "error_report"]


class LeadCaptureSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=160)
    phone = serializers.CharField(required=True, max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True)
    pincode = serializers.CharField(required=False, allow_blank=True, max_length=12)
    source = serializers.ChoiceField(choices=Lead.Source.choices, default=Lead.Source.API)
    source_key = serializers.CharField(required=False, allow_blank=True, max_length=120)
    metadata = serializers.JSONField(required=False)
    deal_value = serializers.DecimalField(required=False, max_digits=12, decimal_places=2)
    stage = serializers.ChoiceField(required=False, choices=Lead.Stage.choices, default=Lead.Stage.NEW)
    interest_type = serializers.ChoiceField(required=False, choices=Lead.InterestType.choices, default=Lead.InterestType.BUY)
    property_type = serializers.CharField(required=False, allow_blank=True, max_length=40)
    budget = serializers.DecimalField(required=False, max_digits=14, decimal_places=2)
    preferred_location = serializers.CharField(required=False, allow_blank=True, max_length=160)
    preferred_property_type = serializers.CharField(required=False, allow_blank=True, max_length=40)
    preferred_bedrooms = serializers.IntegerField(required=False, min_value=0)
    country = serializers.CharField(required=False, allow_blank=True, max_length=120)
    state = serializers.CharField(required=False, allow_blank=True, max_length=120)
    district = serializers.CharField(required=False, allow_blank=True, max_length=120)
    tehsil = serializers.CharField(required=False, allow_blank=True, max_length=120)
    village = serializers.CharField(required=False, allow_blank=True, max_length=120)
    city = serializers.CharField(required=False, allow_blank=True, max_length=120)
    notes = serializers.CharField(required=False, allow_blank=True)
    geo_location = serializers.JSONField(required=False)


class LeadBulkAssignSerializer(serializers.Serializer):
    lead_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)
    agent = serializers.IntegerField(required=False, min_value=1)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=200)
    auto = serializers.BooleanField(required=False, default=False)


class LeadContactSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=["whatsapp", "email", "sms", "call", "messenger", "instagram_dm"])
    message = serializers.CharField(required=False, allow_blank=True)
    subject = serializers.CharField(required=False, allow_blank=True, max_length=200)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class LeadConvertSerializer(serializers.Serializer):
    deal_amount = serializers.DecimalField(required=False, max_digits=14, decimal_places=2)
    commission_rate = serializers.DecimalField(required=False, max_digits=5, decimal_places=2)
    company_share_percent = serializers.DecimalField(required=False, max_digits=5, decimal_places=2)
    agent_share_percent = serializers.DecimalField(required=False, max_digits=5, decimal_places=2)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    customer_phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    customer_name = serializers.CharField(required=False, allow_blank=True, max_length=160)
    create_payment = serializers.BooleanField(required=False, default=True)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class LeadCSVImportSerializer(serializers.Serializer):
    file = serializers.FileField()
    source = serializers.CharField(required=False, allow_blank=True, max_length=120)
    source_key = serializers.CharField(required=False, allow_blank=True, max_length=120)
    mapping = serializers.JSONField(required=False)
    auto_assign = serializers.BooleanField(required=False, default=True)
    preview_only = serializers.BooleanField(required=False, default=False)


class LeadScrapeSerializer(serializers.Serializer):
    url = serializers.URLField(required=False, allow_blank=True)
    raw_html = serializers.CharField(required=False, allow_blank=True)
    source = serializers.CharField(required=False, allow_blank=True, max_length=120)
    source_key = serializers.CharField(required=False, allow_blank=True, max_length=120)
    auto_assign = serializers.BooleanField(required=False, default=True)
    max_items = serializers.IntegerField(required=False, min_value=1, max_value=100, default=25)
