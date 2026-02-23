from django.contrib import admin

from .models import POSHoldBill, POSReprintLog, POSSession, POSTerminal

admin.site.register(POSTerminal)
admin.site.register(POSSession)
admin.site.register(POSHoldBill)
admin.site.register(POSReprintLog)
