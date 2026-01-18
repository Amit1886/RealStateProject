# accounts/forms.py
from django import forms
from django.contrib.auth import get_user_model
from khataapp.models import UserProfile

User = get_user_model()


# ----------------- SIGNUP FORM -----------------
class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    mobile = forms.CharField(max_length=15, required=True, label="Mobile Number")

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username


# ----------------- LOGIN FORM -----------------
class LoginForm(forms.Form):
    identifier = forms.CharField(
        max_length=150,
        help_text="Email ya mobile",
        label="Email or Mobile"
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Password"
    )
    use_otp = forms.BooleanField(
        required=False,
        initial=True,
        label="Login via OTP"
    )

    def clean(self):
        cleaned = super().clean()
        identifier = cleaned.get("identifier")
        if not identifier:
            raise forms.ValidationError("Please enter Email or Mobile.")
        return cleaned


# ----------------- OTP FORM -----------------
class OTPForm(forms.Form):
    code = forms.CharField(max_length=6, label="OTP")


# ----------------- EXTRA INFO FORM -----------------
class ExtraInfoForm(forms.Form):
    name = forms.CharField(max_length=150, label="Full Name")
    mobile = forms.CharField(max_length=15, label="Mobile Number")


# ----------------- USER PROFILE FORM -----------------
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "full_name", "mobile", "address",
            "business_name", "business_type", "gst_number",
            "profile_picture", "plan", "bank_name", "account_number",
            "ifsc_code", "upi_id", "qr_code"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ Lazy import to avoid circular dependency
        from billing.models import Plan

        if not self.instance.plan:
            basic_plan = Plan.objects.filter(name__iexact="Basic").first()
            if basic_plan:
                self.fields["plan"].initial = basic_plan