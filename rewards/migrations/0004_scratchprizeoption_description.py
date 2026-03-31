from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rewards", "0003_scratchprizeoption"),
    ]

    operations = [
        migrations.AddField(
            model_name="scratchprizeoption",
            name="description",
            field=models.CharField(blank=True, default="", max_length=220),
        ),
    ]
