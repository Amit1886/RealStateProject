# accounts/forms.py
from django import forms
from django.contrib.auth import authenticate
from .models import User
from khataapp.models import UserProfile

class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ["username", "email", "mobile", "password"]

class LoginForm(forms.Form):
    identifier = forms.CharField(help_text="Email ya mobile")
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    use_otp = forms.BooleanField(required=False, initial=True)

    def clean(self):
        cleaned = super().clean()
        return cleaned

class OTPForm(forms.Form):
    code = forms.CharField(max_length=6)

class ExtraInfoForm(forms.Form):
    name = forms.CharField(max_length=150)
    mobile = forms.CharField(max_length=15)

class UserProfileAdminForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = "__all__"   # सब editable
