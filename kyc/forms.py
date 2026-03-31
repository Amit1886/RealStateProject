import re

from django import forms
from django.utils import timezone

from .models import KYCDocument, KYCProfile


def _mask_aadhaar(value: str) -> str:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    if len(digits) >= 4:
        return f"XXXXXXXX{digits[-4:]}"
    return value or ""


class KYCProfileForm(forms.ModelForm):
    class Meta:
        model = KYCProfile
        fields = ["full_name", "pan_number", "aadhaar_number_masked"]

    def clean_pan_number(self):
        pan = (self.cleaned_data.get("pan_number") or "").strip().upper()
        if pan and not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan):
            raise forms.ValidationError("PAN format invalid. Example: ABCDE1234F")
        return pan

    def clean_aadhaar_number_masked(self):
        aadhaar = (self.cleaned_data.get("aadhaar_number_masked") or "").strip().replace(" ", "")
        if aadhaar and not re.fullmatch(r"(\d{12}|X{8}\d{4})", aadhaar):
            raise forms.ValidationError("Aadhaar should be 12 digits or masked like XXXXXXXX1234.")
        return _mask_aadhaar(aadhaar)

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.status = KYCProfile.Status.PENDING
        instance.last_submitted_at = timezone.now()
        if commit:
            instance.save()
        return instance


class KYCDocumentForm(forms.ModelForm):
    class Meta:
        model = KYCDocument
        fields = ["document_type", "document_file", "document_number_masked"]

    def clean_document_number_masked(self):
        value = (self.cleaned_data.get("document_number_masked") or "").strip()
        if value.isdigit() and len(value) == 12:
            return _mask_aadhaar(value)
        return value

