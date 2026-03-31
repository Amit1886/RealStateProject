from django.contrib import admin

from .models import Bank, LoanApplication, LoanProduct


@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "active", "support_phone")
    list_filter = ("active", "company")
    search_fields = ("name", "support_phone", "support_email")


@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = ("name", "bank", "property_type", "interest_rate", "loan_amount", "tenure_years", "active")
    list_filter = ("active", "property_type", "bank")
    search_fields = ("name", "bank__name")


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "applicant", "loan_product", "requested_amount", "emi_estimate", "status", "created_at")
    list_filter = ("status", "loan_product__bank")
    search_fields = ("applicant__email", "loan_product__name", "property__title")

