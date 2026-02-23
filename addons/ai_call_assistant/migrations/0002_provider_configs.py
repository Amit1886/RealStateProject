from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("ai_call_assistant", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="WhatsAppProviderConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("branch_code", models.CharField(db_index=True, default="default", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "provider",
                    models.CharField(
                        choices=[("meta_cloud", "Meta WhatsApp Cloud"), ("twilio", "Twilio"), ("other", "Other")],
                        default="meta_cloud",
                        max_length=40,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("sandbox", models.BooleanField(default=True)),
                ("demo_sender", models.CharField(blank=True, max_length=40)),
                ("access_token", models.TextField(blank=True)),
                ("webhook_verify_token", models.CharField(blank=True, max_length=120)),
                ("extra", models.JSONField(blank=True, default=dict)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="whatsappproviderconfig_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="whatsappproviderconfig_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["branch_code", "provider"],
                "unique_together": {("branch_code", "provider")},
            },
        ),
        migrations.CreateModel(
            name="IVRProviderConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("branch_code", models.CharField(db_index=True, default="default", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "provider",
                    models.CharField(
                        choices=[("exotel", "Exotel"), ("twilio", "Twilio"), ("other", "Other")],
                        default="exotel",
                        max_length=40,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("sandbox", models.BooleanField(default=True)),
                ("demo_number", models.CharField(blank=True, max_length=40)),
                ("api_key", models.CharField(blank=True, max_length=200)),
                ("api_secret", models.CharField(blank=True, max_length=200)),
                ("extra", models.JSONField(blank=True, default=dict)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ivrproviderconfig_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ivrproviderconfig_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["branch_code", "provider"],
                "unique_together": {("branch_code", "provider")},
            },
        ),
    ]

