from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlanPermissions',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('allow_dashboard', models.BooleanField(default=True)),
                ('allow_reports', models.BooleanField(default=True)),
                ('allow_pdf_export', models.BooleanField(default=False)),
                ('allow_excel_export', models.BooleanField(default=False)),
                ('allow_add_party', models.BooleanField(default=True)),
                ('allow_edit_party', models.BooleanField(default=True)),
                ('allow_delete_party', models.BooleanField(default=False)),
                ('max_parties', models.PositiveIntegerField(default=100)),
                ('allow_add_transaction', models.BooleanField(default=True)),
                ('allow_edit_transaction', models.BooleanField(default=True)),
                ('allow_delete_transaction', models.BooleanField(default=False)),
                ('allow_bulk_transaction', models.BooleanField(default=False)),
                ('allow_commerce', models.BooleanField(default=False)),
                ('allow_warehouse', models.BooleanField(default=False)),
                ('allow_orders', models.BooleanField(default=False)),
                ('allow_inventory', models.BooleanField(default=False)),
                ('allow_whatsapp', models.BooleanField(default=False)),
                ('allow_sms', models.BooleanField(default=False)),
                ('allow_email', models.BooleanField(default=False)),
                ('allow_settings', models.BooleanField(default=False)),
                ('allow_users', models.BooleanField(default=False)),
                ('allow_api_access', models.BooleanField(default=False)),
                ('allow_ledger', models.BooleanField(default=True)),
                ('allow_credit_report', models.BooleanField(default=False)),
                ('allow_analytics', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('plan', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='permissions', to='billing.plan')),
            ],
            options={
                'verbose_name': 'Plan Permission',
                'verbose_name_plural': 'Plan Permissions',
            },
        ),
    ]
