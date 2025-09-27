from django import forms
from .models import (
    Product, Warehouse, OrderItem, ChatMessage, Transaction,
    Category, Order, Party, Invoice
)

# ---------------- Party Form ----------------
class PartyForm(forms.ModelForm):
    class Meta:
        model = Party
        fields = ["name", "mobile", "email", "party_type", "gst", "address", "upi_id"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "mobile": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "party_type": forms.Select(attrs={"class": "form-control"}),
            "gst": forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "upi_id": forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional"}),
        }


# ---------------- Product Form ----------------
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name", "description", "price", "unit", "sku",
            "hsn_code", "gst_rate", "stock", "category"
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
        fields = ["name", "address"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


# ---------------- Order Form ----------------
class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["party", "status", "notes", "assigned_to"]
        widgets = {
            "party": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "assigned_to": forms.Select(attrs={"class": "form-control"}),
        }


# ---------------- Order Item Form ----------------
class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ["product", "qty", "price"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-control"}),
            "qty": forms.NumberInput(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control"}),
        }


# ---------------- Chat Message Form ----------------
class ChatMessageForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ["text", "attachment"]
        widgets = {
            "text": forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": "Type message..."}),
            "attachment": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

# ---------------- Transaction Form ----------------
class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["party", "txn_type", "amount", "notes"]
        widgets = {
            "party": forms.Select(attrs={"class": "form-control"}),
            "txn_type": forms.Select(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(attrs={"class": "form-control"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["party"].queryset = Party.objects.filter(owner=user)


# ---------------- Invoice Form ----------------
class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["order", "status"]
        widgets = {
            "order": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }
