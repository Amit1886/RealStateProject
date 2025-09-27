from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from decimal import Decimal
import uuid

# ✅ Import Party & Transaction from khataapp
from khataapp.models import Party, Transaction


# ---------------- Warehouses ----------------
class Warehouse(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="warehouses")
    name = models.CharField(max_length=120)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("owner", "name")

    def __str__(self):
        return f"{self.name} ({self.owner})"


# ---------------- Categories & Products ----------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(max_length=50, default="pcs")
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)
    hsn_code = models.CharField(max_length=20, blank=True, null=True)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    stock = models.IntegerField(default=0)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.sku})"


# ---------------- Inventory ----------------
class Inventory(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inventories")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="inventories")
    stock = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("owner", "product")

    def __str__(self):
        return f"{self.product.name} ({self.owner}) - {self.stock}"


class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stocks")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stocks")
    quantity = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "warehouse")

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"


# ---------------- Chat ----------------
class ChatThread(models.Model):
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name="chat_threads")
    message = models.TextField(default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat with {self.party.name}"


class ChatMessage(models.Model):
    SENDER_CHOICES = (("user", "User"), ("party", "Party"))
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name="messages")
    sent_by = models.CharField(max_length=10, choices=SENDER_CHOICES)
    text = models.TextField()
    attachment = models.FileField(upload_to="chat_files/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sent_by}: {self.text[:30]}"


# ---------------- Party Portal Token ----------------
class PartyPortal(models.Model):
    party = models.OneToOneField(Party, on_delete=models.CASCADE, related_name="portal")
    token = models.CharField(max_length=64, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def portal_url(self):
        return reverse("commerce:portal_home", kwargs={"token": self.token})

    def __str__(self):
        return f"Portal for {self.party}"


# ---------------- Orders ----------------
class Order(models.Model):
    STATUS = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
        ("fulfilled", "Fulfilled"),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
        null=True,   # ← yaha NULL allow kar diya
        blank=True   # ← yaha blank allow kar diya
    )
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name="orders")
    placed_by = models.CharField(max_length=10, choices=(("user", "User"), ("party", "Party")), default="party")
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_orders"
    )

    def total_amount(self):
        agg = self.items.aggregate(
            t=models.Sum(models.F("qty") * models.F("price"), output_field=models.DecimalField(max_digits=12, decimal_places=2))
        )
        return agg["t"] or Decimal("0.00")

    def __str__(self):
        return f"Order #{self.pk} by {self.party} [{self.status}]"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    qty = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    def line_total(self):
        return (self.price or Decimal("0")) * self.qty

    def __str__(self):
        return f"{self.product} x {self.qty}"

# ---------------- Invoice ----------------
class Invoice(models.Model):
    STATUS = (("unpaid", "Unpaid"), ("paid", "Paid"), ("cancelled", "Cancelled"))
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")
    number = models.CharField(max_length=32, unique=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS, default="unpaid")
    created_at = models.DateTimeField(auto_now_add=True)
    payment_link = models.URLField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = f"INV-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        if not self.amount:
            self.amount = self.order.total_amount()
        p = self.order.party
        if p.upi_id:
            self.payment_link = (
                f"upi://pay?pa={p.upi_id}&pn={p.name.replace(' ', '%20')}"
                f"&am={self.amount}&cu=INR&tn=Invoice%20{self.number}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.number} ({self.status})"


# ---------------- Payment ----------------
class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, default="upi")
    reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.invoice.number}: {self.amount} via {self.method}"


# ---------------- Notification ----------------
class Notification(models.Model):
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return self.message[:50]
