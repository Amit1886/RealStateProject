# full path: ~/myproject/khatapro/khataapp/forms.py
from django import forms
<<<<<<< HEAD
from django.contrib.auth import get_user_model
from .models import Party, Transaction, SupplierPayment, FieldAgent
=======
from .models import Party, Transaction, SupplierPayment
>>>>>>> fc1dc1ed70d9c9c0a937d50fa66837bc7585d738
from khataapp.models import UserProfile
from .models import ContactMessage
from commerce.models import Order


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


# ----------------- Supplier Payment Form -----------------
class SupplierPaymentForm(forms.ModelForm):
    class Meta:
        model = SupplierPayment
        fields = ['order', 'amount', 'payment_mode', 'reference', 'notes', 'payment_date']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # Filter orders to show only purchase orders for this user with outstanding amounts
            self.fields['order'].queryset = Order.objects.filter(
                owner=user,
                order_type='PURCHASE',
                due_amount__gt=0
            ).select_related('party')
<<<<<<< HEAD


# ----------------- Field Agent Form -----------------
class FieldAgentForm(forms.ModelForm):
    class Meta:
        model = FieldAgent
        fields = ["user", "role", "mobile", "assigned_parties", "is_active", "notes"]
        widgets = {
            "assigned_parties": forms.SelectMultiple(attrs={"size": 8}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)

        User = get_user_model()
        qs = User.objects.filter(is_active=True).exclude(is_superuser=True)
        if owner:
            qs = qs.exclude(id=owner.id)

        if self.instance and self.instance.pk:
            qs = qs | User.objects.filter(id=self.instance.user_id)

        self.fields["user"].queryset = qs.distinct()
=======
>>>>>>> fc1dc1ed70d9c9c0a937d50fa66837bc7585d738
