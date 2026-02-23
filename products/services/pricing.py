from decimal import Decimal

from products.models import ProductPriceRule


def get_dynamic_price(product, channel: str, qty: int) -> Decimal:
    rule = (
        ProductPriceRule.objects.filter(product=product, channel=channel, is_active=True, min_qty__lte=qty)
        .order_by("-min_qty")
        .first()
    )
    if rule and (rule.max_qty is None or qty <= rule.max_qty):
        return rule.override_price
    if channel == "b2b":
        return product.b2b_price
    if channel == "b2c":
        return product.b2c_price
    if channel == "quick":
        return product.b2c_price
    return product.wholesale_price
