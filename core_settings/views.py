from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse

from core_settings.permissions import has_feature
from core_settings.models import CompanySettings, UISettings, AppSettings


def party_disabled(request):
    return HttpResponse("❌ Party module disabled by admin")


def settings_dashboard(request):

    if not request.user.is_authenticated:
        return redirect("accounts:login")

    # 🔐 Subscription permission
    if not has_feature(request.user, "settings"):
        return HttpResponse("❌ Your plan does not allow Settings access")

    company = CompanySettings.objects.first()
    ui = UISettings.objects.first()
    app = AppSettings.objects.first()

    if request.method == "POST":

        # 🏢 Company
        if has_feature(request.user, "company"):
            company.company_name = request.POST.get("company_name")
            company.mobile = request.POST.get("mobile")
            company.email = request.POST.get("email")
            company.save()

        # 🎨 UI
        if has_feature(request.user, "ui"):
            ui.primary_color = request.POST.get("primary_color")
            ui.secondary_color = request.POST.get("secondary_color")
            ui.theme_mode = request.POST.get("theme_mode")
            ui.sidebar_position = request.POST.get("sidebar_position")
            ui.save()

        messages.success(request, "✅ Settings Updated Successfully")
        return redirect("settings")

    return render(request, "core_settings/dashboard.html", {
        "company": company,
        "ui": ui,
        "app": app
    })
