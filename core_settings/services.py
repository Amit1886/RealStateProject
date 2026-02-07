from django.contrib.auth.models import Group
from django.db import transaction, OperationalError
from django.core.cache import cache

from core_settings.models import (
    SettingCategory,
    SettingDefinition,
    SettingPermission,
    SettingValue,
    SettingHistory,
)


SETTINGS_REGISTRY = [
    {
        "slug": "user_account",
        "label": "User & Account",
        "icon": "user",
        "description": "Profile, login security, and personalization.",
        "settings": [
            {"key": "user_profile_edit", "label": "Profile editable", "data_type": "boolean", "default": True, "scope": "user"},
            {"key": "user_change_password", "label": "Password change", "data_type": "boolean", "default": True, "scope": "user"},
            {"key": "user_2fa_enabled", "label": "2FA / OTP", "data_type": "boolean", "default": False, "scope": "user"},
            {"key": "user_role_visibility", "label": "Role visibility", "data_type": "boolean", "default": True, "scope": "user"},
            {"key": "user_login_logs", "label": "Login security logs", "data_type": "boolean", "default": True, "scope": "user"},
            {"key": "user_session_control", "label": "Session control", "data_type": "boolean", "default": True, "scope": "user"},
            {"key": "user_theme", "label": "Theme", "data_type": "select", "default": "light", "options": ["light", "dark"], "scope": "user"},
            {"key": "user_language", "label": "Language", "data_type": "select", "default": "en", "options": ["en", "hi", "gu", "mr"], "scope": "user"},
        ],
    },
    {
        "slug": "company",
        "label": "Company",
        "icon": "building",
        "description": "Business identity, legal, and banking.",
        "settings": [
            {"key": "company_name", "label": "Company name", "data_type": "string", "default": "My Business"},
            {"key": "company_logo", "label": "Company logo URL", "data_type": "string", "default": ""},
            {"key": "company_gst", "label": "GST number", "data_type": "string", "default": ""},
            {"key": "company_cin", "label": "CIN", "data_type": "string", "default": ""},
            {"key": "company_address", "label": "Address", "data_type": "text", "default": ""},
            {"key": "company_contact", "label": "Contact info", "data_type": "text", "default": ""},
            {"key": "company_bank_details", "label": "Bank details", "data_type": "text", "default": ""},
            {"key": "company_digital_signature", "label": "Digital signature URL", "data_type": "string", "default": ""},
            {"key": "company_invoice_footer", "label": "Invoice footer notes", "data_type": "text", "default": ""},
            {"key": "company_terms", "label": "Terms & conditions", "data_type": "text", "default": ""},
            {"key": "company_currency", "label": "Default currency", "data_type": "select", "default": "INR", "options": ["INR", "USD", "EUR", "GBP"]},
            {"key": "company_timezone", "label": "Timezone", "data_type": "select", "default": "Asia/Kolkata", "options": ["Asia/Kolkata", "UTC", "America/New_York"]},
        ],
    },
    {
        "slug": "financial",
        "label": "Financial",
        "icon": "calculator",
        "description": "Fiscal year, ledgers, and currency rules.",
        "settings": [
            {"key": "financial_year", "label": "Financial year start", "data_type": "date", "default": ""},
            {"key": "opening_balances", "label": "Opening balances", "data_type": "json", "default": {}},
            {"key": "ledger_defaults", "label": "Ledger defaults", "data_type": "json", "default": {}},
            {"key": "account_groups", "label": "Account groups", "data_type": "json", "default": []},
            {"key": "chart_of_accounts", "label": "Chart of accounts", "data_type": "json", "default": []},
            {"key": "default_tax_mode", "label": "Default tax mode", "data_type": "select", "default": "exclusive", "options": ["inclusive", "exclusive"]},
            {"key": "rounding_rules", "label": "Rounding rules", "data_type": "select", "default": "nearest", "options": ["nearest", "up", "down"]},
            {"key": "multi_currency", "label": "Multi-currency enable", "data_type": "boolean", "default": False},
        ],
    },
    {
        "slug": "invoice_voucher",
        "label": "Invoice & Voucher",
        "icon": "file-text",
        "description": "Numbering, formats, and auto rules.",
        "settings": [
            {"key": "invoice_series", "label": "Invoice series generator", "data_type": "string", "default": "INV-2026-0001"},
            {"key": "voucher_numbering", "label": "Voucher numbering rules", "data_type": "string", "default": "VCH-YYYY-####"},
            {"key": "prefix_suffix", "label": "Prefix / suffix pattern", "data_type": "string", "default": ""},
            {"key": "auto_numbering", "label": "Auto numbering", "data_type": "boolean", "default": True},
            {"key": "credit_note_format", "label": "Credit/Debit note format", "data_type": "string", "default": "CN-YYYY-####"},
            {"key": "estimate_format", "label": "Estimate / Proforma format", "data_type": "string", "default": "EST-YYYY-####"},
            {"key": "auto_due_date_rule", "label": "Auto due date rules (days)", "data_type": "number", "default": 15},
        ],
    },
    {
        "slug": "item_inventory",
        "label": "Item & Inventory",
        "icon": "package",
        "description": "Products, categories, and stock rules.",
        "settings": [
            {"key": "item_code_format", "label": "Item code format", "data_type": "string", "default": "ITEM-####"},
            {"key": "barcode_rules", "label": "Barcode rules", "data_type": "string", "default": ""},
            {"key": "sku_generator", "label": "SKU generator", "data_type": "string", "default": "SKU-####"},
            {"key": "item_categories", "label": "Item categories", "data_type": "json", "default": []},
            {"key": "units_conversions", "label": "Units & conversions", "data_type": "json", "default": []},
            {"key": "low_stock_alert", "label": "Low stock alert (qty)", "data_type": "number", "default": 5},
            {"key": "batch_expiry", "label": "Batch & expiry", "data_type": "boolean", "default": False},
            {"key": "serial_tracking", "label": "Serial number tracking", "data_type": "boolean", "default": False},
        ],
    },
    {
        "slug": "printer_label",
        "label": "Printer & Label",
        "icon": "printer",
        "description": "Printer setup and label layouts.",
        "settings": [
            {"key": "invoice_printer", "label": "Invoice printer setup", "data_type": "string", "default": ""},
            {"key": "thermal_mode", "label": "Thermal printer mode", "data_type": "boolean", "default": False},
            {"key": "page_size", "label": "Page size", "data_type": "select", "default": "A4", "options": ["A4", "A5", "Letter", "Thermal-80mm"]},
            {"key": "print_templates", "label": "Print templates", "data_type": "json", "default": []},
            {"key": "label_printing", "label": "Label printing", "data_type": "boolean", "default": False},
            {"key": "barcode_label_layout", "label": "Barcode label layout", "data_type": "string", "default": ""},
            {"key": "qr_code_printing", "label": "QR code printing", "data_type": "boolean", "default": True},
            {"key": "bulk_label_print", "label": "Bulk label print", "data_type": "boolean", "default": False},
        ],
    },
    {
        "slug": "scanner_barcode",
        "label": "Scanner & Barcode",
        "icon": "scan",
        "description": "Scan mapping and fast scan behavior.",
        "settings": [
            {"key": "scanner_mapping", "label": "Barcode scanner mapping", "data_type": "json", "default": {}},
            {"key": "camera_scan", "label": "Camera scan mode", "data_type": "boolean", "default": False},
            {"key": "fast_scan", "label": "Fast scan toggle", "data_type": "boolean", "default": True},
            {"key": "auto_add_on_scan", "label": "Auto add on scan", "data_type": "boolean", "default": True},
            {"key": "scan_to_cart", "label": "Scan-to-cart behavior", "data_type": "select", "default": "add", "options": ["add", "replace", "confirm"]},
        ],
    },
    {
        "slug": "whatsapp_comm",
        "label": "WhatsApp & Communication",
        "icon": "message-circle",
        "description": "Messaging, reminders, and email/SMS.",
        "settings": [
            {"key": "whatsapp_api_config", "label": "WhatsApp API config", "data_type": "text", "default": ""},
            {"key": "order_via_whatsapp", "label": "Order via WhatsApp", "data_type": "boolean", "default": False},
            {"key": "invoice_share_auto", "label": "Invoice share automation", "data_type": "boolean", "default": False},
            {"key": "payment_link_auto", "label": "Payment link auto-send", "data_type": "boolean", "default": False},
            {"key": "reminder_templates", "label": "Reminder templates", "data_type": "json", "default": []},
            {"key": "chatbot_order_mode", "label": "Chatbot order mode", "data_type": "boolean", "default": False},
            {"key": "sms_gateway_config", "label": "SMS gateway config", "data_type": "text", "default": ""},
            {"key": "email_smtp_config", "label": "Email SMTP config", "data_type": "text", "default": ""},
        ],
    },
    {
        "slug": "social_integration",
        "label": "Social & Integration",
        "icon": "share-2",
        "description": "Links, API keys, and webhooks.",
        "settings": [
            {"key": "social_links", "label": "Social media links", "data_type": "json", "default": {}},
            {"key": "website_link", "label": "Website link", "data_type": "string", "default": ""},
            {"key": "google_login", "label": "Google login", "data_type": "boolean", "default": False},
            {"key": "api_keys_manager", "label": "API keys manager", "data_type": "json", "default": {}},
            {"key": "webhook_settings", "label": "Webhook settings", "data_type": "json", "default": {}},
            {"key": "third_party_integrations", "label": "Third-party integrations", "data_type": "json", "default": []},
        ],
    },
    {
        "slug": "tax_compliance",
        "label": "Tax & Compliance",
        "icon": "shield",
        "description": "GST, HSN/SAC, and filing reminders.",
        "settings": [
            {"key": "tax_categories", "label": "Tax categories", "data_type": "json", "default": []},
            {"key": "gst_slabs", "label": "GST slabs", "data_type": "json", "default": []},
            {"key": "hsn_sac_mapping", "label": "HSN/SAC mapping", "data_type": "json", "default": {}},
            {"key": "tax_inclusive_mode", "label": "Tax inclusive/exclusive", "data_type": "select", "default": "exclusive", "options": ["inclusive", "exclusive"]},
            {"key": "region_tax_rules", "label": "Region tax rules", "data_type": "json", "default": {}},
            {"key": "filing_reminders", "label": "Filing reminder alerts", "data_type": "boolean", "default": True},
        ],
    },
]


