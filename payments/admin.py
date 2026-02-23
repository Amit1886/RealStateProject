from django.contrib import admin

from .models import DailyCashSummary, PaymentTransaction

admin.site.register(PaymentTransaction)
admin.site.register(DailyCashSummary)
