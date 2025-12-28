from .models import UISettings, CompanySettings

def global_settings(request):
    return {
        "ui": UISettings.objects.first(),
        "company": CompanySettings.objects.first(),
    }

def ui_settings(request):
    return {
        "ui": UISettings.objects.first()
    }
