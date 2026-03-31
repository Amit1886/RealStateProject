from __future__ import annotations

from django.conf import settings
from django.db import models


class GroupVisit(models.Model):
    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="group_visits")
    visit_date = models.DateTimeField(db_index=True)
    location = models.CharField(max_length=200)
    leads = models.ManyToManyField("leads.Lead", through="GroupVisitAttendance", related_name="group_visits", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="group_visits_created")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-visit_date", "-created_at"]
        indexes = [models.Index(fields=["agent", "visit_date"])]

    def __str__(self):
        return f"GroupVisit {self.id} @ {self.location}"


class GroupVisitAttendance(models.Model):
    class AttendanceStatus(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        PENDING = "pending", "Pending"

    group_visit = models.ForeignKey(GroupVisit, on_delete=models.CASCADE, related_name="attendance_rows")
    lead = models.ForeignKey("leads.Lead", on_delete=models.CASCADE, related_name="group_visit_attendance")
    attendance_status = models.CharField(max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.PENDING, db_index=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["group_visit__visit_date", "id"]
        unique_together = [("group_visit", "lead")]
        indexes = [models.Index(fields=["lead", "attendance_status"])]

    def __str__(self):
        return f"{self.group_visit_id}:{self.lead_id}:{self.attendance_status}"


class SiteVisit(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    lead = models.ForeignKey("leads.Lead", on_delete=models.CASCADE, related_name="site_visits")
    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="site_visits")
    group_visit = models.ForeignKey(GroupVisit, on_delete=models.SET_NULL, null=True, blank=True, related_name="site_visits")
    visit_date = models.DateTimeField()
    location = models.CharField(max_length=200)
    visit_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    visit_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    checkin_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    checkin_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    distance_mismatch = models.FloatField(default=0, help_text="KM difference between planned and check-in")
    is_group_visit = models.BooleanField(default=False, db_index=True)
    is_no_show = models.BooleanField(default=False, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED, db_index=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-visit_date"]
        indexes = [
            models.Index(fields=["agent", "status", "visit_date"]),
            models.Index(fields=["lead", "is_no_show"]),
        ]

    def __str__(self):
        return f"Visit {self.id} for Lead {self.lead_id}"

    def save(self, *args, **kwargs):
        self.is_group_visit = bool(self.group_visit_id)
        super().save(*args, **kwargs)
