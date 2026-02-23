from django.db.models import Sum
from django.utils import timezone

from orders.models import Order
from products.models import Product


def ask_business_ai(question: str):
    q = question.lower().strip()
    today = timezone.localdate()

    if "today profit" in q:
        profit = Order.objects.filter(created_at__date=today).aggregate(v=Sum("margin_amount"))["v"] or 0
        return f"Today profit is {profit}."

    if "top salesman" in q:
        row = (
            Order.objects.filter(salesman__isnull=False)
            .values("salesman__id", "salesman__email")
            .annotate(v=Sum("total_amount"))
            .order_by("-v")
            .first()
        )
        if not row:
            return "No salesman data available."
        return f"Top salesman is {row['salesman__email']} with sales {row['v']}."

    if "slow products" in q:
        ids = (
            Order.objects.values("items__product")
            .annotate(v=Sum("items__qty"))
            .order_by("v")[:5]
        )
        product_ids = [x["items__product"] for x in ids if x["items__product"]]
        names = list(Product.objects.filter(id__in=product_ids).values_list("name", flat=True))
        return "Slow products: " + (", ".join(names) if names else "No data")

    return "LLM integration placeholder: connect your provider and map business prompts."
