from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rewards", "0004_scratchprizeoption_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="scratchprizeoption",
            name="badge",
            field=models.CharField(blank=True, default="Demo preset", max_length=40),
        ),
    ]