def get_user_role(user):
    if user.is_superuser:
        return "super_admin"
    if user.is_staff:
        return "admin"
    manager_group = Group.objects.filter(name__iexact="manager").first()
    if manager_group and manager_group in user.groups.all():
        return "manager"
    return "user"


def sync_settings_registry():
    registry_key = "core_settings_registry_v1"
    if cache.get(registry_key):
        return

    try:
        with transaction.atomic():
            for index, category_data in enumerate(SETTINGS_REGISTRY):
                category, _ = SettingCategory.objects.update_or_create(
                    slug=category_data["slug"],
                    defaults={
                        "label": category_data["label"],
                        "description": category_data.get("description", ""),
                        "icon": category_data.get("icon", ""),
                        "sort_order": index,
                    },
                )
                for setting_index, setting in enumerate(category_data.get("settings", [])):
                    SettingDefinition.objects.update_or_create(
                        key=setting["key"],
                        defaults={
                            "category": category,
                            "label": setting["label"],
                            "help_text": setting.get("help_text", ""),
                            "data_type": setting.get("data_type", "string"),
                            "default_value": setting.get("default", ""),
                            "options": setting.get("options", []),
                            "scope": setting.get("scope", "global"),
                            "sort_order": setting_index,
                        },
                    )
                for role in ["super_admin", "admin", "manager", "user"]:
                    SettingPermission.objects.get_or_create(
                        role=role,
                        category=category,
                        defaults={"can_view": True, "can_edit": True, "hidden": False},
                    )
        cache.set(registry_key, True, 3600)
    except OperationalError:
        # Avoid crashing the request if sqlite is locked; retry later.
        cache.set(registry_key, True, 30)
        return


