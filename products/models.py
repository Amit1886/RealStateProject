from decimal import Decimal

from django.db import models

from warehouse.models import Warehouse


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="products")
    sku = models.CharField(max_length=64, unique=True)
    barcode = models.CharField(max_length=128, unique=True, db_index=True)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    mrp = models.DecimalField(max_digits=12, decimal_places=2)
    b2b_price = models.DecimalField(max_digits=12, decimal_places=2)
    b2c_price = models.DecimalField(max_digits=12, decimal_places=2)
    wholesale_price = models.DecimalField(max_digits=12, decimal_places=2)
    fast_moving = models.BooleanField(default=False)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["sku", "barcode"]), models.Index(fields=["fast_moving"])]

    def __str__(self):
        return self.name


class ProductPriceRule(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="dynamic_price_rules")
    channel = models.CharField(max_length=20, choices=(("b2b", "B2B"), ("b2c", "B2C"), ("pos", "POS"), ("quick", "Quick")))
    min_qty = models.PositiveIntegerField(default=1)
    max_qty = models.PositiveIntegerField(null=True, blank=True)
    override_price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["product", "channel", "is_active"])]


class WarehouseInventory(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="inventories")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="warehouse_inventories")
    available_qty = models.IntegerField(default=0)
    reserved_qty = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("warehouse", "product")
        indexes = [models.Index(fields=["warehouse", "available_qty"])]

    @property
    def sellable_qty(self):
        return self.available_qty - self.reserved_qty
