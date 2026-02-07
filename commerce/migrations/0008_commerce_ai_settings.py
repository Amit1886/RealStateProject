from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("commerce", "0007_order_due_amount_order_invoice_number_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CommerceAISettings",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fast_daily_sales", models.DecimalField(decimal_places=2, default=1.5, max_digits=8)),
                ("medium_daily_sales", models.DecimalField(decimal_places=2, default=0.6, max_digits=8)),
                ("slow_daily_sales", models.DecimalField(decimal_places=2, default=0.2, max_digits=8)),
                ("safety_factor", models.DecimalField(decimal_places=2, default=0.7, max_digits=4)),
                ("default_budget", models.DecimalField(decimal_places=2, default=50000, max_digits=14)),
                ("default_target_days", models.PositiveIntegerField(default=30)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "AI Reorder Setting",
                "verbose_name_plural": "AI Reorder Settings",
            },
        ),
    ]