def _get_value_for_definition(definition, owner):
    value_obj = SettingValue.objects.filter(definition=definition, owner=owner).first()
    if value_obj:
        return value_obj.value
    return definition.default_value


def get_settings_payload(user):
    sync_settings_registry()
    role = get_user_role(user)
    categories = []
    permissions = {p.category_id: p for p in SettingPermission.objects.filter(role=role)}

    for category in SettingCategory.objects.all():
        permission = permissions.get(category.id)
        if permission and permission.hidden:
            continue
        if permission and not permission.can_view:
            continue
        settings_payload = []
        for definition in category.definitions.all():
            owner = user if definition.scope == "user" else None
            settings_payload.append(
                {
                    "key": definition.key,
                    "label": definition.label,
                    "help_text": definition.help_text,
                    "data_type": definition.data_type,
                    "value": _get_value_for_definition(definition, owner),
                    "options": definition.options or [],
                    "scope": definition.scope,
                    "editable": bool(permission.can_edit) if permission else True,
                }
            )
        categories.append(
            {
                "slug": category.slug,
                "label": category.label,
                "description": category.description,
                "icon": category.icon,
                "settings": settings_payload,
                "editable": bool(permission.can_edit) if permission else True,
            }
        )

    return {"role": role, "categories": categories}


@transaction.atomic
def apply_updates(user, updates):
    sync_settings_registry()
    role = get_user_role(user)
    permissions = {p.category_id: p for p in SettingPermission.objects.filter(role=role)}
    results = []

    for update in updates:
        key = update.get("key")
        value = update.get("value")
        if not key:
            continue
        definition = SettingDefinition.objects.filter(key=key).select_related("category").first()
        if not definition:
            continue
        permission = permissions.get(definition.category_id)
        if permission and not permission.can_edit:
            results.append({"key": key, "status": "forbidden"})
            continue

        owner = user if definition.scope == "user" else None
        value_obj = SettingValue.objects.filter(definition=definition, owner=owner).first()
        previous = value_obj.value if value_obj else definition.default_value

        value_obj, _ = SettingValue.objects.update_or_create(
            definition=definition,
            owner=owner,
            defaults={"value": value, "updated_by": user},
        )

        SettingHistory.objects.create(
            definition=definition,
            owner=owner,
            previous_value=previous,
            new_value=value,
            updated_by=user,
        )

        results.append({"key": key, "status": "updated", "value": value})

    return results


