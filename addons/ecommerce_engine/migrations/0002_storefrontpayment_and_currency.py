from __future__ import annotations

import decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("ecommerce_engine", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="storefrontorder",
            name="currency",
            field=models.CharField(default="INR", max_length=10),
        ),
        migrations.CreateModel(
            name="StorefrontPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("branch_code", models.CharField(db_index=True, default="default", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("gateway", models.CharField(default="razorpay", max_length=30)),
                ("payment_ref", models.CharField(max_length=120)),
                ("amount", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=12)),
                ("currency", models.CharField(default="INR", max_length=10)),
                (
                    "status",
                    models.CharField(
                        choices=[("initiated", "Initiated"), ("captured", "Captured"), ("failed", "Failed")],
                        db_index=True,
                        default="initiated",
                        max_length=20,
                    ),
                ),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="storefrontpayment_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="storefrontpayment_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to="ecommerce_engine.storefrontorder",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="storefrontpayment",
            index=models.Index(fields=["gateway", "payment_ref"], name="addons_ecom_gateway__d1db50_idx"),
        ),
    ]

