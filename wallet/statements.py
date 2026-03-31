from __future__ import annotations

import csv
import zipfile
from io import BytesIO, StringIO
from xml.sax.saxutils import escape

from django.utils import timezone
try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None

from accounts.utils import render_to_pdf_bytes
from wallet.models import WalletTransaction
from wallet.services import get_or_create_wallet


def get_statement_queryset(user, *, start_date=None, end_date=None, entry_type="", source=""):
    wallet = get_or_create_wallet(user)
    queryset = wallet.transactions.select_related("wallet", "user", "counterparty_wallet").order_by("-created_at")
    if start_date:
        queryset = queryset.filter(created_at__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__date__lte=end_date)
    if entry_type:
        queryset = queryset.filter(entry_type=entry_type)
    if source:
        queryset = queryset.filter(source=source)
    return queryset


def build_statement_rows(queryset):
    rows = []
    for txn in queryset:
        rows.append(
            {
                "created_at": timezone.localtime(txn.created_at),
                "reference_id": str(txn.reference_id),
                "entry_type": txn.entry_type,
                "source": txn.source,
                "status": txn.status,
                "amount": txn.amount,
                "reference": txn.reference,
                "narration": txn.narration,
                "balance_after": txn.balance_after,
                "counterparty": getattr(getattr(txn.counterparty_wallet, "user", None), "email", "") or "",
            }
        )
    return rows


def render_statement_csv(rows):
    stream = StringIO()
    writer = csv.writer(stream)
    writer.writerow(["Date", "Reference ID", "Type", "Source", "Status", "Amount", "Reference", "Narration", "Counterparty", "Balance After"])
    for row in rows:
        writer.writerow(
            [
                row["created_at"].strftime("%Y-%m-%d %H:%M"),
                row["reference_id"],
                row["entry_type"],
                row["source"],
                row["status"],
                row["amount"],
                row["reference"],
                row["narration"],
                row["counterparty"],
                row["balance_after"],
            ]
        )
    return stream.getvalue()


def render_statement_xlsx(rows):
    if Workbook is None:
        return _render_minimal_xlsx(rows)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Wallet Statement"
    sheet.append(["Date", "Reference ID", "Type", "Source", "Status", "Amount", "Reference", "Narration", "Counterparty", "Balance After"])
    for row in rows:
        sheet.append(
            [
                row["created_at"].strftime("%Y-%m-%d %H:%M"),
                row["reference_id"],
                row["entry_type"],
                row["source"],
                row["status"],
                float(row["amount"]),
                row["reference"],
                row["narration"],
                row["counterparty"],
                float(row["balance_after"]),
            ]
        )
    content = BytesIO()
    workbook.save(content)
    return content.getvalue()


def _render_minimal_xlsx(rows):
    headers = ["Date", "Reference ID", "Type", "Source", "Status", "Amount", "Reference", "Narration", "Counterparty", "Balance After"]
    dataset = [headers]
    for row in rows:
        dataset.append(
            [
                row["created_at"].strftime("%Y-%m-%d %H:%M"),
                row["reference_id"],
                row["entry_type"],
                row["source"],
                row["status"],
                str(row["amount"]),
                row["reference"],
                row["narration"],
                row["counterparty"],
                str(row["balance_after"]),
            ]
        )

    def build_sheet_xml(data):
        lines = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
            "<sheetData>",
        ]
        for row_index, cells in enumerate(data, start=1):
            lines.append(f'<row r="{row_index}">')
            for col_index, value in enumerate(cells, start=1):
                cell_ref = _column_letter(col_index) + str(row_index)
                safe = escape("" if value is None else str(value))
                lines.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{safe}</t></is></c>')
            lines.append("</row>")
        lines.append("</sheetData></worksheet>")
        return "".join(lines)

    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            "</Relationships>",
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Wallet Statement" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        archive.writestr("xl/worksheets/sheet1.xml", build_sheet_xml(dataset))
        archive.writestr(
            "docProps/core.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            "<dc:title>Wallet Statement</dc:title><dc:creator>Codex</dc:creator></cp:coreProperties>",
        )
        archive.writestr(
            "docProps/app.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            "<Application>Codex</Application></Properties>",
        )
    return output.getvalue()


def _column_letter(index):
    result = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def render_statement_pdf(user, wallet, rows, *, start_date=None, end_date=None, request=None):
    context = {
        "wallet": wallet,
        "user": user,
        "rows": rows,
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": timezone.localtime(timezone.now()),
    }
    return render_to_pdf_bytes("wallet/statement_pdf.html", context, request=request)
