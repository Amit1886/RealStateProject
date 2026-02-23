from decimal import Decimal

from commission.models import CommissionPayout, CommissionRule


def calculate_margin_commission(order, salesman_user=None, delivery_user=None):
    margin = order.margin_amount
    rule = CommissionRule.objects.filter(is_default=True, is_active=True).first() or CommissionRule.objects.filter(is_active=True).first()

    if margin <= 0 or not rule:
        payout = CommissionPayout.objects.create(
            order=order,
            rule=rule,
            margin_amount=margin,
            salesman_amount=Decimal("0.00"),
            delivery_amount=Decimal("0.00"),
            company_profit=Decimal("0.00"),
        )
        return payout

    salesman_amount = (margin * rule.salesman_percent) / Decimal("100.00")
    delivery_amount = (margin * rule.delivery_percent) / Decimal("100.00")
    company_profit = margin - salesman_amount - delivery_amount

    payout = CommissionPayout.objects.create(
        order=order,
        rule=rule,
        margin_amount=margin,
        salesman_amount=salesman_amount,
        delivery_amount=delivery_amount,
        company_profit=company_profit,
    )
    return payout
