from __future__ import annotations

from printer_config.models import PrintDocumentType


PLACEHOLDER_CATALOG = [
    {"key": "company.name", "label": "Company Name", "group": "company"},
    {"key": "company.address", "label": "Company Address", "group": "company"},
    {"key": "company.phone", "label": "Company Phone", "group": "company"},
    {"key": "company.email", "label": "Company Email", "group": "company"},
    {"key": "company.tax_id", "label": "Company GST/TAX ID", "group": "company"},
    {"key": "company.website", "label": "Company Website", "group": "company"},
    {"key": "company.logo_url", "label": "Company Logo URL", "group": "company"},
    {"key": "document.number", "label": "Document Number", "group": "document"},
    {"key": "document.type", "label": "Document Type", "group": "document"},
    {"key": "document.date", "label": "Document Date", "group": "document"},
    {"key": "document.due_date", "label": "Due Date", "group": "document"},
    {"key": "document.status", "label": "Document Status", "group": "document"},
    {"key": "customer.name", "label": "Customer Name", "group": "party"},
    {"key": "customer.address", "label": "Customer Address", "group": "party"},
    {"key": "customer.phone", "label": "Customer Phone", "group": "party"},
    {"key": "customer.email", "label": "Customer Email", "group": "party"},
    {"key": "customer.tax_id", "label": "Customer GST/TAX ID", "group": "party"},
    {"key": "seller.name", "label": "Seller Name", "group": "party"},
    {"key": "seller.phone", "label": "Seller Phone", "group": "party"},
    {"key": "seller.email", "label": "Seller Email", "group": "party"},
    {"key": "transport.vehicle_no", "label": "Vehicle Number", "group": "transport"},
    {"key": "transport.driver_name", "label": "Driver Name", "group": "transport"},
    {"key": "transport.lr_no", "label": "LR Number", "group": "transport"},
    {"key": "transport.e_way_bill_no", "label": "E-Way Bill Number", "group": "transport"},
    {"key": "payment.mode", "label": "Payment Mode", "group": "payment"},
    {"key": "payment.reference", "label": "Payment Reference", "group": "payment"},
    {"key": "payment.status", "label": "Payment Status", "group": "payment"},
    {"key": "payment.paid_at", "label": "Payment Date", "group": "payment"},
    {"key": "totals.subtotal", "label": "Subtotal", "group": "totals"},
    {"key": "totals.discount", "label": "Discount", "group": "totals"},
    {"key": "totals.tax", "label": "Tax", "group": "totals"},
    {"key": "totals.shipping", "label": "Shipping", "group": "totals"},
    {"key": "totals.grand_total", "label": "Grand Total", "group": "totals"},
    {"key": "totals.paid", "label": "Paid Amount", "group": "totals"},
    {"key": "totals.balance", "label": "Balance Amount", "group": "totals"},
    {"key": "qr_value", "label": "QR Raw Value", "group": "assets"},
    {"key": "barcode_value", "label": "Barcode Raw Value", "group": "assets"},
    {"key": "qr_image", "label": "QR Image Data URI", "group": "assets"},
    {"key": "barcode_image", "label": "Barcode Image Data URI", "group": "assets"},
    {"key": "digital_signature_image", "label": "Digital Signature Image", "group": "assets"},
    {"key": "stamp_image", "label": "Stamp Image", "group": "assets"},
    {"key": "header_text", "label": "Header Text", "group": "layout"},
    {"key": "footer_text", "label": "Footer Text", "group": "layout"},
    {"key": "theme_mode", "label": "Theme Mode", "group": "layout"},
    {"key": "print_mode", "label": "Print Mode", "group": "layout"},
    {"key": "generated_at", "label": "Generated Timestamp", "group": "meta"},
    {"key": "custom", "label": "Custom fields object", "group": "meta"},
]


def get_placeholder_catalog(document_type: str | None = None):
    """Return placeholder metadata for editor UIs and API clients."""
    rows = [dict(row) for row in PLACEHOLDER_CATALOG]
    if not document_type:
        return rows

    normalized = (document_type or "").strip().lower()
    # All placeholders are valid globally; annotate relevance.
    for row in rows:
        row["document_type"] = normalized
        row["recommended"] = normalized in {
            PrintDocumentType.INVOICE,
            PrintDocumentType.CASH_MEMO,
            PrintDocumentType.RECEIPT,
            PrintDocumentType.VOUCHER,
            PrintDocumentType.ORDER_SLIP,
            PrintDocumentType.PURCHASE_BILL,
            PrintDocumentType.SALES_BILL,
            PrintDocumentType.PAYMENT_RECEIPT,
            PrintDocumentType.RETURN_INVOICE,
            PrintDocumentType.CREDIT_NOTE,
            PrintDocumentType.DEBIT_NOTE,
            PrintDocumentType.TRANSPORT_RECEIPT,
            PrintDocumentType.DELIVERY_CHALLAN,
            PrintDocumentType.E_WAY_BILL,
            PrintDocumentType.REPORT_LAYOUT,
        }
    return rows


def flatten_placeholder_keys():
    return [row["key"] for row in PLACEHOLDER_CATALOG]
