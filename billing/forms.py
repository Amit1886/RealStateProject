# full path: ~/myproject/khatapro/billing/forms.py
from django import forms
from .models import Plan

class SubscriptionForm(forms.Form):
    plan = forms.ModelChoiceField(queryset=Plan.objects.all(), widget=forms.RadioSelect)
