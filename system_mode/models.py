from django.conf import settings
from django.db import models, transaction


class SystemMode(models.Model):
    class Mode(models.TextChoices):
        POS = "POS", "POS Embedded"
        TABLET = "TABLET", "Tablet"
        MOBILE = "MOBILE", "Mobile"
        DESKTOP = "DESKTOP", "Desktop"
        ADMIN_SUPER = "ADMIN_SUPER", "Admin Super Control"
        AUTO = "AUTO", "Auto"

    current_mode = models.CharField(
        max_length=20,
        choices=Mode.choices,
        default=Mode.DESKTOP,
        db_index=True,
    )
    is_locked = models.BooleanField(default=False)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_mode_updates",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Mode"
        verbose_name_plural = "System Mode"

    def save(self, *args, **kwargs):
        # Hard singleton model.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls, for_update=False):
        qs = cls.objects
        if for_update:
            qs = qs.select_for_update()
        instance = qs.filter(pk=1).first()
        if instance:
            return instance

        with transaction.atomic():
            locked = cls.objects.select_for_update().filter(pk=1).first()
            if locked:
                return locked
            return cls.objects.create(pk=1, current_mode=cls.Mode.DESKTOP)

    def __str__(self):
        lock_state = "Locked" if self.is_locked else "Unlocked"
        return f"{self.current_mode} ({lock_state})"
