from django.contrib import admin

from .models import ScanEvent, ScannerConfig

admin.site.register(ScannerConfig)
admin.site.register(ScanEvent)
