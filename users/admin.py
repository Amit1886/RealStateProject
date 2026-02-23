from django.contrib import admin

from .models import CommissionLedger, UserProfileExt, WalletLedger

admin.site.register(UserProfileExt)
admin.site.register(WalletLedger)
admin.site.register(CommissionLedger)
