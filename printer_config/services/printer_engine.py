from django.template import Context, Template

from printer_config.models import PrinterTestLog
from printer_config.services.context_builder import build_document_context
from printer_config.services.template_renderer import render_template_payload

DEFAULT_TEMPLATES = {
    "pos_invoice": "<h3>POS Invoice</h3><p>Order: {{ order_number }}</p><p>Total: {{ total_amount }}</p>",
    "retail_invoice": "<h3>Retail Invoice</h3><p>Order: {{ order_number }}</p>",
    "wholesale_invoice": "<h3>Wholesale Invoice</h3><p>Order: {{ order_number }}</p>",
    "credit_invoice": "<h3>Credit Invoice</h3><p>Order: {{ order_number }}</p>",
    "return_bill": "<h3>Return Bill</h3><p>Order: {{ order_number }}</p>",
}


def render_invoice_template(printer, payload: dict):
    template_string = printer.template_html or DEFAULT_TEMPLATES.get(
        payload.get("invoice_type", "pos_invoice"),
        DEFAULT_TEMPLATES["pos_invoice"],
    )
    if payload.get("document_type"):
        context = build_document_context(
            document_type=payload.get("document_type"),
            source_model=payload.get("source_model", ""),
            source_id=payload.get("source_id"),
            payload=payload,
            user=printer.user,
        )
        rendered = render_template_payload(
            document_type=payload.get("document_type"),
            context=context,
            print_mode=payload.get("print_mode", "desktop"),
        )
        return rendered["html"]
    return Template(template_string).render(Context(payload))


def test_print(printer):
    PrinterTestLog.objects.create(printer=printer, result="success", message="Test print simulated")
    return "success"