@transaction.atomic
def undo_last_change(user, key):
    definition = SettingDefinition.objects.filter(key=key).first()
    if not definition:
        return None
    owner = user if definition.scope == "user" else None
    history = (
        SettingHistory.objects.filter(definition=definition, owner=owner)
        .order_by("-created_at")
        .first()
    )
    if not history:
        return None

    SettingValue.objects.update_or_create(
        definition=definition,
        owner=owner,
        defaults={"value": history.previous_value, "updated_by": user},
    )

    SettingHistory.objects.create(
        definition=definition,
        owner=owner,
        previous_value=history.new_value,
        new_value=history.previous_value,
        updated_by=user,
    )

    return history.previous_value


def build_ai_hints(payload):
    hints = []
    settings_by_key = {}
    for category in payload.get("categories", []):
        for setting in category.get("settings", []):
            settings_by_key[setting["key"]] = setting.get("value")

    if not settings_by_key.get("company_gst"):
        hints.append("GST number is missing. Add GST to avoid tax compliance issues.")
    if not settings_by_key.get("invoice_series"):
        hints.append("Invoice series is empty. Set a unique series to prevent duplicates.")
    if settings_by_key.get("multi_currency") and settings_by_key.get("company_currency") == "INR":
        hints.append("Multi-currency is enabled. Consider configuring additional currencies.")
    if settings_by_key.get("thermal_mode") and settings_by_key.get("page_size") not in ["Thermal-80mm"]:
        hints.append("Thermal mode is ON but page size is not thermal. Switch page size to Thermal-80mm.")
    if settings_by_key.get("tax_inclusive_mode") == "inclusive" and settings_by_key.get("default_tax_mode") == "exclusive":
        hints.append("Tax mode mismatch. Align default tax mode with inclusive setting.")

    if not hints:
        hints.append("All critical settings look healthy. You're ready to go.")

    return hints


def get_status_cards(payload):
    settings_by_key = {}
    for category in payload.get("categories", []):
        for setting in category.get("settings", []):
            settings_by_key[setting["key"]] = setting.get("value")

    company_ready = bool(settings_by_key.get("company_name")) and bool(settings_by_key.get("company_gst"))
    tax_ready = bool(settings_by_key.get("gst_slabs")) or bool(settings_by_key.get("tax_categories"))
    printer_ready = bool(settings_by_key.get("invoice_printer")) or bool(settings_by_key.get("page_size"))
    whatsapp_ready = bool(settings_by_key.get("whatsapp_api_config"))

    return {
        "company_config_status": "Configured" if company_ready else "Missing",
        "tax_setup_status": "Configured" if tax_ready else "Missing",
        "printer_ready_status": "Ready" if printer_ready else "Not Ready",
        "whatsapp_connected_status": "Connected" if whatsapp_ready else "Not Connected",
    }
