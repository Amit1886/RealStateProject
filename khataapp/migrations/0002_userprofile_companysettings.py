from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_initial"),
        ("khataapp", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanySettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company_name", models.CharField(blank=True, default="", max_length=255)),
                ("auto_sms_send", models.BooleanField(default=False)),
                (
                    "default_plan",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="billing.plan",
                    ),
                ),
                (
                    "owner",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="company_settings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(blank=True, default="", max_length=255)),
                ("mobile", models.CharField(blank=True, default="", max_length=20)),
                ("created_from", models.CharField(blank=True, default="", max_length=50)),
                ("business_name", models.CharField(blank=True, default="", max_length=255)),
                ("business_type", models.CharField(blank=True, default="", max_length=100)),
                ("address", models.CharField(blank=True, default="", max_length=255)),
                ("gst_number", models.CharField(blank=True, default="", max_length=50)),
                ("profile_picture", models.ImageField(blank=True, null=True, upload_to="profiles/")),
                ("bank_name", models.CharField(blank=True, default="", max_length=120)),
                ("account_number", models.CharField(blank=True, default="", max_length=50)),
                ("ifsc_code", models.CharField(blank=True, default="", max_length=20)),
                ("upi_id", models.CharField(blank=True, default="", max_length=120)),
                ("qr_code", models.ImageField(blank=True, null=True, upload_to="profiles/qr/")),
                (
                    "plan",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="khata_profiles",
                        to="billing.plan",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="khata_stub_profile", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
    ]
