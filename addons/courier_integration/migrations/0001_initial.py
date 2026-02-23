from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CourierProviderConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("branch_code", models.CharField(db_index=True, default="default", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "provider",
                    models.CharField(
                        choices=[("shiprocket", "Shiprocket"), ("delhivery", "Delhivery"), ("dtdc", "DTDC")],
                        max_length=40,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("sandbox", models.BooleanField(default=True)),
                ("base_url", models.URLField(blank=True)),
                ("api_key", models.CharField(blank=True, max_length=255)),
                ("api_secret", models.CharField(blank=True, max_length=255)),
                ("extra", models.JSONField(blank=True, default=dict)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="courierproviderconfig_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="courierproviderconfig_updated",
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
            name="Shipment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("branch_code", models.CharField(db_index=True, default="default", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "provider",
                    models.CharField(
                        choices=[("shiprocket", "Shiprocket"), ("delhivery", "Delhivery"), ("dtdc", "DTDC")],
                        default="shiprocket",
                        max_length=40,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("booked", "Booked"),
                            ("in_transit", "In Transit"),
                            ("delivered", "Delivered"),
                            ("rto", "RTO"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="created",
                        max_length=20,
                    ),
                ),
                ("ref_type", models.CharField(db_index=True, default="storefront_order", max_length=40)),
                ("ref", models.CharField(db_index=True, max_length=80)),
                ("awb", models.CharField(blank=True, max_length=80)),
                ("tracking_number", models.CharField(blank=True, max_length=120)),
                ("tracking_url", models.URLField(blank=True)),
                ("meta", models.JSONField(blank=True, default=dict)),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="shipment_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="shipment_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["provider", "status"], name="ship_provider_status_idx")],
            },
        ),
        migrations.CreateModel(
            name="ShipmentEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(max_length=80)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "shipment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="courier_integration.shipment",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
