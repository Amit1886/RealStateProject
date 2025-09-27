# khataapp/utils/credit_report.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from khataapp.models import Party, Transaction
from io import BytesIO


def generate_credit_report_pdf():
    """
    Generate a grade-wise PDF report of all parties.
    Returns a BytesIO buffer.
    """
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(150, height - 50, "Credit Report (Grade-wise)")

    y = height - 80
    pdf.setFont("Helvetica-Bold", 12)

    grades = ['A+', 'A', 'B', 'C', 'D', '-']
    for grade in grades:
        parties = Party.objects.filter(credit_grade=grade)
        if not parties.exists():
            continue

        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(50, y, f"Grade: {grade}")
        y -= 20
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(60, y, "Name | Type | Credit | Debit | Balance")
        y -= 15

        pdf.setFont("Helvetica", 10)
        for party in parties:
            total_credit = party.total_credit()
            total_debit = party.total_debit()
            balance = total_credit - total_debit
            line = f"{party.name} | {party.party_type} | ₹{total_credit} | ₹{total_debit} | ₹{balance}"
            pdf.drawString(60, y, line)
            y -= 15

            if y < 50:  # page break
                pdf.showPage()
                y = height - 50
                pdf.setFont("Helvetica-Bold", 12)

        y -= 20
        pdf.setFont("Helvetica-Bold", 12)

    pdf.save()
    buffer.seek(0)
    return buffer


def generate_credit_report_pdf_for_party(party: Party):
    """
    Generate PDF report for a single party.
    Returns a BytesIO buffer.
    """
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(150, height - 50, f"Credit Report: {party.name}")

    y = height - 80
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, f"Name: {party.name}")
    y -= 20
    pdf.drawString(50, y, f"Type: {party.party_type}")
    y -= 20
    pdf.drawString(50, y, f"Credit Grade: {party.credit_grade}")
    y -= 30

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Transactions:")
    y -= 20
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(60, y, "Date | Type | Amount | Notes")
    y -= 15

    pdf.setFont("Helvetica", 10)
    transactions = Transaction.objects.filter(party=party).order_by('-date')
    for txn in transactions:
        line = f"{txn.date} | {txn.txn_type} | ₹{txn.amount} | {txn.notes or '-'}"
        pdf.drawString(60, y, line)
        y -= 15
        if y < 50:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(50, y, "Transactions:")
            y -= 20
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(60, y, "Date | Type | Amount | Notes")
            y -= 15
            pdf.setFont("Helvetica", 10)

    total_credit = party.total_credit()
    total_debit = party.total_debit()
    balance = total_credit - total_debit

    y -= 20
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, f"Total Credit: ₹{total_credit}")
    y -= 20
    pdf.drawString(50, y, f"Total Debit: ₹{total_debit}")
    y -= 20
    pdf.drawString(50, y, f"Balance: ₹{balance}")

    pdf.save()
    buffer.seek(0)
    return buffer