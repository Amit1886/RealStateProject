from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rewards", "0002_rewardrule_spinrewardoption_rewardcoin_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScratchPrizeOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=120)),
                (
                    "reward_type",
                    models.CharField(
                        choices=[
                            ("coins", "Coins"),
                            ("cashback", "Cashback"),
                            ("bonus", "Bonus"),
                        ],
                        default="coins",
                        max_length=20,
                    ),
                ),
                ("coin_amount", models.PositiveIntegerField(default=0)),
                ("wallet_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("weight", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["label", "id"],
            },
        ),
    ]
