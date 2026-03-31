from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class KYCProfile(models.Model):
    class Status(models.TextChoices):
        NOT_SUBMITTED = "not_submitted", "Not Submitted"
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kyc_profile")
    full_name = models.CharField(max_length=160, blank=True, default="")
    pan_number = models.CharField(max_length=10, blank=True, default="")
    aadhaar_number_masked = models.CharField(max_length=16, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_SUBMITTED, db_index=True)
    rejection_reason = models.CharField(max_length=255, blank=True, default="")
    verified_at = models.DateTimeField(null=True, blank=True)
    last_submitted_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kyc_verified_profiles",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]

    @property
    def pan_masked(self) -> str:
        if not self.pan_number:
            return ""
        if len(self.pan_number) < 4:
            return self.pan_number
        return f"{self.pan_number[:3]}XXXX{self.pan_number[-3:]}"

    def approve(self, reviewer=None):
        self.status = self.Status.VERIFIED
        self.verified_at = timezone.now()
        self.verified_by = reviewer
        self.rejection_reason = ""
        self.save(update_fields=["status", "verified_at", "verified_by", "rejection_reason", "updated_at"])
        self.documents.update(status=KYCDocument.Status.VERIFIED, reviewed_at=timezone.now())

    def reject(self, *, reviewer=None, reason: str = ""):
        self.status = self.Status.REJECTED
        self.verified_by = reviewer
        self.rejection_reason = reason[:255]
        self.save(update_fields=["status", "verified_by", "rejection_reason", "updated_at"])
        self.documents.update(status=KYCDocument.Status.REJECTED, review_note=self.rejection_reason, reviewed_at=timezone.now())

    def __str__(self) -> str:
        return f"KYC {self.user_id} [{self.status}]"


class KYCDocument(models.Model):
    class DocumentType(models.TextChoices):
        AADHAAR = "aadhaar", "Aadhaar"
        PAN = "pan", "PAN"
        PASSPORT = "passport", "Passport"
        DL = "driving_license", "Driving License"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    profile = models.ForeignKey(KYCProfile, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=40, choices=DocumentType.choices)
    document_file = models.FileField(upload_to="kyc/%Y/%m/")
    document_number_masked = models.CharField(max_length=32, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    extracted_data = models.JSONField(default=dict, blank=True)
    review_note = models.CharField(max_length=255, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.profile_id}:{self.document_type}:{self.status}"

