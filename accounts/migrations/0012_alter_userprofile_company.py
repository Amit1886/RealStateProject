# Generated migration to alter UserProfile.company to ForeignKey

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core_settings", "0001_initial"),
        ("accounts", "0011_userprofile_company"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userprofile",
            name="company",
        ),
        migrations.AddField(
            model_name="userprofile",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="user_profiles",
                to="core_settings.companysettings",
            ),
        ),
    ]
