from django.conf import settings
from django.db import models


class ScannerConfig(models.Model):
    class ScannerType(models.TextChoices):
        LASER = "laser", "Laser"
        CCD = "ccd", "CCD"
        QR_2D = "qr_2d", "2D QR"
        BLUETOOTH = "bluetooth", "Bluetooth"
        USB_HID = "usb_hid", "USB HID"
        CAMERA = "camera", "Camera"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scanner_configs")
    model_name = models.CharField(max_length=100)
    scanner_type = models.CharField(max_length=20, choices=ScannerType.choices)
    barcode_types_supported = models.JSONField(default=list, blank=True)
    scanning_delay_ms = models.PositiveIntegerField(default=100)
    auto_submit = models.BooleanField(default=True)
    sound_enabled = models.BooleanField(default=True)
    default_action_after_scan = models.CharField(max_length=50, default="add_item")
    camera_constraints = models.JSONField(default=dict, blank=True)
    is_default = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)


class ScanEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    scanner_config = models.ForeignKey(ScannerConfig, on_delete=models.SET_NULL, null=True, blank=True)
    raw_code = models.CharField(max_length=255)
    code_type = models.CharField(max_length=50, default="unknown")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["raw_code", "created_at"])]
