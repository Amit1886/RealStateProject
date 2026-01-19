"""
Fix OTP foreign key to point to accounts_user instead of auth_user
This is necessary because we have both auth_user and accounts_user tables,
but the OTP FK is incorrectly pointing to auth_user.
"""
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_userprofile_company"),
    ]

    operations = [
        migrations.AlterField(
            model_name="otp",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="otps",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
