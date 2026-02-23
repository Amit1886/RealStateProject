from django.contrib import admin

from .models import DeliveryAssignment, DeliveryTrackingPing

admin.site.register(DeliveryAssignment)
admin.site.register(DeliveryTrackingPing)
