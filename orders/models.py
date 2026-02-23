from decimal import Decimal

from django.conf import settings
from django.db import models

from warehouse.models import Warehouse


class Order(models.Model):
    class OrderType(models.TextChoices):
        ONLINE = "online", "Online"
        SALESMAN = "salesman", "Salesman"
        POS = "pos", "POS"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PACKED = "packed", "Packed"
        OUT_FOR_DELIVERY = "out_for_delivery", "Out for delivery"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    order_number = models.CharField(max_length=50, unique=True)
    order_type = models.CharField(max_length=20, choices=OrderType.choices, db_index=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="customer_orders")
    salesman = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="sales_orders")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, related_name="orders")
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING, db_index=True)

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    cost_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    margin_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    walk_in_customer_name = models.CharField(max_length=120, blank=True)
    is_hold = models.BooleanField(default=False)
    is_return = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["order_type", "status"]),
            models.Index(fields=["warehouse", "created_at"]),
        ]

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    qty = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    line_discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    margin_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        indexes = [models.Index(fields=["order", "product"])]


class POSBill(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="pos_bill")
    bill_number = models.CharField(max_length=40, unique=True)
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="pos_bills")
    terminal_id = models.CharField(max_length=50)
    payment_mode = models.CharField(max_length=20, choices=(("cash", "Cash"), ("upi", "UPI"), ("card", "Card"), ("wallet", "Wallet")))
    reprint_count = models.PositiveIntegerField(default=0)
    printed_at = models.DateTimeField(null=True, blank=True)


class OrderReturn(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="returns")
    reason = models.CharField(max_length=255)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
