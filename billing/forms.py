# full path: ~/myproject/khatapro/billing/forms.py
from django import forms
from .models import Plan
from .models import Commerce

class SubscriptionForm(forms.Form):
    plan = forms.ModelChoiceField(queryset=Plan.objects.all(), widget=forms.RadioSelect)


class CommerceForm(forms.ModelForm):
    class Meta:
        model = Commerce
        fields = [
            "business_name",
            "category",
            "gst_number",
            "contact_number",
            "address",
        ]
        widgets = {
            "business_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Business Name"}),
            "category": forms.TextInput(attrs={"class": "form-control", "placeholder": "Category"}),
            "gst_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "GST Number"}),
            "contact_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Contact Number"}),
            "address": forms.Textarea(attrs={"class": "form-control", "placeholder": "Business Address", "rows": 3}),
        }