from django.http import FileResponse
from .utils.credit_report import generate_credit_report_pdf
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import UserProfilePlanForm
from .models import UserProfile
from billing.models import Plan
from .forms import PlanChangeForm
from django.contrib import messages
from django.utils.timezone import now
from .models import Party, CreditEntry, EMI, CreditSettings


@login_required
def credit_report_view(request):
    buffer = generate_credit_report_pdf()
    return FileResponse(buffer, as_attachment=True, filename="credit_report.pdf")

@login_required
def profile_view(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    return render(request, "profile_view.html", {"profile": profile})

@login_required
def update_plan(request):
    profile = UserProfile.objects.get(user=request.user)
    if request.method == "POST":
        form = PlanChangeForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("khataapp:profile_view")
    else:
        form = PlanChangeForm(instance=profile)
    return render(request, "profile_view.html", {"profile": profile, "form": form})

@login_required
def my_credits(request):
    """Show logged-in user's credit entries and EMI schedule."""
    try:
        party = Party.objects.get(user=request.user)
    except Party.DoesNotExist:
        messages.error(request, "No party profile found.")
        return render(request, "khataapp/my_credits.html", {"entries": []})

    entries = CreditEntry.objects.filter(party=party).select_related("party")
    emis = EMI.objects.filter(entry__party=party)

    return render(request, "khataapp/my_credits.html", {
        "party": party,
        "entries": entries,
        "emis": emis,
        "credit_settings": CreditSettings.get_solo(),  # singleton settings
        "today": now().date(),
    })