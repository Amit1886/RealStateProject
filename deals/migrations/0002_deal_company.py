from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("saas_core", "0001_initial"),
        ("deals", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="deal",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="deals",
                to="saas_core.company",
            ),
        ),
    ]
