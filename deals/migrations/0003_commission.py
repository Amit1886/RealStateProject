from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ("saas_core", "0001_initial"),
        ("deals", "0002_deal_company"),
    ]

    operations = [
        migrations.CreateModel(
            name="Commission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("admin_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("agent_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("sub_agent_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("total_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("settled", models.BooleanField(default=False)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="commissions", to="saas_core.company")),
                ("deal", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="commission", to="deals.deal")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
