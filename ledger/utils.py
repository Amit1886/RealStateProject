# --- LEDGER FUNCTIONS HERE ----

def add_order_to_ledger(order):
    all_entries = []

    amount = order.total_amount()

    all_entries.append({
        "date": order.created_at.date(),
        "invoice_no": f"ORDER-{order.pk}",
        "description": f"Order placed by {order.party.name}",
        "amount": amount,        # Debit (+)
        "debit": amount,
        "credit": 0,
        "balance": 0,
    })

    return all_entries


def add_invoice_to_ledger(invoice):
    all_entries = []

    all_entries.append({
        "date": invoice.created_at.date(),
        "invoice_no": invoice.number,
        "description": f"Invoice generated for Order #{invoice.order.pk}",
        "amount": invoice.amount,
        "debit": invoice.amount,
        "credit": 0,
        "balance": 0,
    })

    return all_entries


def calculate_running_balance(entries):
    balance = 0
    final_entries = []

    for e in entries:
        amount = e["amount"]

        if amount > 0:
            e["debit"] = amount
            e["credit"] = 0
        else:
            e["debit"] = 0
            e["credit"] = abs(amount)

        balance += amount
        e["balance"] = balance

        final_entries.append(e)

    return final_entries
