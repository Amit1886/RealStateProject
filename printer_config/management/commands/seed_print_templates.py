from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from printer_config.models import PrintDocumentType, PrintPaperSize, PrintTemplate
from printer_config.services.sample_templates import BASE_TEMPLATE_CSS, default_template_html, sample_template_config


class Command(BaseCommand):
    help = "Seed default dynamic print templates for all supported document types."

    def handle(self, *args, **options):
        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).order_by("id").first()

        created = 0
        updated = 0
        for doc_type, label in PrintDocumentType.choices:
            name = f"{label} - Default"
            slug = slugify(f"{doc_type}-default")
            obj, was_created = PrintTemplate.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "document_type": doc_type,
                    "description": f"System default template for {label}",
                    "is_active": True,
                    "is_admin_approved": True,
                    "is_default": True,
                    "restrict_basic_plan": False,
                    "admin_only": False,
                    "paper_size": PrintPaperSize.A4,
                    "html_template": default_template_html(doc_type),
                    "css_template": BASE_TEMPLATE_CSS,
                    "json_config": sample_template_config(),
                    "enabled_sections": sample_template_config().get("sections", {}),
                    "created_by": admin_user,
                    "approved_by": admin_user,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
            self.stdout.write(f"[ok] {obj.slug}")

        self.stdout.write(
            self.style.SUCCESS(f"Template seeding done. created={created} updated={updated}")
        )
