from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import django.utils.timezone
from decimal import Decimal


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Party",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("mobile", models.CharField(blank=True, default="", max_length=20)),
                ("whatsapp_number", models.CharField(blank=True, default="", max_length=20)),
                ("party_type", models.CharField(blank=True, default="", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="khata_parties",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CreditAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("balance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="credit_accounts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="FieldAgent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("phone", models.CharField(blank=True, default="", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="field_agents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Transaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "txn_type",
                    models.CharField(
                        choices=[("credit", "Credit"), ("debit", "Debit")], max_length=10
                    ),
                ),
                ("txn_mode", models.CharField(blank=True, default="", max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("date", models.DateField(default=django.utils.timezone.now)),
                ("notes", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="khata_transactions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "party",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="transactions",
                        to="khataapp.party",
                    ),
                ),
            ],
        ),
    ]

