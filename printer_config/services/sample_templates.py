from __future__ import annotations

from printer_config.models import PrintDocumentType


BASE_TEMPLATE_CSS = """
@page {
  size: auto;
  margin: 0;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 0;
  font-family: var(--font-family, Arial, sans-serif);
  font-size: var(--font-size, 12px);
  color: #111827;
  background: #fff;
}
body.print-theme-dark {
  color: #e5e7eb;
  background: #0f172a;
}
.print-document {
  width: 100%;
}
.sheet {
  width: 100%;
  margin: 0 auto;
  border: var(--border-size, 0) solid #d1d5db;
  padding: var(--padding-size, 0);
}
.doc-header {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  margin-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 8px;
}
.doc-title {
  font-size: 18px;
  font-weight: 700;
}
.meta, .summary {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
}
.meta td, .summary td, .summary th {
  border: 1px solid #e5e7eb;
  padding: 6px 8px;
  vertical-align: top;
}
.summary th {
  text-align: left;
  background: #f8fafc;
}
.right {
  text-align: right;
}
.section-title {
  font-size: 13px;
  font-weight: 700;
  margin: 10px 0 6px 0;
}
.assets-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
}
.small {
  font-size: 11px;
  color: #64748b;
}
.page-break {
  page-break-before: always;
}
.items-wrap {
  page-break-inside: auto;
}
.items-wrap tr {
  page-break-inside: avoid;
}
"""


DEFAULT_TEMPLATE_HTML = """
<div class="sheet">
  {% if sections.header|default:True %}
  <div class="doc-header">
    <div>
      <div class="doc-title">{{ document.type|default:"Document"|upper }}</div>
      <div>{{ company.name|default:"Company Name" }}</div>
      <div class="small">{{ company.address }}</div>
      <div class="small">{{ company.phone }} {% if company.email %}| {{ company.email }}{% endif %}</div>
      {% if company.tax_id %}<div class="small">Tax/GST: {{ company.tax_id }}</div>{% endif %}
    </div>
    <div>
      {% if company.logo_url %}
      <img src="{{ company.logo_url }}" alt="logo" style="max-width:100px;max-height:60px;">
      {% endif %}
    </div>
  </div>
  {% endif %}

  <table class="meta">
    <tr>
      <td><strong>No:</strong> {{ document.number }}</td>
      <td><strong>Date:</strong> {{ document.date }}</td>
      <td><strong>Status:</strong> {{ document.status }}</td>
    </tr>
    <tr>
      <td colspan="2"><strong>Customer:</strong> {{ customer.name }}</td>
      <td><strong>Phone:</strong> {{ customer.phone }}</td>
    </tr>
  </table>

  {% if sections.items|default:True %}
  <div class="section-title">Items</div>
  <div class="items-wrap">
    <table class="summary">
      <thead>
        <tr>
          <th>#</th>
          <th>Item</th>
          <th>Qty</th>
          <th>Unit</th>
          <th class="right">Price</th>
          <th class="right">Amount</th>
        </tr>
      </thead>
      <tbody>
        {% for item in items %}
        <tr>
          <td>{{ forloop.counter }}</td>
          <td>{{ item.name }}</td>
          <td>{{ item.qty }}</td>
          <td>{{ item.unit }}</td>
          <td class="right">{{ item.price }}</td>
          <td class="right">{{ item.amount }}</td>
        </tr>
        {% empty %}
        <tr><td colspan="6" class="small">No items</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

  {% if sections.totals|default:True %}
  <div class="section-title">Totals</div>
  <table class="meta">
    <tr><td>Subtotal</td><td class="right">{{ totals.subtotal }}</td></tr>
    <tr><td>Discount</td><td class="right">{{ totals.discount }}</td></tr>
    <tr><td>Tax</td><td class="right">{{ totals.tax }}</td></tr>
    <tr><td><strong>Grand Total</strong></td><td class="right"><strong>{{ totals.grand_total }}</strong></td></tr>
    <tr><td>Paid</td><td class="right">{{ totals.paid }}</td></tr>
    <tr><td>Balance</td><td class="right">{{ totals.balance }}</td></tr>
  </table>
  {% endif %}

  {% if sections.assets|default:True %}
  <div class="assets-row">
    <div>
      {% if qr_image %}
      <img src="{{ qr_image }}" alt="qr" style="width:92px;height:92px;">
      {% endif %}
      {% if barcode_image %}
      <div><img src="{{ barcode_image }}" alt="barcode" style="max-width:220px;max-height:60px;"></div>
      {% endif %}
    </div>
    <div style="text-align:right;">
      {% if digital_signature_image %}
      <div><img src="{{ digital_signature_image }}" alt="signature" style="max-width:140px;max-height:70px;"></div>
      {% endif %}
      {% if stamp_image %}
      <div><img src="{{ stamp_image }}" alt="stamp" style="max-width:90px;max-height:90px;"></div>
      {% endif %}
    </div>
  </div>
  {% endif %}

  {% if sections.footer|default:True %}
  <div class="small" style="margin-top:12px;border-top:1px dashed #d1d5db;padding-top:8px;">
    {{ footer_text|default:company.name }}
  </div>
  {% endif %}
</div>
"""


def default_template_html(document_type: str) -> str:
    doc_type = (document_type or "").strip().lower()
    if doc_type in {
        PrintDocumentType.TRANSPORT_RECEIPT,
        PrintDocumentType.DELIVERY_CHALLAN,
        PrintDocumentType.E_WAY_BILL,
    }:
        return DEFAULT_TEMPLATE_HTML.replace("Items", "Consignment Items")
    if doc_type in {
        PrintDocumentType.CREDIT_NOTE,
        PrintDocumentType.DEBIT_NOTE,
    }:
        return DEFAULT_TEMPLATE_HTML.replace("Totals", "Adjustment Summary")
    if doc_type == PrintDocumentType.REPORT_LAYOUT:
        return DEFAULT_TEMPLATE_HTML.replace("Items", "Report Rows")
    return DEFAULT_TEMPLATE_HTML


def sample_template_config():
    return {
        "sections": {
            "header": True,
            "items": True,
            "totals": True,
            "assets": True,
            "footer": True,
        },
        "table": {
            "show_hsn": False,
            "show_barcode_column": False,
            "show_discount_column": True,
            "show_tax_column": True,
        },
        "branding": {
            "show_logo": True,
            "show_signature": True,
            "show_stamp": False,
        },
        "page_break": {
            "a4_multi_page": True,
            "rows_per_page": 20,
        },
    }
