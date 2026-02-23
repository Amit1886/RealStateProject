from django.contrib import admin

from .models import CreditRiskScore, ProductVelocity, SalesAnalyticsSnapshot, SalesmanPerformance

admin.site.register(SalesAnalyticsSnapshot)
admin.site.register(ProductVelocity)
admin.site.register(SalesmanPerformance)
admin.site.register(CreditRiskScore)
