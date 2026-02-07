from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("core_settings", "0002_appsettings_featuresettings_modulesettings_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SettingCategory",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("label", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                ("icon", models.CharField(blank=True, max_length=50)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={
                "ordering": ["sort_order", "label"],
            },
        ),
        migrations.CreateModel(
            name="SettingDefinition",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(max_length=120, unique=True)),
                ("label", models.CharField(max_length=160)),
                ("help_text", models.CharField(blank=True, max_length=255)),
                ("data_type", models.CharField(choices=[("string", "String"), ("text", "Text"), ("number", "Number"), ("boolean", "Boolean"), ("select", "Select"), ("json", "JSON"), ("date", "Date")], default="string", max_length=20)),
                ("default_value", models.JSONField(blank=True, default=dict)),
                ("options", models.JSONField(blank=True, default=list)),
                ("scope", models.CharField(choices=[("global", "Global"), ("user", "User")], default="global", max_length=20)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="definitions", to="core_settings.settingcategory")),
            ],
            options={
                "ordering": ["sort_order", "label"],
            },
        ),
        migrations.CreateModel(
            name="SettingPermission",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("super_admin", "Super Admin"), ("admin", "Admin"), ("manager", "Manager"), ("user", "User")], max_length=20)),
                ("can_view", models.BooleanField(default=True)),
                ("can_edit", models.BooleanField(default=True)),
                ("hidden", models.BooleanField(default=False)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="permissions", to="core_settings.settingcategory")),
            ],
            options={
                "unique_together": {("role", "category")},
            },
        ),
        migrations.CreateModel(
            name="SettingValue",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("definition", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="values", to="core_settings.settingdefinition")),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="settings_values", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="settings_updates", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(condition=Q(("owner__isnull", False)), fields=("definition", "owner"), name="unique_setting_value_owner"),
                    models.UniqueConstraint(condition=Q(("owner__isnull", True)), fields=("definition",), name="unique_setting_value_global"),
                ],
            },
        ),
        migrations.CreateModel(
            name="SettingHistory",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("previous_value", models.JSONField(blank=True, default=dict)),
                ("new_value", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("definition", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="history", to="core_settings.settingdefinition")),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="settings_history", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="settings_history_updates", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
