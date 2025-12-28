from django import forms
from django.forms import inlineformset_factory
from .models import (
    Product, Warehouse, OrderItem, ChatMessage,
     Order, Invoice
)

# ---------------- Product Form ----------------
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "price",
            "stock",
            "sku",
            "description",
            "unit",
            "hsn_code",
            "gst_rate",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "price": forms.NumberInput(attrs={"class": "form-control"}),
            "unit": forms.TextInput(attrs={"class": "form-control"}),
            "sku": forms.TextInput(attrs={"class": "form-control"}),
            "hsn_code": forms.TextInput(attrs={"class": "form-control"}),
            "gst_rate": forms.NumberInput(attrs={"class": "form-control"}),
            "stock": forms.NumberInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-control"}),
        }

# ---------------- Warehouse Form ----------------
class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'location', 'capacity']  # removed manager

# ---------------- Order Form ----------------
class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["party", "status", "notes", "assigned_to"]
        widgets = {
            "party": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "assigned_to": forms.Select(attrs={"class": "form-control"}),
        }


# ---------------- Order Item Form ----------------
class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ["product", "qty", "price"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-control product-select"}),
            "qty": forms.NumberInput(attrs={"class": "form-control qty-input", "min": "1"}),
            "price": forms.NumberInput(attrs={"class": "form-control price-input", "min": "0", "step": "0.01"}),
        }


# ✅ Define Inline Formset
OrderItemFormSet = inlineformset_factory(
    Order, OrderItem,
    form=OrderItemForm,
    extra=1,  # show at least one item by default
    can_delete=True
)

# ---------------- Chat Message Form ----------------
class ChatMessageForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ["text", "attachment"]
        widgets = {
            "text": forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": "Type message..."}),
            "attachment": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

# ---------------- Invoice Form ----------------
class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["order", "status"]
        widgets = {
            "order": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }
