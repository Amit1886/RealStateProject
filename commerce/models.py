from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid
import random
import string
from khataapp.models import Party
from django.contrib.auth import get_user_model

User = get_user_model()


@property
def quantity(self):
    return self.qty


# ---------------- Warehouses ----------------
class Warehouse(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=255, blank=True, null=True)
    capacity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ---------------- Categories & Products ----------------
class Category(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.owner.email})"

class Product(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, related_name="products", null=True, blank=True
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=50, default="pcs")
    hsn_code = models.CharField(max_length=20, blank=True, null=True)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_products",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name

# ---------------- Inventory ----------------
class Inventory(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inventories"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="inventories")
    stock = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("owner", "product")

    def __str__(self):
        return f"{self.product.name} ({self.owner}) - {self.stock}"


# ---------------- Stock ----------------
class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stocks")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stocks")
    quantity = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "warehouse")

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"


# ---------------- Chat Models ----------------
class ChatThread(models.Model):
    party = models.ForeignKey(
        Party,
        on_delete=models.CASCADE,
        related_name="chat_threads"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat with {self.party.name}"

    @property
    def last_message(self):
        """Return latest message for quick access."""
        return self.messages.last()


class ChatMessage(models.Model):
    SENDER_CHOICES = (
        ("user", "User"),
        ("party", "Party"),
    )
    thread = models.ForeignKey(
        ChatThread,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sent_by = models.CharField(max_length=10, choices=SENDER_CHOICES)
    text = models.TextField(blank=True)
    attachment = models.FileField(upload_to="chat_files/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sent_by}: {self.text[:40] if self.text else '[File]'}"

# ---------------- Orders ----------------
# MULTI PRODUCT ORDER MODELS
class Order(models.Model):
    STATUS = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
        ("fulfilled", "Fulfilled"),
    )

    ORDER_TYPE = (
        ("SALE", "Sale"),
        ("PURCHASE", "Purchase"),
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="commerce_orders",
        null=True,
        blank=True,
    )

    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name="orders")

    placed_by = models.CharField(
        max_length=10,
        choices=(("user", "User"), ("party", "Party")),
        default="party",
    )

    status = models.CharField(max_length=12, choices=STATUS, default="pending")

    # ✅ New field for distinguishing Sale / Purchase
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE, default="SALE")

    # Purchase specific fields
    invoice_number = models.CharField(max_length=50, blank=True, null=True, help_text="Purchase invoice number")
    due_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Outstanding amount for purchase")
    payment_due_date = models.DateField(blank=True, null=True, help_text="Date when payment is due")

    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_orders",
    )

    def total_amount(self):
        """Sum all order item totals."""
        agg = self.items.aggregate(
            t=models.Sum(
                models.F("qty") * models.F("price"),
                output_field=models.DecimalField(max_digits=12, decimal_places=2),
            )
        )
        return agg["t"] or Decimal("0.00")

    def __str__(self):
        return f"Order #{self.pk} - {self.party.name if self.party else 'Unknown'} ({self.order_type} - {self.status})"


# ---------------- Order Item ----------------
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    qty = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def line_total(self):
        return self.qty * self.price

    def __str__(self):
        return f"{self.product.name if self.product else 'Unknown'} x {self.qty}"


# ---------------- Invoice ----------------
class Invoice(models.Model):
    STATUS = (("unpaid", "Unpaid"), ("paid", "Paid"), ("cancelled", "Cancelled"))
    GST_CHOICES = (
        ("GST", "GST"),
        ("NON_GST", "Non GST"),
    )

    gst_type = models.CharField(
        max_length=10,
        choices=GST_CHOICES,
        default="NON_GST"
    )

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")
    number = models.CharField(max_length=32, unique=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS, default="unpaid")
    created_at = models.DateTimeField(auto_now_add=True)
    payment_link = models.URLField(blank=True, null=True)

    def save(self, *args, **kwargs):
        """Auto-generate invoice number and payment link."""
        if not self.number:
            self.number = f"INV-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        # Auto-set amount from order if not given
        if not self.amount and hasattr(self, "order"):
            self.amount = self.order.total_amount()

        # Generate UPI payment link if Party has UPI ID
        party = getattr(self.order, "party", None)
        if party and party.upi_id:
            self.payment_link = (
                f"upi://pay?pa={party.upi_id}&pn={party.name.replace(' ', '%20')}"
                f"&am={self.amount}&cu=INR&tn=Invoice%20{self.number}"
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.number} ({self.status})"

# ---------------- Sales Voucher ----------------
class SalesVoucher(models.Model):
    invoice_no = models.AutoField(primary_key=True)

    order = models.ForeignKey(
        Order,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    party = models.ForeignKey('khataapp.Party', on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)

    is_gst = models.BooleanField(default=True)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)


class SalesVoucherItem(models.Model):
    voucher = models.ForeignKey(SalesVoucher, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('commerce.Product', on_delete=models.CASCADE)

    qty = models.DecimalField(max_digits=10, decimal_places=2)
    rate = models.DecimalField(max_digits=10, decimal_places=2)

    gst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        choices=[
            (0, '0%'),
            (5, '5%'),
            (12, '12%'),
            (18, '18%'),
            (28, '28%'),
        ],
        default=0
    )


# ---------------- Payment ----------------
class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=50, blank=True, null=True)
    reference = models.CharField(max_length=100, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.invoice.number}: ₹{self.amount} via {self.method or 'N/A'}"


# ---------------- Notification ----------------
class Notification(models.Model):
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return self.message[:50]


# ---------------- Coupons ----------------
class Coupon(models.Model):
    COUPON_TYPES = (
        ("discount", "Discount"),
        ("offer", "Offer"),
        ("spin_win", "Spin and Win"),
        ("scratch", "Scratch Card"),
    )

    DISCOUNT_TYPES = (
        ("percentage", "Percentage"),
        ("fixed", "Fixed Amount"),
    )

    title = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    coupon_type = models.CharField(max_length=20, choices=COUPON_TYPES, default="discount")

    # Discount specific fields
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, blank=True, null=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    # Usage limits
    usage_limit = models.PositiveIntegerField(default=1)  # Total usage limit
    per_user_limit = models.PositiveIntegerField(default=1)  # Per user limit
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Validity
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # For spin-win and scratch
    win_probability = models.DecimalField(max_digits=5, decimal_places=2, default=0.1)  # 10% chance

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.code})"

    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now and
            (self.valid_until is None or self.valid_until >= now)
        )

    def get_discount_amount(self, order_total):
        if self.coupon_type != "discount":
            return Decimal("0.00")

        if self.discount_type == "percentage":
            discount = (order_total * self.discount_value) / 100
            if self.max_discount and discount > self.max_discount:
                discount = self.max_discount
        else:  # fixed
            discount = self.discount_value

        return min(discount, order_total)  # Never exceed order total


class UserCoupon(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_coupons")
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="user_coupons")
    is_used = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "coupon")

    def __str__(self):
        return f"{self.user.username} - {self.coupon.code}"


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="usages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coupon_usages")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="coupon_usages", blank=True, null=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.coupon.code} used by {self.user.username} - ₹{self.discount_amount}"


# ---------------- Stock Entry ----------------
class StockEntry(models.Model):
    ENTRY_TYPE_CHOICES = [
        ("IN", "Stock In"),
        ("OUT", "Stock Out"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stockentry")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    entry_type = models.CharField(max_length=3, choices=ENTRY_TYPE_CHOICES)
    date = models.DateField()

    def __str__(self):
        return f"{self.product.name} - {self.entry_type} {self.quantity}"
