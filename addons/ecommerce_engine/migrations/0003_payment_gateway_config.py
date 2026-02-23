from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("ecommerce_engine", "0002_storefrontpayment_and_currency"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentGatewayConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("branch_code", models.CharField(db_index=True, default="default", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "provider",
                    models.CharField(
                        choices=[("razorpay", "Razorpay"), ("stripe", "Stripe"), ("other", "Other")],
                        default="razorpay",
                        max_length=40,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("sandbox", models.BooleanField(default=True)),
                ("key_id", models.CharField(blank=True, max_length=200)),
                ("key_secret", models.CharField(blank=True, max_length=200)),
                ("webhook_secret", models.CharField(blank=True, max_length=200)),
                ("extra", models.JSONField(blank=True, default=dict)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="paymentgatewayconfig_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="paymentgatewayconfig_updated",
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

