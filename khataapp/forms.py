# full path: ~/myproject/khatapro/khataapp/forms.py
from django import forms
from .models import Party, Transaction
from khataapp.models import UserProfile
from .models import ContactMessage


# ----------------- Party Form -----------------
class PartyForm(forms.ModelForm):
    class Meta:
        model = Party
        fields = ['name', 'mobile', 'email', 'party_type']


# ----------------- Transaction Form -----------------
class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['party', 'txn_type', 'amount', 'notes']


# ----------------- User Profile (Dashboard) -----------------
class UserProfileDashboardForm(forms.ModelForm):
    class Meta:
        from accounts.models import UserProfile   # ✅ lazy import here
        model = UserProfile
        exclude = ["user"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and getattr(self.instance, "user", None):
            if "email" in self.fields:
                self.fields["email"].disabled = True
            if "mobile" in self.fields:
                self.fields["mobile"].disabled = True

# ----------------- User Profile Plan Change Form -----------------
def get_plan_model():
    """Lazy import of Plan model to avoid circular import"""
    from plans.models import Plan
    return Plan

class UserProfilePlanForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['plan']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Plan = get_plan_model()  # imported lazily
        self.fields['plan'].queryset = Plan.objects.all()

# ----------------- Contact Form -----------------
class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'mobile', 'message']