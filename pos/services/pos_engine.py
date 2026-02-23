from uuid import uuid4

from pos.models import POSHoldBill


def hold_bill(session_id: int, payload: dict):
    code = f"HOLD-{uuid4().hex[:8].upper()}"
    return POSHoldBill.objects.create(session_id=session_id, hold_code=code, payload=payload)


def retrieve_hold_bill(hold_code: str):
    return POSHoldBill.objects.filter(hold_code=hold_code).first()
