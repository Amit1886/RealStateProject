from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from rest_framework import permissions, viewsets

from .forms import KYCDocumentForm, KYCProfileForm
from .models import KYCDocument, KYCProfile
from .serializers import KYCDocumentSerializer, KYCProfileSerializer


class KYCProfileViewSet(viewsets.ModelViewSet):
    serializer_class = KYCProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = KYCProfile.objects.prefetch_related("documents").order_by("-updated_at")
        return queryset if self.request.user.is_staff else queryset.filter(user=self.request.user)


class KYCDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = KYCDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = KYCDocument.objects.select_related("profile", "profile__user").order_by("-uploaded_at")
        return queryset if self.request.user.is_staff else queryset.filter(profile__user=self.request.user)


@login_required
def dashboard(request):
    profile, _ = KYCProfile.objects.get_or_create(
        user=request.user,
        defaults={"full_name": request.user.get_full_name() or request.user.username},
    )
    if request.method == "POST":
        form = KYCProfileForm(request.POST, instance=profile)
        doc_form = KYCDocumentForm(request.POST, request.FILES)
        if form.is_valid() and doc_form.is_valid():
            profile = form.save()
            if doc_form.cleaned_data.get("document_file"):
                doc = doc_form.save(commit=False)
                doc.profile = profile
                doc.status = KYCDocument.Status.PENDING
                doc.save()
            messages.success(request, "KYC submitted successfully. Review queue me chala gaya hai.")
            return redirect("kyc:dashboard")
        messages.error(request, "KYC form me kuch fields correct karni hain.")
    else:
        form = KYCProfileForm(instance=profile)
        doc_form = KYCDocumentForm()

    context = {
        "kyc_profile": profile,
        "form": form,
        "doc_form": doc_form,
        "documents": profile.documents.all(),
        "pending_profiles": KYCProfile.objects.select_related("user").filter(status=KYCProfile.Status.PENDING).order_by("-last_submitted_at")[:10] if request.user.is_staff else [],
    }
    return render(request, "kyc/dashboard.html", context)


@login_required
@require_POST
def review_profile(request, profile_id):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponse("Admin access required", status=403)
    profile = get_object_or_404(KYCProfile.objects.select_related("user"), pk=profile_id)
    action = (request.POST.get("action") or "").strip().lower()
    reason = (request.POST.get("reason") or "").strip()
    if action == "approve":
        profile.approve(reviewer=request.user)
        messages.success(request, f"KYC approved for {profile.user.email}.")
    elif action == "reject":
        profile.reject(reviewer=request.user, reason=reason or "Document mismatch")
        messages.success(request, f"KYC rejected for {profile.user.email}.")
    else:
        messages.error(request, "Unknown KYC review action.")
    return redirect("kyc:dashboard")

