from django.contrib import admin

from .models import CommissionPayout, CommissionRule

admin.site.register(CommissionRule)
admin.site.register(CommissionPayout)
