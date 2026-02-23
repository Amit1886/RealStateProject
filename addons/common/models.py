from django.conf import settings
from django.db import models


class BranchScopedModel(models.Model):
    """Optional branch partition key for SaaS and multi-branch rollouts."""

    branch_code = models.CharField(max_length=64, db_index=True, default="default")

    class Meta:
        abstract = True


class AuditStampedModel(models.Model):
    """Tracks creator/updater without touching legacy models."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True
