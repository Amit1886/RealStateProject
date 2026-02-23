from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SocialAccountConnection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("branch_code", models.CharField(db_index=True, default="default", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "platform",
                    models.CharField(
                        choices=[
                            ("facebook", "Facebook"),
                            ("instagram", "Instagram"),
                            ("youtube", "YouTube"),
                            ("linkedin", "LinkedIn"),
                            ("x", "X"),
                        ],
                        max_length=20,
                    ),
                ),
                ("account_handle", models.CharField(max_length=120)),
                ("access_token", models.TextField(blank=True)),
                ("refresh_token", models.TextField(blank=True)),
                ("token_expires_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="socialaccountconnection_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="socialaccountconnection_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"unique_together": {("platform", "account_handle", "branch_code")}},
        ),
        migrations.CreateModel(
            name="ContentSchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("branch_code", models.CharField(db_index=True, default="default", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "platform",
                    models.CharField(
                        choices=[
                            ("facebook", "Facebook"),
                            ("instagram", "Instagram"),
                            ("youtube", "YouTube"),
                            ("linkedin", "LinkedIn"),
                            ("x", "X"),
                        ],
                        max_length=20,
                    ),
                ),
                ("title", models.CharField(max_length=160)),
                ("caption", models.TextField(blank=True)),
                ("hashtags", models.CharField(blank=True, max_length=500)),
                ("media_url", models.URLField(blank=True)),
                ("scheduled_for", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("scheduled", "Scheduled"),
                            ("published", "Published"),
                            ("failed", "Failed"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("post_response", models.JSONField(blank=True, default=dict)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="contentschedule_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="contentschedule_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-scheduled_for"]},
        ),
        migrations.CreateModel(
            name="AutoReplyRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("branch_code", models.CharField(db_index=True, default="default", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "platform",
                    models.CharField(
                        choices=[
                            ("facebook", "Facebook"),
                            ("instagram", "Instagram"),
                            ("youtube", "YouTube"),
                            ("linkedin", "LinkedIn"),
                            ("x", "X"),
                        ],
                        max_length=20,
                    ),
                ),
                ("trigger_keyword", models.CharField(max_length=120)),
                ("response_text", models.TextField()),
                ("is_active", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="autoreplyrule_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="autoreplyrule_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CreativeAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("branch_code", models.CharField(db_index=True, default="default", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("banner", "Banner"),
                            ("poster", "Poster"),
                            ("reel_script", "Reel Script"),
                            ("video_edit", "Video Edit"),
                        ],
                        max_length=20,
                    ),
                ),
                ("prompt", models.TextField()),
                ("output_url", models.URLField(blank=True)),
                ("status", models.CharField(default="queued", max_length=20)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="creativeasset_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="creativeasset_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]

