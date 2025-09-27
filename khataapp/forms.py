# full path: ~/myproject/khatapro/khataapp/forms.py
from django import forms
from .models import Party, Transaction
from .models import UserProfile, Plan

class PartyForm(forms.ModelForm):
    class Meta:
        model = Party
        fields = ['name', 'mobile', 'email', 'party_type']

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        # Remove 'date' since it's non-editable
        fields = ['party', 'txn_type', 'amount', 'date', 'notes']

class UserProfilePlanForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["plan"]   # सिर्फ Plan field editable होगी

class PlanChangeForm(forms.ModelForm):
    plan = forms.ModelChoiceField(
        queryset=Plan.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label=None
    )

    class Meta:
        model = UserProfile
        fields = ["plan"]
