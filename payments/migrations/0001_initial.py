# Generated for compatibility with the lightweight payments app.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("wallet", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentOrder",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("reference_id", models.CharField(blank=True, db_index=True, default="", max_length=64, unique=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="INR", max_length=10)),
                (
                    "gateway",
                    models.CharField(
                        choices=[
                            ("razorpay", "Razorpay"),
                            ("phonepe", "PhonePe"),
                            ("stripe", "Stripe"),
                            ("dummy", "Dummy"),
                        ],
                        db_index=True,
                        default="dummy",
                        max_length=20,
                    ),
                ),
                (
                    "purpose",
                    models.CharField(
                        choices=[
                            ("wallet_topup", "Wallet Top-up"),
                            ("property_booking", "Property Booking"),
                            ("service_purchase", "Service Purchase"),
                            ("manual", "Manual"),
                        ],
                        db_index=True,
                        default="manual",
                        max_length=40,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("paid", "Paid"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "wallet",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="payment_orders",
                        to="wallet.wallet",
                    ),
                ),
            ],
            options={
                "db_table": "payments_paymentorder",
                "ordering": ["-created_at"],
            },
        ),
    ]
