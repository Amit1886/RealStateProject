from uuid import uuid4


def create_razorpay_order_placeholder(amount):
    return {
        "provider": "razorpay",
        "order_id": f"rzp_{uuid4().hex[:16]}",
        "amount": amount,
        "status": "created",
        "note": "Placeholder integration. Replace with Razorpay SDK/API call.",
    }
