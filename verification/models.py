from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from saas_core.models import Company


class PropertyVerification(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="property_verifications",
    )
    property = models.ForeignKey(
        "leads.Property",
        on_delete=models.CASCADE,
        related_name="verifications",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="property_verification_requests",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="property_verifications_reviewed",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED, db_index=True)
    notes = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["property", "status"]),
            models.Index(fields=["requested_by", "status"]),
        ]

    def mark_reviewed(self, *, reviewer, status: str, notes: str = ""):
        self.reviewed_by = reviewer
        self.status = status
        self.reviewed_at = timezone.now()
        if notes:
            self.notes = notes
        self.save(update_fields=["reviewed_by", "status", "reviewed_at", "notes", "updated_at"])

    def __str__(self) -> str:
        return f"{self.property_id}:{self.status}"


class VerificationDocument(models.Model):
    class DocumentType(models.TextChoices):
        SALE_AGREEMENT = "sale_agreement", "Sale Agreement"
        PROPERTY_DOCUMENT = "property_document", "Property Document"
        IDENTITY = "identity", "Identity Verification"
        DEAL_CONTRACT = "deal_contract", "Deal Contract"
        OTHER = "other", "Other"

    verification = models.ForeignKey(
        PropertyVerification,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=30, choices=DocumentType.choices, default=DocumentType.OTHER, db_index=True)
    file = models.FileField(upload_to="verification_documents/", null=True, blank=True)
    external_url = models.URLField(blank=True, default="")
    title = models.CharField(max_length=160, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verification_documents_uploaded",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["verification", "document_type"]),
        ]

    def __str__(self) -> str:
        return self.title or f"{self.verification_id}:{self.document_type}"

