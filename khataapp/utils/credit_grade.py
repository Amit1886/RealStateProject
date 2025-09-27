# khataapp/utils/credit_grade.py
from django.db.models import Sum
from khataapp.models import Party, Transaction

def compute_grade_for_party(party: Party) -> str:
    """
    Ratio based grading:
      ratio = (total_debit / total_credit) * 100
      A+: >= 90, A: >=70, B: >=50, C: >=30, else D
    अगर दोनों 0 हैं -> D
    """
    totals = Transaction.objects.filter(party=party).values('txn_type').annotate(total=Sum('amount'))
    total_credit = 0
    total_debit = 0
    for row in totals:
        if row['txn_type'] == 'credit':
            total_credit = row['total'] or 0
        elif row['txn_type'] == 'debit':
            total_debit = row['total'] or 0

    if total_credit == 0 and total_debit == 0:
        return 'D'

    ratio = (float(total_debit) / float(total_credit) * 100.0) if total_credit > 0 else 0.0

    if ratio >= 90:
        return 'A+'
    elif ratio >= 70:
        return 'A'
    elif ratio >= 50:
        return 'B'
    elif ratio >= 30:
        return 'C'
    else:
        return 'D'