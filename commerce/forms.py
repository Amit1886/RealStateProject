from django import forms
from django.forms import inlineformset_factory
from .models import (
    Product,
    Warehouse,
    Order,
    OrderItem,
    Invoice,
    Coupon,
    Payment,
    ChatMessage,
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

# ---------------- Coupon Form ----------------
class CouponForm(forms.ModelForm):
    valid_until = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"})
    )

    class Meta:
        model = Coupon
        fields = [
            "title", "code", "description", "coupon_type",
            "discount_type", "discount_value", "max_discount",
            "usage_limit", "per_user_limit", "min_order_amount",
            "valid_from", "valid_until", "is_active", "win_probability"
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "coupon_type": forms.Select(attrs={"class": "form-control"}),
            "discount_type": forms.Select(attrs={"class": "form-control"}),
            "discount_value": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "max_discount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "usage_limit": forms.NumberInput(attrs={"class": "form-control"}),
            "per_user_limit": forms.NumberInput(attrs={"class": "form-control"}),
            "min_order_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "valid_from": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "win_probability": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "1"}),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = code.upper()
        return code

# ---------------- Payment Form ----------------
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["invoice", "amount", "method", "reference", "note"]
        widgets = {
            "invoice": forms.Select(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "method": forms.Select(attrs={"class": "form-control"}),
            "reference": forms.TextInput(attrs={"class": "form-control"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }