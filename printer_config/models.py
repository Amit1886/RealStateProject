from django.conf import settings
from django.db import models


class PrinterConfig(models.Model):
    class PrinterType(models.TextChoices):
        THERMAL_58 = "thermal_58", "Thermal 58mm"
        THERMAL_80 = "thermal_80", "Thermal 80mm"
        A4 = "a4", "A4"

    class ConnectionType(models.TextChoices):
        USB = "usb", "USB"
        BLUETOOTH = "bluetooth", "Bluetooth"
        CUPS = "cups", "CUPS"
        NETWORK = "network", "Network"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="printer_configs")
    model_name = models.CharField(max_length=100)
    printer_type = models.CharField(max_length=20, choices=PrinterType.choices)
    connection_type = models.CharField(max_length=20, choices=ConnectionType.choices)
    auto_print = models.BooleanField(default=False)
    include_logo = models.BooleanField(default=True)
    include_qr = models.BooleanField(default=True)
    include_barcode = models.BooleanField(default=True)
    template_html = models.TextField(blank=True)
    connection_payload = models.JSONField(default=dict, blank=True)
    is_default = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)


class PrinterTestLog(models.Model):
    printer = models.ForeignKey(PrinterConfig, on_delete=models.CASCADE, related_name="tests")
    result = models.CharField(max_length=20, choices=(("success", "Success"), ("failed", "Failed")))
    message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PrintDocumentType(models.TextChoices):
    INVOICE = "invoice", "Invoice"
    CASH_MEMO = "cash_memo", "Cash Memo"
    RECEIPT = "receipt", "Receipt"
    VOUCHER = "voucher", "Voucher"
    ORDER_SLIP = "order_slip", "Order Slip"
    PURCHASE_BILL = "purchase_bill", "Purchase Bill"
    SALES_BILL = "sales_bill", "Sales Bill"
    TRANSPORT_RECEIPT = "transport_receipt", "Transport Receipt"
    DELIVERY_CHALLAN = "delivery_challan", "Delivery Challan"
    E_WAY_BILL = "e_way_bill", "E-Way Bill"
    RETURN_INVOICE = "return_invoice", "Return Invoice"
    PAYMENT_RECEIPT = "payment_receipt", "Payment Receipt"
    CREDIT_NOTE = "credit_note", "Credit Note"
    DEBIT_NOTE = "debit_note", "Debit Note"
    REPORT_LAYOUT = "report_layout", "Report Print Layout"


class PrintPaperSize(models.TextChoices):
    A4 = "a4", "A4"
    A5 = "a5", "A5"
    POS_58 = "pos_58", "POS 58mm"
    POS_80 = "pos_80", "POS 80mm"
    MOBILE = "mobile", "Mobile View"
    TABLET = "tablet", "Tablet View"
    DESKTOP = "desktop", "Desktop View"
    CUSTOM = "custom", "Custom"


class SizeUnit(models.TextChoices):
    PX = "px", "px"
    MM = "mm", "mm"
    CM = "cm", "cm"
    PERCENT = "%", "%"


class PrintMode(models.TextChoices):
    POS = "pos", "POS"
    MOBILE = "mobile", "Mobile"
    TABLET = "tablet", "Tablet"
    DESKTOP = "desktop", "Desktop"


class TextAlign(models.TextChoices):
    LEFT = "left", "Left"
    CENTER = "center", "Center"
    RIGHT = "right", "Right"


class ThemeMode(models.TextChoices):
    LIGHT = "light", "Light"
    DARK = "dark", "Dark"


class PrintTemplate(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    document_type = models.CharField(
        max_length=40,
        choices=PrintDocumentType.choices,
        db_index=True,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_admin_approved = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    restrict_basic_plan = models.BooleanField(default=False)
    admin_only = models.BooleanField(default=False)

    html_template = models.TextField()
    css_template = models.TextField(blank=True)
    json_config = models.JSONField(default=dict, blank=True)
    enabled_sections = models.JSONField(default=dict, blank=True)
    locked_advanced_fields = models.JSONField(default=list, blank=True)
    placeholder_whitelist = models.JSONField(default=list, blank=True)

    paper_size = models.CharField(max_length=20, choices=PrintPaperSize.choices, default=PrintPaperSize.A4)
    width_value = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    height_value = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    size_unit = models.CharField(max_length=5, choices=SizeUnit.choices, default=SizeUnit.MM)

    margin_top = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    margin_right = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    margin_bottom = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    margin_left = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    padding_value = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    border_value = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    font_family = models.CharField(max_length=120, default="Arial, sans-serif")
    font_size = models.PositiveIntegerField(default=12)
    text_align = models.CharField(max_length=10, choices=TextAlign.choices, default=TextAlign.LEFT)
    allow_dark_mode = models.BooleanField(default=True)
    thermal_layout = models.BooleanField(default=False)
    allow_custom_html = models.BooleanField(default=True)
    allow_custom_css = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_print_templates",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_print_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["document_type", "name"]
        indexes = [
            models.Index(fields=["document_type", "is_active"]),
            models.Index(fields=["is_default", "is_admin_approved"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_document_type_display()})"


class TemplatePlanAccess(models.Model):
    template = models.ForeignKey(PrintTemplate, on_delete=models.CASCADE, related_name="plan_access")
    plan = models.ForeignKey("billing.Plan", on_delete=models.CASCADE, related_name="print_template_access")
    is_enabled = models.BooleanField(default=True)
    is_default_for_plan = models.BooleanField(default=False)
    allow_advanced_fields = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("template", "plan")
        indexes = [models.Index(fields=["plan", "is_enabled"])]

    def __str__(self):
        return f"{self.plan.name} -> {self.template.name}"


class UserPrintTemplate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="print_templates")
    name = models.CharField(max_length=140)
    template = models.ForeignKey(
        PrintTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_templates",
    )
    document_type = models.CharField(max_length=40, choices=PrintDocumentType.choices, db_index=True)
    print_mode = models.CharField(max_length=20, choices=PrintMode.choices, default=PrintMode.DESKTOP)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    theme_mode = models.CharField(max_length=10, choices=ThemeMode.choices, default=ThemeMode.LIGHT)

    company_name = models.CharField(max_length=180, blank=True)
    company_address = models.TextField(blank=True)
    company_phone = models.CharField(max_length=30, blank=True)
    company_email = models.EmailField(blank=True)
    company_tax_id = models.CharField(max_length=50, blank=True)
    company_website = models.CharField(max_length=120, blank=True)
    header_text = models.CharField(max_length=255, blank=True)
    footer_text = models.CharField(max_length=255, blank=True)

    logo = models.ImageField(upload_to="print_assets/logos/", null=True, blank=True)
    signature_image = models.ImageField(upload_to="print_assets/signatures/", null=True, blank=True)
    stamp_image = models.ImageField(upload_to="print_assets/stamps/", null=True, blank=True)

    primary_color = models.CharField(max_length=20, default="#0f766e")
    secondary_color = models.CharField(max_length=20, default="#0f172a")
    accent_color = models.CharField(max_length=20, default="#e2e8f0")
    font_family = models.CharField(max_length=120, default="Arial, sans-serif")
    font_size = models.PositiveIntegerField(default=12)

    paper_size = models.CharField(max_length=20, choices=PrintPaperSize.choices, default=PrintPaperSize.A4)
    width_value = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    height_value = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    size_unit = models.CharField(max_length=5, choices=SizeUnit.choices, default=SizeUnit.MM)
    margin_top = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    margin_right = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    margin_bottom = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    margin_left = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    padding_value = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    border_value = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    section_visibility = models.JSONField(default=dict, blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)
    custom_css = models.TextField(blank=True)
    custom_html = models.TextField(blank=True)

    qr_enabled = models.BooleanField(default=True)
    barcode_enabled = models.BooleanField(default=True)
    thermal_mode = models.BooleanField(default=False)
    auto_print = models.BooleanField(default=False)
    show_digital_signature = models.BooleanField(default=False)
    show_stamp = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "document_type"]),
            models.Index(fields=["user", "print_mode"]),
            models.Index(fields=["is_default", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.name}"


class PrintRenderLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        QUEUED = "queued", "Queued"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="print_render_logs",
    )
    template = models.ForeignKey(
        PrintTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="render_logs",
    )
    user_template = models.ForeignKey(
        UserPrintTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="render_logs",
    )
    source_model = models.CharField(max_length=120, blank=True)
    source_id = models.CharField(max_length=120, blank=True)
    document_type = models.CharField(max_length=40, choices=PrintDocumentType.choices, db_index=True)
    print_mode = models.CharField(max_length=20, choices=PrintMode.choices, default=PrintMode.DESKTOP)
    paper_size = models.CharField(max_length=20, choices=PrintPaperSize.choices, default=PrintPaperSize.A4)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUCCESS)
    error_message = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    rendered_html = models.TextField(blank=True)
    rendered_css = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "document_type", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.document_type} - {self.status} - {self.created_at:%Y-%m-%d %H:%M}"
