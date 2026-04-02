import csv
import urllib.parse

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, get_user_model, logout
from django.contrib.auth import get_backends
from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum, Q, Max, Count
from django.core.paginator import Paginator, EmptyPage
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from decimal import Decimal
from django.db.models import Case, When, F, FloatField
from django.http import HttpResponseForbidden
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from requests import request
from .models import DailySummary
from accounts.models import LedgerEntry as Transaction
from django.utils.timezone import now
from datetime import timedelta
# accounts/views.py

from .models import Expense, ExpenseCategory, LoyaltyPoints, LoyaltyProgram, MembershipTier, SpecialOffer
import uuid
import json
from accounts.models import UserProfile as KhataProfile
from django.views.decorators.http import require_POST, require_http_methods
from billing.services import ensure_free_plan
from billing.services import user_has_feature
from billing.permissions import feature_required



# Accounts
from datetime import datetime, date
from .models import  OTP, LedgerEntry
from .utils import render_to_pdf_bytes, send_email_otp, send_sms_otp
from .forms import SignupForm, LoginForm, OTPForm, UserProfileForm

# External Models
from accounts.models import UserProfile
Party = UserProfile
try:
    from agents.models import Agent as FieldAgent
except Exception:
    FieldAgent = None
try:
    from core_settings.models import CompanySettings
except Exception:
    CompanySettings = None
CollectorVisit = None
LoginLink = None
OfflineMessage = None
ReminderLog = None
from whatsapp.api_connector import send_whatsapp_message
from billing.models import Plan, Subscription
from billing.services import get_active_subscription, get_locked_feature_count, get_usage_summary
from .services.crm_dashboard import build_crm_dashboard_context
from .services.snapshot import build_business_snapshot
from django.db.utils import OperationalError, ProgrammingError
try:
    from commerce.models import Order, Payment, Invoice, Quotation
    from commerce.models import Coupon, UserCoupon
except Exception:
    Order = Payment = Invoice = Quotation = Coupon = UserCoupon = None



User = get_user_model()
PARTY_SMART_KHATA_DEFER_FIELDS = (
    "credit_score",
    "last_payment_date",
    "average_payment_delay",
    "total_due",
)
# Only defer fields that actually exist on the Party model in this build.
_party_fields = {f.name for f in Party._meta.get_fields()}
PARTY_DEFER_FIELDS = tuple(f for f in PARTY_SMART_KHATA_DEFER_FIELDS if f in _party_fields)

def calculate_running_balance(entries):
    balance = 0

    for e in entries:
        amount = e.get("amount", 0)

        # Debit = positive
        # Credit = negative
        if amount > 0:
            e["debit"] = amount
            e["credit"] = 0
        else:
            e["debit"] = 0
            e["credit"] = abs(amount)

        # Running balance (Busy style)
        balance += amount
        e["balance"] = balance

    return entries
# ---------------------------------------------------
# WhatsApp Message URL Builder
# ---------------------------------------------------
def whatsapp_message_url(mobile, text):
    import urllib.parse
    return f"https://wa.me/91{mobile}?text={urllib.parse.quote(text)}"


def _resolve_date_range_preset(raw_value: str | None) -> tuple[str, str]:
    value = (raw_value or "").strip().lower()
    today = timezone.localdate()
    if value == "today":
        return today.isoformat(), today.isoformat()
    if value == "this_week":
        week_start = today - timedelta(days=today.weekday())
        return week_start.isoformat(), today.isoformat()
    if value == "this_month":
        month_start = today.replace(day=1)
        return month_start.isoformat(), today.isoformat()
    return "", ""


# ---------------------------------------------------
# Role Resolution
# ---------------------------------------------------
def resolve_user_role(user):
    if not user:
        return "party"

    if user.is_superuser or user.is_staff:
        return "owner"

    agent = getattr(user, "field_agent_profile", None)
    if agent and agent.is_active:
        return "collector" if agent.role == "collector" else "staff"

    # Group-based roles (seeded by management commands)
    if user.groups.filter(name__iexact="agent").exists():
        return "collector"
    if user.groups.filter(name__iexact="staff").exists():
        return "staff"

    # Party/customer-style accounts (read-only views)
    if user.groups.filter(name__iexact="party").exists():
        return "party"
    if user.groups.filter(name__iexact="customer").exists():
        return "party"
    if user.groups.filter(name__iexact="supplier").exists():
        return "party"
    if user.groups.filter(name__iexact="vendor").exists():
        return "party"

    # Legacy heuristic: party accounts often use a local email domain.
    try:
        email = (user.email or "").strip().lower()
        if email.endswith("@party.local"):
            return "party"
    except Exception:
        pass

    # Safety default for desktop: treat unknown users as owners so signup/login isn't blocked.
    return "owner"


def role_based_redirect(user):
    return redirect("accounts:dashboard")

def users_list(request):
    admin_users = User.objects.filter(is_staff=True)  # admin users
    signup_users = User.objects.filter(is_staff=False)  # users created from signup
    profiles = UserProfile.objects.all()  # profile data if needed

    context = {
        "admin_users": admin_users,
        "signup_users": signup_users,
        "profiles": profiles,
    }
    return render(request, "accounts/users_list.html", context)

# ----------------- DASHBOARD -----------------
@login_required
def dashboard(request):
    user = request.user
    from django.conf import settings

    # ====
    # PERIOD FILTER
    # ====
    period = request.GET.get("period", "today")
    today = now().date()

    if period == "yesterday":
        selected_date = today - timedelta(days=1)
    elif period == "month":
        selected_date = today.replace(day=1)
    else:
        selected_date = today

    # ====
    # BUSINESS SNAPSHOT
    # ====
    force_refresh = request.GET.get("refresh") == "1"
    snapshot = build_business_snapshot(user, selected_date, refresh=force_refresh)

    # ====
    # GREETING
    # ====
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good Morning"
    elif hour < 17:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    # ====
    # PROFILE
    # ====
    profile, _ = UserProfile.objects.get_or_create(user=user)

    # ====
    # DAILY SUMMARY
    # ====
    summary = update_daily_summary(user, refresh=force_refresh)

    # ====
    # RECENT DATA
    # ====
    recent_parties_qs = Party.objects.filter(user=user).order_by("-id")
    if PARTY_DEFER_FIELDS:
        recent_parties_qs = recent_parties_qs.defer(*PARTY_DEFER_FIELDS)
    recent_parties = recent_parties_qs[:5]
    recent_transactions = Transaction.objects.filter(
        party__user=user
    ).order_by("-id")[:5]

    # ====
    # OVERALL TOTALS
    # ====
    total_credit_all = Transaction.objects.filter(
        party__user=user, txn_type="credit"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    total_debit_all = Transaction.objects.filter(
        party__user=user, txn_type="debit"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    net_balance = total_debit_all - total_credit_all

    # ====
    # REAL ESTATE AGENT DASHBOARD (leads/deals/visits)
    # ====
    agent_dashboard = None
    agent_profile = getattr(user, "agent_profile", None)
    if agent_profile:
        try:
            from leads.models import Lead
            from deals.models import Deal
            from visits.models import SiteVisit

            leads_qs = Lead.objects.filter(assigned_agent=agent_profile)
            agent_lead_stats = {
                "total": leads_qs.count(),
                "new": leads_qs.filter(status=Lead.Status.NEW).count(),
                "hot": leads_qs.filter(temperature=Lead.Temperature.HOT).count(),
                "visit": leads_qs.filter(stage=Lead.Stage.VISIT).count(),
            }

            deals_qs = Deal.objects.filter(agent=agent_profile)
            agent_deal_stats = {
                "open_value": deals_qs.filter(
                    status__in=[Deal.Status.DRAFT, Deal.Status.PENDING]
                ).aggregate(total=Sum("deal_amount"))["total"]
                or Decimal("0.00"),
                "won_value": deals_qs.filter(status=Deal.Status.WON).aggregate(total=Sum("deal_amount"))["total"]
                or Decimal("0.00"),
                "open_count": deals_qs.filter(status__in=[Deal.Status.DRAFT, Deal.Status.PENDING]).count(),
                "won_count": deals_qs.filter(status=Deal.Status.WON).count(),
            }

            upcoming_visits = list(
                SiteVisit.objects.filter(agent=agent_profile, visit_date__gte=timezone.now())
                .order_by("visit_date")[:5]
                .values("id", "visit_date", "location", "status", "lead__name")
            )

            agent_dashboard = {
                "agent": agent_profile,
                "lead_stats": agent_lead_stats,
                "deal_stats": agent_deal_stats,
                "upcoming_visits": upcoming_visits,
            }
        except Exception:
            agent_dashboard = None

    # ====
    # PARTY CARDS
    # ====
    party_cards = []
    parties_qs = Party.objects.filter(user=user).order_by("full_name", "user__username")
    if PARTY_DEFER_FIELDS:
        parties_qs = parties_qs.defer(*PARTY_DEFER_FIELDS)
    parties = parties_qs

    decimal_zero = Decimal("0.00")

    # Avoid N+1 aggregation queries per party (dashboard can become very slow with many parties).
    txn_totals = (
        Transaction.objects.filter(party__user=user)
        .values("party_id", "txn_type")
        .annotate(total=Sum("amount"))
    )
    cash_credit_by_party = {}
    cash_debit_by_party = {}
    for r in txn_totals:
        party_id = r.get("party_id")
        total = r.get("total") or decimal_zero
        if r.get("txn_type") == "credit":
            cash_credit_by_party[party_id] = total
        else:
            cash_debit_by_party[party_id] = total

    invoice_total_by_party = {}
    if Invoice:
        try:
            invoice_total_by_party = {
                r["order__party_id"]: (r["total"] or decimal_zero)
                for r in Invoice.objects.filter(order__party__user=user)
                .values("order__party_id")
                .annotate(total=Sum("amount"))
            }
        except (OperationalError, ProgrammingError):
            invoice_total_by_party = {}

    payment_total_by_party = {}
    if Payment:
        try:
            payment_total_by_party = {
                r["invoice__order__party_id"]: (r["total"] or decimal_zero)
                for r in Payment.objects.filter(invoice__order__party__user=user)
                .values("invoice__order__party_id")
                .annotate(total=Sum("amount"))
            }
        except (OperationalError, ProgrammingError):
            payment_total_by_party = {}

    for party in parties:

        party_cash_credit = cash_credit_by_party.get(party.id, decimal_zero)
        party_cash_debit = cash_debit_by_party.get(party.id, decimal_zero)
        invoice_total = invoice_total_by_party.get(party.id, decimal_zero)
        payment_total = payment_total_by_party.get(party.id, decimal_zero)

        total_debit = invoice_total + party_cash_debit
        total_credit = payment_total + party_cash_credit

        balance = total_debit - total_credit   # 👈 yaha balance define kiya

        party_cards.append({
            "party": party,
            "total_debit": total_debit,     # ✅ correct variable
            "total_credit": total_credit,   # ✅ correct variable
            "balance": balance,             # ✅ correct variable
        })

    # ====
    # COUPONS
    # ====
    active_coupons = []
    user_coupons = []
    if Coupon and UserCoupon:
        try:
            active_coupons = Coupon.objects.filter(is_active=True).order_by("-created_at")[:10]
            user_coupons = UserCoupon.objects.filter(user=user).select_related("coupon")
        except (OperationalError, ProgrammingError):
            active_coupons = []
            user_coupons = []

    # ====
    # SUBSCRIPTION & FEATURES
    # ====
    subscription = get_active_subscription(user)
    locked_features_count = get_locked_feature_count(user)
    usage_summary = get_usage_summary(user)

    # ====
    # COMMERCE: QUOTATIONS
    # ====
    if Quotation:
        try:
            quotation_total = Quotation.objects.filter(party__user=user).count()
            quotation_pending_approval = Quotation.objects.filter(party__user=user, status=Quotation.Status.VERIFIED).count()
            quotation_converted = Quotation.objects.filter(party__user=user, status=Quotation.Status.CONVERTED).count()
            quotation_rejected = Quotation.objects.filter(party__user=user, status=Quotation.Status.REJECTED).count()
        except (OperationalError, ProgrammingError):
            # Migrations may not be applied yet (e.g., fresh DB). Keep dashboard functional.
            quotation_total = 0
            quotation_pending_approval = 0
            quotation_converted = 0
            quotation_rejected = 0
    else:
        quotation_total = 0
        quotation_pending_approval = 0
        quotation_converted = 0
        quotation_rejected = 0

    # ====
    # SMART KHATA: HIGH DUE CUSTOMERS (Widget)
    # ====
    high_due_customers = []
    if {"total_due", "credit_score"}.issubset(_party_fields):
        try:
            high_due_qs = (
                Party.objects.filter(user=user, party_type="customer", total_due__gt=0)
                .order_by("-total_due", "name", "id")[:5]
            )
            last_sent_map = {
                row["party_id"]: row["last_sent"]
                for row in ReminderLog.objects.filter(party__in=high_due_qs, status="sent")
                .values("party_id")
                .annotate(last_sent=Max("sent_at"))
            }
            for c in high_due_qs:
                high_due_customers.append(
                    {
                        "party": c,
                        "due": getattr(c, "total_due", 0) or 0,
                        "credit_score": int(getattr(c, "credit_score", 0) or 0),
                        "last_reminder_sent": last_sent_map.get(c.id),
                    }
                )
        except Exception:
            high_due_customers = []

    # ====
    # SMART BI: Business Health Meter (lazy daily compute)
    # ====
    business_health = None
    business_health_level = None
    try:
        from smart_bi.services.business_health import health_level as _health_level, upsert_business_metric

        business_health = upsert_business_metric(user, day=timezone.localdate())
        business_health_level = _health_level(getattr(business_health, "health_score", 0) or 0)
    except Exception:
        business_health = None
        business_health_level = None

    duplicate_invoice_alerts = []
    try:
        from smart_bi.models import DuplicateInvoiceLog

        duplicate_invoice_alerts = list(
            DuplicateInvoiceLog.objects.select_related(
                "invoice",
                "invoice__order",
                "invoice__order__party",
                "possible_duplicate",
                "possible_duplicate__order",
                "possible_duplicate__order__party",
            )
            .filter(user=user)
            .order_by("-created_at", "-id")[:5]
        )
    except Exception:
        duplicate_invoice_alerts = []

    # ====
    # REAL ESTATE SHOWCASE CONTEXT
    # ====
    workspace_role = "admin" if (user.is_superuser or user.is_staff) else "agent" if agent_profile else "customer"
    role_labels = {
        "admin": "Admin Command Center",
        "agent": "Agent Operating Dashboard",
        "customer": "Customer Property Journey",
    }
    platform_links = [
        {
            "label": "React Home",
            "url": "http://localhost:5173/",
            "description": "Public workspace preview with role-based login and SaaS showcase.",
        },
        {
            "label": "React Login",
            "url": "http://localhost:5173/accounts/login/",
            "description": "React login route showing the demo flow and all feature families.",
        },
        {
            "label": "Django Dashboard",
            "url": request.build_absolute_uri(reverse("accounts:dashboard")),
            "description": "This server-rendered dashboard with the same feature story.",
        },
        {
            "label": "Edit Profile",
            "url": request.build_absolute_uri(reverse("accounts:edit_profile")),
            "description": "Django-side profile editing entry point.",
        },
    ]

    dashboard_feature_tracks_map = {
        "admin": [
            {
                "title": "Tenant Operations",
                "summary": "Company-wide control over the network.",
                "items": [
                    "Approve agents, map service areas, and manage team coverage.",
                    "Moderate listings, builder projects, and marketplace visibility.",
                    "Track subscriptions, wallet operations, and commission flows.",
                    "Review fraud flags, documents, and platform security posture.",
                ],
            },
            {
                "title": "Intelligence Layer",
                "summary": "Advanced analytics visible inside the SaaS stack.",
                "items": [
                    "Demand heatmaps, price trends, and hot investment locations.",
                    "Property aggregation and duplicate detection pipeline.",
                    "Investor matching and builder marketplace expansion.",
                    "Campaign performance, automation trails, and revenue insights.",
                ],
            },
        ],
        "agent": [
            {
                "title": "Agent Workbench",
                "summary": "Sab kuch profile se settings tak visible.",
                "items": [
                    "Profile, KYC, license, city, district, state, and pin-code coverage.",
                    "Lead queue, notes, follow-ups, call logs, and visit scheduling.",
                    "Listing uploads, approvals visibility, wishlist-ready marketplace inventory.",
                    "Wallet, commission payout, premium leads, and plan-based selling capacity.",
                ],
            },
            {
                "title": "Automation + Intelligence",
                "summary": "Field selling ko smarter banane wale modules.",
                "items": [
                    "AI voice qualification for fresh leads.",
                    "Demand heatmaps and price trend awareness by locality.",
                    "Investor opportunities and builder project launches.",
                    "Document vault, fraud checks, and alert-driven follow-up support.",
                ],
            },
        ],
        "customer": [
            {
                "title": "Customer Journey",
                "summary": "Discovery, shortlist, and visit coordination in one place.",
                "items": [
                    "Marketplace filters, property comparison, and shortlist flows.",
                    "Visit scheduling linked directly to the CRM pipeline.",
                    "Owner listing upload and communication-ready property enquiries.",
                    "Alerts, secure documents, and mobile-ready access path.",
                ],
            },
        ],
    }
    dashboard_demo_steps_map = {
        "admin": [
            "Review approved agents and verify area mapping.",
            "Open listings and approve or reject pending inventory.",
            "Check analytics for heatmaps, price trends, and top zones.",
            "Monitor communication automation and revenue dashboards.",
        ],
        "agent": [
            "Open profile to review KYC, license, service areas, and readiness.",
            "Go to leads and update the pipeline from new to closed.",
            "Show properties from marketplace and schedule a site visit.",
            "Check wallet, commissions, premium leads, and subscription access.",
            "Open settings to review automation, security, and demo routes.",
        ],
        "customer": [
            "Search marketplace inventory and compare shortlisted options.",
            "Add a property to wishlist and schedule a visit.",
            "Track saved preferences, alerts, and communication touchpoints.",
        ],
    }
    dashboard_settings_cards_map = {
        "admin": [
            {
                "title": "Security",
                "items": ["JWT authentication", "OTP login ready", "Role-based permissions", "Tenant-scoped access control"],
            },
            {
                "title": "Automation",
                "items": ["Lead routing", "Notification fanout", "Call, email, SMS, and WhatsApp hooks", "Celery + Redis workers"],
            },
            {
                "title": "Access",
                "items": ["React web dashboard", "Django dashboard", "API-first architecture", "Flutter mobile app path"],
            },
        ],
        "agent": [
            {
                "title": "Profile Controls",
                "items": ["Identity and mobile", "License and KYC", "Coverage mapping", "Franchise visibility"],
            },
            {
                "title": "Communication",
                "items": ["CRM call logs", "WhatsApp-ready listing sharing", "Email and SMS hooks", "AI voice qualification"],
            },
            {
                "title": "Workspace Access",
                "items": ["React home", "React login route", "Django dashboard", "Edit profile entry point"],
            },
        ],
        "customer": [
            {
                "title": "Account",
                "items": ["Identity and contact", "Budget and location preferences", "Secure access", "Wishlist visibility"],
            },
            {
                "title": "Alerts",
                "items": ["New property alerts", "Price drop alerts", "Builder launch signals", "In-app, email, SMS, and WhatsApp"],
            },
            {
                "title": "Experience",
                "items": ["Responsive dashboard", "Mobile-ready services", "Visit reminders", "Agent-assisted journey"],
            },
        ],
    }

    real_estate_counts = {
        "lead_count": 0,
        "property_count": 0,
        "visit_count": 0,
        "builder_count": 0,
        "project_count": 0,
        "aggregated_count": 0,
        "heatmap_count": 0,
        "trend_count": 0,
        "investor_match_count": 0,
        "premium_lead_count": 0,
        "document_count": 0,
        "voice_call_count": 0,
        "bank_count": 0,
        "loan_product_count": 0,
        "loan_application_count": 0,
        "verification_count": 0,
        "scheme_count": 0,
        "scheme_match_count": 0,
        "article_count": 0,
        "wallet_balance": getattr(getattr(user, "wallet", None), "balance", Decimal("0.00")) or Decimal("0.00"),
        "subscription_name": "",
    }
    agent_profile_summary = None
    featured_property = None
    top_loan_products = []
    top_schemes = []
    top_articles = []
    recent_verifications = []
    try:
        from leads.models import Builder as REBuilder
        from leads.models import Lead as RELead
        from leads.models import Property as REProperty
        from leads.models import PropertyProject
        from intelligence.models import (
            AggregatedProperty,
            DemandHeatmapSnapshot,
            InvestorMatch,
            PremiumLeadListing,
            PriceTrendSnapshot,
            PropertyAlertSubscription,
            RealEstateDocument,
        )
        from loans.models import Bank, LoanApplication, LoanProduct
        from verification.models import PropertyVerification
        from schemes.models import Scheme, UserSchemeMatch
        from content.models import Article
        from visits.models import SiteVisit
        from voice.models import VoiceCall

        company = getattr(user, "company", None)
        lead_qs = RELead.objects.filter(company=company) if company else RELead.objects.all()
        property_qs = REProperty.objects.filter(company=company) if company else REProperty.objects.all()
        visit_qs = SiteVisit.objects.all()
        builder_qs = REBuilder.objects.filter(company=company) if company else REBuilder.objects.all()
        project_qs = PropertyProject.objects.filter(company=company) if company else PropertyProject.objects.all()
        aggregated_qs = AggregatedProperty.objects.filter(company=company) if company else AggregatedProperty.objects.all()
        heatmap_qs = DemandHeatmapSnapshot.objects.filter(company=company) if company else DemandHeatmapSnapshot.objects.all()
        trend_qs = PriceTrendSnapshot.objects.filter(company=company) if company else PriceTrendSnapshot.objects.all()
        investor_qs = InvestorMatch.objects.all()
        premium_qs = PremiumLeadListing.objects.filter(company=company) if company else PremiumLeadListing.objects.all()
        document_qs = RealEstateDocument.objects.filter(company=company) if company else RealEstateDocument.objects.all()
        voice_qs = VoiceCall.objects.all()
        bank_qs = Bank.objects.filter(company=company) if company else Bank.objects.filter(company__isnull=True)
        loan_product_qs = LoanProduct.objects.select_related("bank")
        loan_application_qs = LoanApplication.objects.select_related("loan_product", "loan_product__bank", "property", "applicant")
        verification_qs = PropertyVerification.objects.select_related("property", "requested_by", "reviewed_by")
        scheme_qs = Scheme.objects.all()
        scheme_match_qs = UserSchemeMatch.objects.select_related("scheme", "property", "user")
        article_qs = Article.objects.select_related("category", "author")
        alerts_count = PropertyAlertSubscription.objects.filter(customer__user=user).count()

        if company:
            loan_product_qs = loan_product_qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
            loan_application_qs = loan_application_qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
            verification_qs = verification_qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
            scheme_qs = scheme_qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
            scheme_match_qs = scheme_match_qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
            article_qs = article_qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
        else:
            bank_qs = bank_qs.filter(company__isnull=True)
            loan_product_qs = loan_product_qs.filter(company__isnull=True)
            loan_application_qs = loan_application_qs.filter(company__isnull=True)
            verification_qs = verification_qs.filter(company__isnull=True)
            scheme_qs = scheme_qs.filter(company__isnull=True)
            scheme_match_qs = scheme_match_qs.filter(company__isnull=True)
            article_qs = article_qs.filter(company__isnull=True)

        if workspace_role == "agent" and agent_profile:
            lead_qs = lead_qs.filter(assigned_agent=agent_profile)
            property_qs = property_qs.filter(Q(assigned_agent=agent_profile) | Q(owner=user)).distinct()
            visit_qs = visit_qs.filter(agent=agent_profile)
            premium_qs = premium_qs.filter(Q(buyer_agent=agent_profile) | Q(seller=user)).distinct()
            document_qs = document_qs.filter(Q(agent=agent_profile) | Q(uploaded_by=user)).distinct()
            voice_qs = voice_qs.filter(Q(agent=user) | Q(lead__assigned_agent=agent_profile)).distinct()
            loan_application_qs = loan_application_qs.filter(models.Q(applicant=user) | models.Q(property__assigned_agent=agent_profile)).distinct()
            verification_qs = verification_qs.filter(models.Q(requested_by=user) | models.Q(property__assigned_agent=agent_profile)).distinct()
            scheme_match_qs = scheme_match_qs.filter(models.Q(user=user) | models.Q(property__assigned_agent=agent_profile)).distinct()
            article_qs = article_qs.filter(is_published=True)
            agent_profile_summary = {
                "approval_status": agent_profile.approval_status,
                "kyc_verified": agent_profile.kyc_verified,
                "license_number": agent_profile.license_number,
                "experience_years": agent_profile.experience_years,
                "coverage": ", ".join([v for v in [agent_profile.city, agent_profile.district, agent_profile.state, agent_profile.pin_code] if v]) or "Coverage not mapped",
                "rating": agent_profile.rating,
                "total_sales": agent_profile.total_sales,
            }
        elif workspace_role == "customer":
            property_qs = property_qs.filter(Q(status=REProperty.Status.APPROVED) | Q(status=REProperty.Status.ACTIVE))
            visit_qs = visit_qs.filter(customer=user)
            premium_qs = premium_qs.filter(seller=user)
            document_qs = document_qs.filter(Q(customer__user=user) | Q(uploaded_by=user)).distinct()
            voice_qs = voice_qs.filter(lead__created_by=user).distinct()
            loan_application_qs = loan_application_qs.filter(applicant=user)
            verification_qs = verification_qs.filter(models.Q(requested_by=user) | models.Q(property__owner=user)).distinct()
            scheme_match_qs = scheme_match_qs.filter(user=user)
            article_qs = article_qs.filter(is_published=True)
        else:
            investor_qs = investor_qs.filter(
                Q(property__company=company) | Q(project__company=company)
            ).distinct() if company else investor_qs

        featured_property = (
            property_qs.exclude(status=REProperty.Status.REJECTED)
            .select_related("assigned_agent", "owner")
            .order_by("-approved_at", "-created_at")
            .first()
        )
        if featured_property:
            top_loan_products = list(
                loan_product_qs.filter(active=True).filter(
                    models.Q(property_type=featured_property.property_type) | models.Q(property_type="")
                )[:3]
            )
            recent_verifications = list(
                verification_qs.filter(property=featured_property).order_by("-created_at")[:3]
            )
        else:
            top_loan_products = list(loan_product_qs.filter(active=True)[:3])
            recent_verifications = list(verification_qs.order_by("-created_at")[:3])

        top_schemes = list(scheme_qs.filter(active=True)[:3])
        top_articles = list(article_qs.order_by("-published_at", "-created_at")[:3])

        real_estate_counts.update(
            {
                "lead_count": lead_qs.count(),
                "property_count": property_qs.count(),
                "visit_count": visit_qs.count(),
                "builder_count": builder_qs.count(),
                "project_count": project_qs.count(),
                "aggregated_count": aggregated_qs.count(),
                "heatmap_count": heatmap_qs.count(),
                "trend_count": trend_qs.count(),
                "investor_match_count": investor_qs.count(),
                "premium_lead_count": premium_qs.count(),
                "document_count": document_qs.count() + alerts_count,
                "voice_call_count": voice_qs.count(),
                "bank_count": bank_qs.count(),
                "loan_product_count": loan_product_qs.count(),
                "loan_application_count": loan_application_qs.count(),
                "verification_count": verification_qs.count(),
                "scheme_count": scheme_qs.count(),
                "scheme_match_count": scheme_match_qs.count(),
                "article_count": article_qs.count(),
                "subscription_name": getattr(subscription, "plan_name", "") or getattr(getattr(subscription, "plan", None), "name", ""),
            }
        )
    except Exception:
        agent_profile_summary = None

    # ====
    # CONTEXT
    # ====
    dashboard_tab_feature_map = {
        "leads": "crm.leads",
        "properties": "crm.properties",
        "deals": "crm.deals",
        "agents": "crm.agents",
        "reports": "crm.reports",
        "settings": "crm.settings",
        "wallet": "crm.wallet",
    }
    dashboard_feature_flags = {
        key: user_has_feature(user, feature_key) for key, feature_key in dashboard_tab_feature_map.items()
    }
    allowed_dashboard_tabs = {"dashboard"}
    allowed_dashboard_tabs.update(key for key, enabled in dashboard_feature_flags.items() if enabled)
    active_dashboard_tab = (request.GET.get("tab") or "dashboard").strip().lower()
    if active_dashboard_tab not in allowed_dashboard_tabs:
        active_dashboard_tab = "dashboard"

    dashboard_base_url = reverse("accounts:dashboard")
    dashboard_tabs = [
        {"key": "dashboard", "label": "Dashboard", "href": f"{dashboard_base_url}?tab=dashboard#module-workspace"},
        {"key": "leads", "label": "Leads", "href": f"{dashboard_base_url}?tab=leads#module-workspace", "feature_key": "crm.leads"},
        {"key": "properties", "label": "Properties", "href": f"{dashboard_base_url}?tab=properties#module-workspace", "feature_key": "crm.properties"},
        {"key": "deals", "label": "Deals", "href": f"{dashboard_base_url}?tab=deals#module-workspace", "feature_key": "crm.deals"},
        {"key": "agents", "label": "Agents", "href": f"{dashboard_base_url}?tab=agents#module-workspace", "feature_key": "crm.agents"},
        {"key": "reports", "label": "Reports", "href": f"{dashboard_base_url}?tab=reports#module-workspace", "feature_key": "crm.reports"},
        {"key": "wallet", "label": "Wallet", "href": f"{dashboard_base_url}?tab=wallet#module-workspace", "feature_key": "crm.wallet"},
        {"key": "settings", "label": "Settings", "href": f"{dashboard_base_url}?tab=settings#module-workspace", "feature_key": "crm.settings"},
    ]
    dashboard_tabs = [tab for tab in dashboard_tabs if not tab.get("feature_key") or dashboard_feature_flags.get(tab["key"], True)]

    dashboard_page_cache_key = None
    cached_dashboard_context = None
    if active_dashboard_tab == "dashboard" and not force_refresh:
        dashboard_page_cache_key = ":".join(
            [
                "accounts_dashboard_page",
                str(getattr(user, "pk", "anon")),
                workspace_role,
                str(getattr(getattr(user, "company", None), "pk", "none")),
                str(getattr(getattr(user, "agent_profile", None), "pk", "none")),
                period,
                request.get_host() or "localhost",
            ]
        )
        cached_dashboard_context = cache.get(dashboard_page_cache_key)
        if cached_dashboard_context is not None:
            return render(request, "accounts/dashboard.html", cached_dashboard_context)

    crm_dashboard = build_crm_dashboard_context(user, refresh=force_refresh)
    lead_rows = list(crm_dashboard.get("recent_leads", []))
    lead_filters = {"query": "", "source": "", "status": "", "stage": "", "date_range": "", "date_from": "", "date_to": ""}
    lead_source_choices = ()
    lead_status_choices = ()
    lead_stage_choices = ()
    lead_total_count = crm_dashboard.get("total_leads", 0)
    lead_filtered_count = len(lead_rows)
    lead_reset_href = f"{dashboard_base_url}?tab=leads#module-workspace"
    lead_export_href = f"{dashboard_base_url}?tab=leads&lead_export=csv"
    lead_share_href = "https://wa.me/?text=Lead%20list"
    lead_email_share_href = "mailto:?subject=Lead%20List&body=Lead%20list"
    lead_current_url = request.build_absolute_uri(lead_reset_href)
    if active_dashboard_tab == "leads":
        from leads.models import Lead

        lead_queryset = _crm_lead_queryset_for_user(user).order_by("-created_at", "-id")
        lead_total_count = lead_queryset.count()
        lead_source_choices = Lead.Source.choices
        lead_status_choices = Lead.Status.choices
        lead_stage_choices = Lead.Stage.choices

        lead_filters = {
            "query": (request.GET.get("lead_query") or "").strip(),
            "source": (request.GET.get("lead_source") or "").strip(),
            "status": (request.GET.get("lead_status") or "").strip(),
            "stage": (request.GET.get("lead_stage") or "").strip(),
            "date_range": (request.GET.get("lead_date_range") or "").strip(),
            "date_from": (request.GET.get("lead_date_from") or "").strip(),
            "date_to": (request.GET.get("lead_date_to") or "").strip(),
        }
        lead_preset_from, lead_preset_to = _resolve_date_range_preset(lead_filters["date_range"])
        if lead_preset_from and lead_preset_to:
            lead_filters["date_from"] = lead_preset_from
            lead_filters["date_to"] = lead_preset_to

        valid_sources = {value for value, _label in lead_source_choices}
        valid_statuses = {value for value, _label in lead_status_choices}
        valid_stages = {value for value, _label in lead_stage_choices}

        if lead_filters["query"]:
            query = lead_filters["query"]
            lead_queryset = lead_queryset.filter(
                Q(name__icontains=query)
                | Q(mobile__icontains=query)
                | Q(email__icontains=query)
                | Q(city__icontains=query)
            )

        if lead_filters["source"] in valid_sources:
            lead_queryset = lead_queryset.filter(source=lead_filters["source"])
        else:
            lead_filters["source"] = ""

        if lead_filters["status"] in valid_statuses:
            lead_queryset = lead_queryset.filter(status=lead_filters["status"])
        else:
            lead_filters["status"] = ""

        if lead_filters["stage"] in valid_stages:
            lead_queryset = lead_queryset.filter(stage=lead_filters["stage"])
        else:
            lead_filters["stage"] = ""

        if lead_filters["date_from"]:
            start_date = parse_date(lead_filters["date_from"])
            if start_date:
                lead_queryset = lead_queryset.filter(created_at__date__gte=start_date)
            else:
                lead_filters["date_from"] = ""
        if lead_filters["date_to"]:
            end_date = parse_date(lead_filters["date_to"])
            if end_date:
                lead_queryset = lead_queryset.filter(created_at__date__lte=end_date)
            else:
                lead_filters["date_to"] = ""

        lead_filtered_count = lead_queryset.count()

        lead_query_params = {"tab": "leads"}
        if lead_filters["query"]:
            lead_query_params["lead_query"] = lead_filters["query"]
        if lead_filters["source"]:
            lead_query_params["lead_source"] = lead_filters["source"]
        if lead_filters["status"]:
            lead_query_params["lead_status"] = lead_filters["status"]
        if lead_filters["stage"]:
            lead_query_params["lead_stage"] = lead_filters["stage"]
        if lead_filters["date_range"]:
            lead_query_params["lead_date_range"] = lead_filters["date_range"]
        if lead_filters["date_from"]:
            lead_query_params["lead_date_from"] = lead_filters["date_from"]
        if lead_filters["date_to"]:
            lead_query_params["lead_date_to"] = lead_filters["date_to"]

        lead_current_url = request.build_absolute_uri(
            f"{dashboard_base_url}?{urllib.parse.urlencode(lead_query_params)}#module-workspace"
        )
        lead_export_params = dict(lead_query_params)
        lead_export_params["lead_export"] = "csv"
        lead_export_href = f"{dashboard_base_url}?{urllib.parse.urlencode(lead_export_params)}"

        share_parts = [f"{lead_filtered_count} lead records ready"]
        if lead_filters["query"]:
            share_parts.append(f"search {lead_filters['query']}")
        if lead_filters["source"]:
            share_parts.append(f"source {dict(lead_source_choices).get(lead_filters['source'], lead_filters['source'])}")
        if lead_filters["status"]:
            share_parts.append(f"status {dict(lead_status_choices).get(lead_filters['status'], lead_filters['status'])}")
        if lead_filters["stage"]:
            share_parts.append(f"stage {dict(lead_stage_choices).get(lead_filters['stage'], lead_filters['stage'])}")
        if lead_filters["date_from"] or lead_filters["date_to"]:
            share_parts.append(f"date {lead_filters['date_from'] or '-'} to {lead_filters['date_to'] or '-'}")
        share_text = " | ".join(share_parts) + f" | {lead_current_url}"
        lead_share_href = f"https://wa.me/?text={urllib.parse.quote(share_text)}"
        lead_email_share_href = (
            f"mailto:?subject={urllib.parse.quote('Lead List')}&body={urllib.parse.quote(share_text)}"
        )

        if request.GET.get("lead_export") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="lead-list.csv"'
            writer = csv.writer(response)
            writer.writerow(["Name", "Mobile", "Email", "Source", "Status", "Stage", "Agent", "City", "Budget"])
            for lead in lead_queryset:
                writer.writerow(
                    [
                        lead.name or "",
                        lead.mobile or "",
                        lead.email or "",
                        lead.get_source_display(),
                        lead.get_status_display(),
                        lead.get_stage_display(),
                        getattr(lead.assigned_agent, "name", ""),
                        lead.city or "",
                        lead.budget or "",
                    ]
                )
            return response

        lead_rows = list(lead_queryset)

    compact_dashboard_tabs = {"leads", "properties", "deals", "agents", "reports"}
    compact_dashboard_mode = active_dashboard_tab in compact_dashboard_tabs

    property_rows = list(crm_dashboard.get("recent_properties", []))
    property_filters = {"query": "", "status": "", "type": "", "listing_type": "", "date_range": "", "date_from": "", "date_to": ""}
    property_status_choices = ()
    property_type_choices = ()
    property_listing_type_choices = ()
    property_total_count = crm_dashboard.get("total_properties", 0)
    property_filtered_count = len(property_rows)
    property_reset_href = f"{dashboard_base_url}?tab=properties#module-workspace"
    property_export_href = f"{dashboard_base_url}?tab=properties&property_export=csv"
    property_share_href = "https://wa.me/?text=Property%20list"
    property_email_share_href = "mailto:?subject=Property%20List&body=Property%20list"
    property_current_url = request.build_absolute_uri(property_reset_href)
    if active_dashboard_tab == "properties":
        from leads.models import Property as REProperty

        property_queryset = _crm_property_queryset_for_user(user).order_by("-created_at", "-id")
        property_total_count = property_queryset.count()
        property_status_choices = REProperty.Status.choices
        property_type_choices = REProperty.Type.choices
        property_listing_type_choices = REProperty.ListingType.choices
        property_filters = {
            "query": (request.GET.get("property_query") or "").strip(),
            "status": (request.GET.get("property_status") or "").strip(),
            "type": (request.GET.get("property_type") or "").strip(),
            "listing_type": (request.GET.get("property_listing_type") or "").strip(),
            "date_range": (request.GET.get("property_date_range") or "").strip(),
            "date_from": (request.GET.get("property_date_from") or "").strip(),
            "date_to": (request.GET.get("property_date_to") or "").strip(),
        }
        property_preset_from, property_preset_to = _resolve_date_range_preset(property_filters["date_range"])
        if property_preset_from and property_preset_to:
            property_filters["date_from"] = property_preset_from
            property_filters["date_to"] = property_preset_to
        valid_statuses = {value for value, _label in property_status_choices}
        valid_types = {value for value, _label in property_type_choices}
        valid_listing_types = {value for value, _label in property_listing_type_choices}

        if property_filters["query"]:
            query = property_filters["query"]
            property_queryset = property_queryset.filter(
                Q(title__icontains=query)
                | Q(city__icontains=query)
                | Q(district__icontains=query)
                | Q(location__icontains=query)
                | Q(pin_code__icontains=query)
            )
        if property_filters["status"] in valid_statuses:
            property_queryset = property_queryset.filter(status=property_filters["status"])
        else:
            property_filters["status"] = ""
        if property_filters["type"] in valid_types:
            property_queryset = property_queryset.filter(property_type=property_filters["type"])
        else:
            property_filters["type"] = ""
        if property_filters["listing_type"] in valid_listing_types:
            property_queryset = property_queryset.filter(listing_type=property_filters["listing_type"])
        else:
            property_filters["listing_type"] = ""
        if property_filters["date_from"]:
            start_date = parse_date(property_filters["date_from"])
            if start_date:
                property_queryset = property_queryset.filter(created_at__date__gte=start_date)
            else:
                property_filters["date_from"] = ""
        if property_filters["date_to"]:
            end_date = parse_date(property_filters["date_to"])
            if end_date:
                property_queryset = property_queryset.filter(created_at__date__lte=end_date)
            else:
                property_filters["date_to"] = ""

        property_filtered_count = property_queryset.count()
        property_query_params = {"tab": "properties"}
        if property_filters["query"]:
            property_query_params["property_query"] = property_filters["query"]
        if property_filters["status"]:
            property_query_params["property_status"] = property_filters["status"]
        if property_filters["type"]:
            property_query_params["property_type"] = property_filters["type"]
        if property_filters["listing_type"]:
            property_query_params["property_listing_type"] = property_filters["listing_type"]
        if property_filters["date_range"]:
            property_query_params["property_date_range"] = property_filters["date_range"]
        if property_filters["date_from"]:
            property_query_params["property_date_from"] = property_filters["date_from"]
        if property_filters["date_to"]:
            property_query_params["property_date_to"] = property_filters["date_to"]
        property_current_url = request.build_absolute_uri(
            f"{dashboard_base_url}?{urllib.parse.urlencode(property_query_params)}#module-workspace"
        )
        property_export_params = dict(property_query_params)
        property_export_params["property_export"] = "csv"
        property_export_href = f"{dashboard_base_url}?{urllib.parse.urlencode(property_export_params)}"
        if property_filters["date_from"] or property_filters["date_to"]:
            property_share_text = (
                f"{property_filtered_count} properties ready | date {property_filters['date_from'] or '-'} to {property_filters['date_to'] or '-'} | {property_current_url}"
            )
        else:
            property_share_text = f"{property_filtered_count} properties ready | {property_current_url}"
        property_share_href = f"https://wa.me/?text={urllib.parse.quote(property_share_text)}"
        property_email_share_href = (
            f"mailto:?subject={urllib.parse.quote('Property List')}&body={urllib.parse.quote(property_share_text)}"
        )
        if request.GET.get("property_export") == "csv":
            return _build_csv_response(
                "property-list.csv",
                ["Title", "City", "Type", "Listing Type", "Status", "Agent", "Price", "Location"],
                [
                    [
                        prop.title or "",
                        prop.city or "",
                        prop.get_property_type_display(),
                        prop.get_listing_type_display(),
                        prop.get_status_display(),
                        getattr(prop.assigned_agent, "name", ""),
                        prop.price or "",
                        prop.location or "",
                    ]
                    for prop in property_queryset
                ],
            )
        property_rows = list(property_queryset)

    agent_rows = list(crm_dashboard.get("recent_agents", []))
    agent_filters = {"query": "", "approval": "", "specialization": "", "date_range": "", "date_from": "", "date_to": ""}
    agent_approval_choices = ()
    agent_specialization_choices = ()
    agent_total_count = len(agent_rows)
    agent_filtered_count = len(agent_rows)
    agent_reset_href = f"{dashboard_base_url}?tab=agents#module-workspace"
    agent_export_href = f"{dashboard_base_url}?tab=agents&agent_export=csv"
    agent_share_href = "https://wa.me/?text=Agent%20list"
    agent_email_share_href = "mailto:?subject=Agent%20List&body=Agent%20list"
    agent_current_url = request.build_absolute_uri(agent_reset_href)
    if active_dashboard_tab == "agents":
        from agents.models import Agent as CRMPageAgent

        agent_queryset = _crm_agent_queryset_for_user(user).order_by("-updated_at", "-id")
        agent_total_count = agent_queryset.count()
        agent_approval_choices = CRMPageAgent.ApprovalStatus.choices
        agent_specialization_choices = CRMPageAgent.Specialization.choices
        agent_filters = {
            "query": (request.GET.get("agent_query") or "").strip(),
            "approval": (request.GET.get("agent_approval") or "").strip(),
            "specialization": (request.GET.get("agent_specialization") or "").strip(),
            "date_range": (request.GET.get("agent_date_range") or "").strip(),
            "date_from": (request.GET.get("agent_date_from") or "").strip(),
            "date_to": (request.GET.get("agent_date_to") or "").strip(),
        }
        agent_preset_from, agent_preset_to = _resolve_date_range_preset(agent_filters["date_range"])
        if agent_preset_from and agent_preset_to:
            agent_filters["date_from"] = agent_preset_from
            agent_filters["date_to"] = agent_preset_to
        valid_approvals = {value for value, _label in agent_approval_choices}
        valid_specializations = {value for value, _label in agent_specialization_choices}

        if agent_filters["query"]:
            query = agent_filters["query"]
            agent_queryset = agent_queryset.filter(
                Q(name__icontains=query)
                | Q(phone__icontains=query)
                | Q(city__icontains=query)
                | Q(district__icontains=query)
                | Q(pin_code__icontains=query)
                | Q(license_number__icontains=query)
            )
        if agent_filters["approval"] in valid_approvals:
            agent_queryset = agent_queryset.filter(approval_status=agent_filters["approval"])
        else:
            agent_filters["approval"] = ""
        if agent_filters["specialization"] in valid_specializations:
            agent_queryset = agent_queryset.filter(specialization=agent_filters["specialization"])
        else:
            agent_filters["specialization"] = ""
        if agent_filters["date_from"]:
            start_date = parse_date(agent_filters["date_from"])
            if start_date:
                agent_queryset = agent_queryset.filter(created_at__date__gte=start_date)
            else:
                agent_filters["date_from"] = ""
        if agent_filters["date_to"]:
            end_date = parse_date(agent_filters["date_to"])
            if end_date:
                agent_queryset = agent_queryset.filter(created_at__date__lte=end_date)
            else:
                agent_filters["date_to"] = ""

        agent_filtered_count = agent_queryset.count()
        agent_query_params = {"tab": "agents"}
        if agent_filters["query"]:
            agent_query_params["agent_query"] = agent_filters["query"]
        if agent_filters["approval"]:
            agent_query_params["agent_approval"] = agent_filters["approval"]
        if agent_filters["specialization"]:
            agent_query_params["agent_specialization"] = agent_filters["specialization"]
        if agent_filters["date_range"]:
            agent_query_params["agent_date_range"] = agent_filters["date_range"]
        if agent_filters["date_from"]:
            agent_query_params["agent_date_from"] = agent_filters["date_from"]
        if agent_filters["date_to"]:
            agent_query_params["agent_date_to"] = agent_filters["date_to"]
        agent_current_url = request.build_absolute_uri(
            f"{dashboard_base_url}?{urllib.parse.urlencode(agent_query_params)}#module-workspace"
        )
        agent_export_params = dict(agent_query_params)
        agent_export_params["agent_export"] = "csv"
        agent_export_href = f"{dashboard_base_url}?{urllib.parse.urlencode(agent_export_params)}"
        if agent_filters["date_from"] or agent_filters["date_to"]:
            agent_share_text = (
                f"{agent_filtered_count} agents ready | date {agent_filters['date_from'] or '-'} to {agent_filters['date_to'] or '-'} | {agent_current_url}"
            )
        else:
            agent_share_text = f"{agent_filtered_count} agents ready | {agent_current_url}"
        agent_share_href = f"https://wa.me/?text={urllib.parse.quote(agent_share_text)}"
        agent_email_share_href = (
            f"mailto:?subject={urllib.parse.quote('Agent List')}&body={urllib.parse.quote(agent_share_text)}"
        )
        if request.GET.get("agent_export") == "csv":
            return _build_csv_response(
                "agent-list.csv",
                ["Name", "Phone", "City", "Approval", "Specialization", "Score", "Commission"],
                [
                    [
                        agent.name or "",
                        agent.phone or "",
                        agent.city or "",
                        agent.get_approval_status_display(),
                        agent.get_specialization_display(),
                        agent.performance_score or 0,
                        agent.commission_rate or "",
                    ]
                    for agent in agent_queryset
                ],
            )
        agent_rows = list(agent_queryset)

    deal_rows = list(crm_dashboard.get("recent_deals", []))
    deal_filters = {"query": "", "status": "", "stage": "", "date_range": "", "date_from": "", "date_to": ""}
    deal_status_choices = ()
    deal_stage_choices = ()
    deal_total_count = len(deal_rows)
    deal_filtered_count = len(deal_rows)
    deal_reset_href = f"{dashboard_base_url}?tab=deals#module-workspace"
    deal_export_href = f"{dashboard_base_url}?tab=deals&deal_export=csv"
    deal_share_href = "https://wa.me/?text=Deal%20list"
    deal_email_share_href = "mailto:?subject=Deal%20List&body=Deal%20list"
    deal_current_url = request.build_absolute_uri(deal_reset_href)
    if active_dashboard_tab == "deals":
        from deals.models import Deal as CRMPageDeal

        deal_queryset = _crm_deal_queryset_for_user(user).order_by("-updated_at", "-id")
        deal_total_count = deal_queryset.count()
        deal_status_choices = CRMPageDeal.Status.choices
        deal_stage_choices = CRMPageDeal.Stage.choices
        deal_filters = {
            "query": (request.GET.get("deal_query") or "").strip(),
            "status": (request.GET.get("deal_status") or "").strip(),
            "stage": (request.GET.get("deal_stage") or "").strip(),
            "date_range": (request.GET.get("deal_date_range") or "").strip(),
            "date_from": (request.GET.get("deal_date_from") or "").strip(),
            "date_to": (request.GET.get("deal_date_to") or "").strip(),
        }
        deal_preset_from, deal_preset_to = _resolve_date_range_preset(deal_filters["date_range"])
        if deal_preset_from and deal_preset_to:
            deal_filters["date_from"] = deal_preset_from
            deal_filters["date_to"] = deal_preset_to
        valid_statuses = {value for value, _label in deal_status_choices}
        valid_stages = {value for value, _label in deal_stage_choices}

        if deal_filters["query"]:
            query = deal_filters["query"]
            deal_queryset = deal_queryset.filter(
                Q(lead__name__icontains=query)
                | Q(lead__mobile__icontains=query)
                | Q(property__title__icontains=query)
                | Q(agent__name__icontains=query)
                | Q(customer__user__email__icontains=query)
            )
        if deal_filters["status"] in valid_statuses:
            deal_queryset = deal_queryset.filter(status=deal_filters["status"])
        else:
            deal_filters["status"] = ""
        if deal_filters["stage"] in valid_stages:
            deal_queryset = deal_queryset.filter(stage=deal_filters["stage"])
        else:
            deal_filters["stage"] = ""
        if deal_filters["date_from"]:
            start_date = parse_date(deal_filters["date_from"])
            if start_date:
                deal_queryset = deal_queryset.filter(created_at__date__gte=start_date)
            else:
                deal_filters["date_from"] = ""
        if deal_filters["date_to"]:
            end_date = parse_date(deal_filters["date_to"])
            if end_date:
                deal_queryset = deal_queryset.filter(created_at__date__lte=end_date)
            else:
                deal_filters["date_to"] = ""

        deal_filtered_count = deal_queryset.count()
        deal_query_params = {"tab": "deals"}
        if deal_filters["query"]:
            deal_query_params["deal_query"] = deal_filters["query"]
        if deal_filters["status"]:
            deal_query_params["deal_status"] = deal_filters["status"]
        if deal_filters["stage"]:
            deal_query_params["deal_stage"] = deal_filters["stage"]
        if deal_filters["date_range"]:
            deal_query_params["deal_date_range"] = deal_filters["date_range"]
        if deal_filters["date_from"]:
            deal_query_params["deal_date_from"] = deal_filters["date_from"]
        if deal_filters["date_to"]:
            deal_query_params["deal_date_to"] = deal_filters["date_to"]
        deal_current_url = request.build_absolute_uri(
            f"{dashboard_base_url}?{urllib.parse.urlencode(deal_query_params)}#module-workspace"
        )
        deal_export_params = dict(deal_query_params)
        deal_export_params["deal_export"] = "csv"
        deal_export_href = f"{dashboard_base_url}?{urllib.parse.urlencode(deal_export_params)}"
        if deal_filters["date_from"] or deal_filters["date_to"]:
            deal_share_text = (
                f"{deal_filtered_count} deals ready | date {deal_filters['date_from'] or '-'} to {deal_filters['date_to'] or '-'} | {deal_current_url}"
            )
        else:
            deal_share_text = f"{deal_filtered_count} deals ready | {deal_current_url}"
        deal_share_href = f"https://wa.me/?text={urllib.parse.quote(deal_share_text)}"
        deal_email_share_href = (
            f"mailto:?subject={urllib.parse.quote('Deal List')}&body={urllib.parse.quote(deal_share_text)}"
        )
        if request.GET.get("deal_export") == "csv":
            return _build_csv_response(
                "deal-list.csv",
                ["Lead", "Property", "Agent", "Amount", "Commission", "Status", "Stage"],
                [
                    [
                        deal.lead.name if deal.lead_id else f"Deal #{deal.id}",
                        getattr(deal.property, "title", ""),
                        getattr(deal.agent, "name", ""),
                        deal.deal_amount or "",
                        deal.commission_amount or "",
                        deal.get_status_display(),
                        deal.get_stage_display(),
                    ]
                    for deal in deal_queryset
                ],
            )
        deal_rows = list(deal_queryset)

    report_rows = list(crm_dashboard.get("recent_conversations", []))
    report_filters = {"query": "", "activity_type": "", "date_range": "", "date_from": "", "date_to": ""}
    report_type_choices = ()
    report_total_count = len(report_rows)
    report_filtered_count = len(report_rows)
    report_reset_href = f"{dashboard_base_url}?tab=reports#module-workspace"
    report_export_href = f"{dashboard_base_url}?tab=reports&report_export=csv"
    report_share_href = "https://wa.me/?text=Report%20list"
    report_email_share_href = "mailto:?subject=Report%20List&body=Report%20list"
    report_current_url = request.build_absolute_uri(report_reset_href)
    if active_dashboard_tab == "reports":
        report_queryset = _crm_activity_queryset_for_user(user).order_by("-created_at", "-id")
        report_total_count = report_queryset.count()
        known_types = ["note", "whatsapp", "email", "sms", "call", "facebook_messenger", "instagram_dm"]
        found_types = list(report_queryset.values_list("activity_type", flat=True).distinct())
        ordered_types = []
        for item in known_types + found_types:
            if item and item not in ordered_types:
                ordered_types.append(item)
        report_type_choices = [(value, value.replace("_", " ").title()) for value in ordered_types]
        report_filters = {
            "query": (request.GET.get("report_query") or "").strip(),
            "activity_type": (request.GET.get("report_type") or "").strip(),
            "date_range": (request.GET.get("report_date_range") or "").strip(),
            "date_from": (request.GET.get("report_date_from") or "").strip(),
            "date_to": (request.GET.get("report_date_to") or "").strip(),
        }
        report_preset_from, report_preset_to = _resolve_date_range_preset(report_filters["date_range"])
        if report_preset_from and report_preset_to:
            report_filters["date_from"] = report_preset_from
            report_filters["date_to"] = report_preset_to
        valid_types = {value for value, _label in report_type_choices}

        if report_filters["query"]:
            query = report_filters["query"]
            report_queryset = report_queryset.filter(
                Q(lead__name__icontains=query)
                | Q(lead__mobile__icontains=query)
                | Q(note__icontains=query)
                | Q(actor__email__icontains=query)
                | Q(actor__username__icontains=query)
                | Q(activity_type__icontains=query)
            )
        if report_filters["activity_type"] in valid_types:
            report_queryset = report_queryset.filter(activity_type=report_filters["activity_type"])
        else:
            report_filters["activity_type"] = ""
        if report_filters["date_from"]:
            start_date = parse_date(report_filters["date_from"])
            if start_date:
                report_queryset = report_queryset.filter(created_at__date__gte=start_date)
            else:
                report_filters["date_from"] = ""
        if report_filters["date_to"]:
            end_date = parse_date(report_filters["date_to"])
            if end_date:
                report_queryset = report_queryset.filter(created_at__date__lte=end_date)
            else:
                report_filters["date_to"] = ""

        report_filtered_count = report_queryset.count()
        report_query_params = {"tab": "reports"}
        if report_filters["query"]:
            report_query_params["report_query"] = report_filters["query"]
        if report_filters["activity_type"]:
            report_query_params["report_type"] = report_filters["activity_type"]
        if report_filters["date_range"]:
            report_query_params["report_date_range"] = report_filters["date_range"]
        if report_filters["date_from"]:
            report_query_params["report_date_from"] = report_filters["date_from"]
        if report_filters["date_to"]:
            report_query_params["report_date_to"] = report_filters["date_to"]
        report_current_url = request.build_absolute_uri(
            f"{dashboard_base_url}?{urllib.parse.urlencode(report_query_params)}#module-workspace"
        )
        report_export_params = dict(report_query_params)
        report_export_params["report_export"] = "csv"
        report_export_href = f"{dashboard_base_url}?{urllib.parse.urlencode(report_export_params)}"
        report_share_text = f"{report_filtered_count} report rows ready | {report_current_url}"
        report_share_href = f"https://wa.me/?text={urllib.parse.quote(report_share_text)}"
        report_email_share_href = (
            f"mailto:?subject={urllib.parse.quote('Report List')}&body={urllib.parse.quote(report_share_text)}"
        )
        if request.GET.get("report_export") == "csv":
            return _build_csv_response(
                "report-list.csv",
                ["Lead", "Activity", "Actor", "Created", "Note"],
                [
                    [
                        activity.lead.name if activity.lead_id else "",
                        activity.activity_type.replace("_", " ").title(),
                        getattr(activity.actor, "email", "") or getattr(activity.actor, "username", "") or "System",
                        activity.created_at.strftime("%Y-%m-%d %H:%M"),
                        activity.note or "",
                    ]
                    for activity in report_queryset
                ],
            )
        report_rows = list(report_queryset)

    wallet_dashboard = _wallet_workspace_payload(user)
    dashboard_primary_stats = [
        {"label": "Total Leads", "value": crm_dashboard["total_leads"], "icon": "bi-people", "tone": "crm"},
        {"label": "Auto Assigned", "value": crm_dashboard["auto_assigned_count"], "icon": "bi-person-check", "tone": "market"},
        {"label": "Follow Up Due", "value": crm_dashboard["followups_due"], "icon": "bi-bell", "tone": "info"},
        {"label": "Converted", "value": crm_dashboard["converted_leads"], "icon": "bi-arrow-repeat", "tone": "wallet"},
        {"label": "Open Deals", "value": crm_dashboard["open_deals"], "icon": "bi-kanban", "tone": "loan"},
        {"label": "Pending Payouts", "value": crm_dashboard["pending_payout_count"], "icon": "bi-cash-stack", "tone": "loan"},
        {"label": "Customers", "value": crm_dashboard["total_customers"], "icon": "bi-person-vcard", "tone": "scheme"},
        {"label": "Conversations", "value": crm_dashboard["active_conversations"], "icon": "bi-chat-dots", "tone": "content"},
    ]
    dashboard_module_tiles = [
        {"label": "Capture", "value": crm_dashboard["import_batch_count"], "icon": "bi-cloud-arrow-down-fill", "accent": "market", "href": f"{dashboard_base_url}?tab=leads#module-workspace", "feature_key": "crm.leads"},
        {"label": "Assignment", "value": crm_dashboard["auto_assigned_count"], "icon": "bi-diagram-3-fill", "accent": "crm", "href": f"{dashboard_base_url}?tab=agents#module-workspace", "feature_key": "crm.agents"},
        {"label": "Pipeline", "value": crm_dashboard["followups_due"], "icon": "bi-kanban-fill", "accent": "loan", "href": f"{dashboard_base_url}?tab=reports#module-workspace", "feature_key": "crm.reports"},
        {"label": "Deals", "value": crm_dashboard["open_deals"], "icon": "bi-briefcase-fill", "accent": "verify", "href": f"{dashboard_base_url}?tab=deals#module-workspace", "feature_key": "crm.deals"},
        {"label": "Commission", "value": f"Rs {crm_dashboard['total_commission']}", "icon": "bi-cash-coin", "accent": "scheme", "href": reverse("accounts:wallet_workspace"), "feature_key": "crm.wallet"},
        {"label": "Customers", "value": crm_dashboard["total_customers"], "icon": "bi-person-heart", "accent": "content", "href": f"{dashboard_base_url}?tab=deals#module-workspace", "feature_key": "crm.deals"},
        {"label": "Duplicates", "value": crm_dashboard["duplicate_leads"], "icon": "bi-copy", "accent": "intel", "href": f"{dashboard_base_url}?tab=leads#module-workspace", "feature_key": "crm.leads"},
        {"label": "Nearby", "value": crm_dashboard["nearby_property_count"], "icon": "bi-geo-alt-fill", "accent": "intel", "href": f"{dashboard_base_url}?tab=properties#module-workspace", "feature_key": "crm.properties"},
    ]
    dashboard_module_tiles = [tile for tile in dashboard_module_tiles if not tile.get("feature_key") or user_has_feature(user, tile["feature_key"])]
    dashboard_flow_steps = [
        {"label": "Capture", "icon": "bi-cloud-arrow-down"},
        {"label": "Score", "icon": "bi-lightning-charge"},
        {"label": "Assign", "icon": "bi-person-check"},
        {"label": "Contact", "icon": "bi-chat-dots"},
        {"label": "Visit", "icon": "bi-calendar2-check"},
        {"label": "Convert", "icon": "bi-arrow-repeat"},
        {"label": "Payout", "icon": "bi-cash-stack"},
    ]
    dashboard_signal_bars = [
        {"label": "Lead Load", "value": crm_dashboard["total_leads"], "max": max(crm_dashboard["total_leads"], 10), "tone": "crm"},
        {"label": "Assignments", "value": crm_dashboard["auto_assigned_count"], "max": max(crm_dashboard["total_leads"], 10), "tone": "market"},
        {"label": "Follow Up Due", "value": crm_dashboard["followups_due"], "max": max(crm_dashboard["total_leads"], 10), "tone": "loan"},
        {"label": "Converted", "value": crm_dashboard["converted_leads"], "max": max(crm_dashboard["total_leads"], 10), "tone": "scheme"},
    ]
    if workspace_role == "admin":
        dashboard_quick_actions = [
            {"label": "Lead Ops", "href": f"{dashboard_base_url}?tab=leads#module-workspace", "icon": "bi-diagram-3", "feature_key": "crm.leads"},
            {"label": "Assignments", "href": f"{dashboard_base_url}?tab=agents#module-workspace", "icon": "bi-person-check", "feature_key": "crm.agents"},
            {"label": "Payouts", "href": f"{dashboard_base_url}?tab=deals#module-workspace", "icon": "bi-cash-stack", "feature_key": "crm.deals"},
            {"label": "Wallet", "href": reverse("accounts:wallet_workspace"), "icon": "bi-wallet2", "feature_key": "crm.wallet"},
            {"label": "Superadmin", "href": "/superadmin/", "icon": "bi-speedometer2"},
        ]
    elif workspace_role == "agent":
        dashboard_quick_actions = [
            {"label": "My Leads", "href": f"{dashboard_base_url}?tab=leads#module-workspace", "icon": "bi-people", "feature_key": "crm.leads"},
            {"label": "Timeline", "href": reverse("accounts:reports_workspace"), "icon": "bi-chat-dots", "feature_key": "crm.reports"},
            {"label": "Deals", "href": f"{dashboard_base_url}?tab=deals#module-workspace", "icon": "bi-kanban", "feature_key": "crm.deals"},
            {"label": "Wallet", "href": reverse("accounts:wallet_workspace"), "icon": "bi-wallet2", "feature_key": "crm.wallet"},
            {"label": "Profile", "href": reverse("accounts:edit_profile"), "icon": "bi-person-circle"},
        ]
    else:
        dashboard_quick_actions = [
            {"label": "Status", "href": f"{dashboard_base_url}?tab=dashboard#module-workspace", "icon": "bi-activity"},
            {"label": "Nearby", "href": f"{dashboard_base_url}?tab=properties#module-workspace", "icon": "bi-house-door", "feature_key": "crm.properties"},
            {"label": "Assigned Agent", "href": f"{dashboard_base_url}?tab=agents#module-workspace", "icon": "bi-person-badge", "feature_key": "crm.agents"},
            {"label": "Wallet", "href": reverse("accounts:wallet_workspace"), "icon": "bi-wallet2", "feature_key": "crm.wallet"},
            {"label": "Profile", "href": reverse("accounts:edit_profile"), "icon": "bi-person-circle"},
        ]
    dashboard_quick_actions = [action for action in dashboard_quick_actions if not action.get("feature_key") or user_has_feature(user, action["feature_key"])]
    admin_control_summary = {}
    admin_control_tiles = []
    admin_intake_tiles = []
    admin_tech_tiles = []
    admin_crm_tiles = []
    admin_lead_source_tiles = []
    admin_source_choices = []
    admin_recent_leads = []
    admin_recent_agents = []
    admin_recent_customers = []
    admin_recent_import_batches = []
    admin_import_status_counts = {}
    admin_failed_import_batches = []
    admin_duplicate_leads = []
    admin_failed_rows_total = 0
    admin_duplicate_leads_count = 0
    admin_unassigned_leads = []
    admin_source_kind_choices = []
    admin_demo_lead_rows = []
    admin_dashboard_action_url = reverse("accounts:admin_dashboard_action")
    admin_payload_cache_key = None
    admin_payload = None
    if workspace_role == "admin":
        admin_payload_cache_key = (
            f"accounts_dashboard_admin_payload:{getattr(user, 'pk', 'anon')}:"
            f"{getattr(company, 'pk', 'none')}:{active_dashboard_tab}"
        )
        if not force_refresh:
            admin_payload = cache.get(admin_payload_cache_key)
            if admin_payload:
                admin_control_summary = admin_payload.get("admin_control_summary", admin_control_summary)
                admin_control_tiles = admin_payload.get("admin_control_tiles", admin_control_tiles)
                admin_intake_tiles = admin_payload.get("admin_intake_tiles", admin_intake_tiles)
                admin_tech_tiles = admin_payload.get("admin_tech_tiles", admin_tech_tiles)
                admin_crm_tiles = admin_payload.get("admin_crm_tiles", admin_crm_tiles)
                admin_lead_source_tiles = admin_payload.get("admin_lead_source_tiles", admin_lead_source_tiles)
                admin_source_choices = admin_payload.get("admin_source_choices", admin_source_choices)
                admin_recent_leads = admin_payload.get("admin_recent_leads", admin_recent_leads)
                admin_recent_agents = admin_payload.get("admin_recent_agents", admin_recent_agents)
                admin_recent_customers = admin_payload.get("admin_recent_customers", admin_recent_customers)
                admin_recent_import_batches = admin_payload.get("admin_recent_import_batches", admin_recent_import_batches)
                admin_import_status_counts = admin_payload.get("admin_import_status_counts", admin_import_status_counts)
                admin_failed_import_batches = admin_payload.get("admin_failed_import_batches", admin_failed_import_batches)
                admin_duplicate_leads = admin_payload.get("admin_duplicate_leads", admin_duplicate_leads)
                admin_failed_rows_total = admin_payload.get("admin_failed_rows_total", admin_failed_rows_total)
                admin_duplicate_leads_count = admin_payload.get("admin_duplicate_leads_count", admin_duplicate_leads_count)
                admin_unassigned_leads = admin_payload.get("admin_unassigned_leads", admin_unassigned_leads)
                admin_source_kind_choices = admin_payload.get("admin_source_kind_choices", admin_source_kind_choices)
                admin_demo_lead_rows = admin_payload.get("admin_demo_lead_rows", admin_demo_lead_rows)
    if workspace_role == "admin" and admin_payload is None:
        try:
            from customers.models import Customer
            from leads.models import Lead, LeadImportBatch, LeadSource
            from agents.models import Agent as CRMAdminAgent

            admin_control_summary = {
                "users": User.objects.count(),
                "agents": CRMAdminAgent.objects.count(),
                "customers": Customer.objects.count(),
                "leads": crm_dashboard.get("total_leads", Lead.objects.count()),
                "lead_sources": LeadSource.objects.count(),
                "import_batches": LeadImportBatch.objects.count(),
                "overdue_leads": Lead.objects.filter(is_overdue=True).count(),
                "unassigned_leads": crm_dashboard.get("unassigned_leads", 0),
                "active_agents": crm_dashboard.get("active_agents", 0),
            }
            social_source_count = LeadSource.objects.filter(
                kind__in=[
                    LeadSource.Kind.FACEBOOK_ADS,
                    LeadSource.Kind.INSTAGRAM_ADS,
                    LeadSource.Kind.WEBSITE_FORM,
                ]
            ).count()
            api_source_count = LeadSource.objects.filter(kind__in=[LeadSource.Kind.API, LeadSource.Kind.WEBHOOK]).count()
            bulk_source_count = LeadSource.objects.filter(kind=LeadSource.Kind.CSV).count()
            scrape_source_count = LeadSource.objects.filter(kind=LeadSource.Kind.WEB_SCRAPE).count()
            admin_control_tiles = [
                {
                    "label": "Users",
                    "value": "Create / Edit / Delete",
                    "href": reverse("admin:accounts_user_changelist"),
                    "accent": "crm",
                },
                {
                    "label": "Agents",
                    "value": f"{admin_control_summary['agents']} Records",
                    "href": reverse("admin:agents_agent_changelist"),
                    "accent": "market",
                },
                {
                    "label": "Customers",
                    "value": f"{admin_control_summary['customers']} Records",
                    "href": reverse("admin:customers_customer_changelist"),
                    "accent": "content",
                },
                {
                    "label": "Leads",
                    "value": f"{admin_control_summary['leads']} Live",
                    "href": f"{dashboard_base_url}?tab=leads#module-workspace",
                    "accent": "loan",
                },
                {
                    "label": "Lead Sources",
                    "value": "Social / API / Web Scrape",
                    "href": reverse("admin:leads_leadsource_changelist"),
                    "accent": "intel",
                },
                {
                    "label": "Import Batches",
                    "value": f"{admin_control_summary['import_batches']} Jobs",
                    "href": reverse("admin:leads_leadimportbatch_changelist"),
                    "accent": "scheme",
                },
                {
                    "label": "Reports",
                    "value": "Monitor / Audit / Assign",
                    "href": f"{dashboard_base_url}?tab=reports#module-workspace",
                    "accent": "verify",
                },
                {
                    "label": "Feature Tower",
                    "value": "Plan / User / Global Control",
                    "href": reverse("core_settings:feature_control_tower"),
                    "accent": "wallet",
                },
            ]
            admin_intake_tiles = [
                {
                    "label": "Social Intake",
                    "value": f"{social_source_count} Sources",
                    "href": reverse("admin:leads_leadsource_changelist"),
                    "accent": "content",
                },
                {
                    "label": "Bulk CSV",
                    "value": f"{bulk_source_count} Sources",
                    "href": reverse("admin:leads_leadimportbatch_changelist"),
                    "accent": "scheme",
                },
                {
                    "label": "API Capture",
                    "value": f"{api_source_count} Sources",
                    "href": "/api/docs/",
                    "accent": "crm",
                },
                {
                    "label": "Web Scraping",
                    "value": f"{scrape_source_count} Sources",
                    "href": reverse("admin:leads_leadsource_changelist"),
                    "accent": "intel",
                },
                {
                    "label": "Assignments",
                    "value": "Bulk / Manual / Auto",
                    "href": f"{dashboard_base_url}?tab=agents#module-workspace",
                    "accent": "market",
                },
                {
                    "label": "Monitoring",
                    "value": "Overdue / Unassigned",
                    "href": f"{dashboard_base_url}?tab=reports#module-workspace",
                    "accent": "loan",
                },
            ]
            admin_tech_tiles = [
                {
                    "label": "WhatsApp Automation",
                    "value": "Setup + Webhooks",
                    "href": reverse("whatsapp_setup_wizard_alias"),
                    "accent": "content",
                },
                {
                    "label": "Email + SMS",
                    "value": "Follow-ups + Alerts",
                    "href": "/api/v1/communication/",
                    "accent": "info",
                },
                {
                    "label": "API Capture",
                    "value": f"{api_source_count} Sources",
                    "href": "/api/docs/",
                    "accent": "crm",
                },
                {
                    "label": "Bulk CSV",
                    "value": f"{bulk_source_count} Sources",
                    "href": reverse("admin:leads_leadimportbatch_changelist"),
                    "accent": "scheme",
                },
                {
                    "label": "Web Scraping",
                    "value": f"{scrape_source_count} Sources",
                    "href": reverse("admin:leads_leadsource_changelist"),
                    "accent": "intel",
                },
                {
                    "label": "Social Media",
                    "value": f"{social_source_count} Sources",
                    "href": reverse("admin:leads_leadsource_changelist"),
                    "accent": "market",
                },
            ]
            admin_crm_tiles = [
                {
                    "label": "Geo Auto Assign",
                    "value": "Nearest Agent",
                    "href": f"{dashboard_base_url}?tab=leads#module-workspace",
                    "accent": "crm",
                },
                {
                    "label": "Photo to Lead",
                    "value": "OCR Intake",
                    "href": f"{dashboard_base_url}?tab=leads#module-workspace",
                    "accent": "content",
                },
                {
                    "label": "Lead Lock",
                    "value": "Secure Access",
                    "href": f"{dashboard_base_url}?tab=reports#system-signals",
                    "accent": "verify",
                },
                {
                    "label": "Invoice + Payment",
                    "value": "Auto Billing",
                    "href": "/billing/dashboard/",
                    "accent": "wallet",
                },
                {
                    "label": "Agent Leaderboard",
                    "value": "Gamification",
                    "href": f"{dashboard_base_url}?tab=reports#system-signals",
                    "accent": "scheme",
                },
                {
                    "label": "Agent Stats",
                    "value": "Performance",
                    "href": f"{dashboard_base_url}?tab=agents#module-workspace",
                    "accent": "loan",
                },
            ]
            lead_source_count_map = {}
            lead_source_qs = Lead.objects.all()
            if company is not None:
                lead_source_qs = lead_source_qs.filter(company=company)
            for row in lead_source_qs.values("source").annotate(total=Count("id")):
                lead_source_count_map[row["source"]] = row["total"]
            source_accent_map = {
                Lead.Source.WHATSAPP: "content",
                Lead.Source.WHATSAPP_CHATBOT: "content",
                Lead.Source.SMS: "info",
                Lead.Source.EMAIL: "info",
                Lead.Source.FACEBOOK: "market",
                Lead.Source.FACEBOOK_ADS: "market",
                Lead.Source.INSTAGRAM: "market",
                Lead.Source.INSTAGRAM_ADS: "market",
                Lead.Source.GOOGLE: "crm",
                Lead.Source.GOOGLE_ADS: "crm",
                Lead.Source.TELEGRAM: "wallet",
                Lead.Source.YOUTUBE: "scheme",
                Lead.Source.API: "crm",
                Lead.Source.WEBSITE: "loan",
                Lead.Source.LANDING_PAGE: "loan",
                Lead.Source.MISSED_CALL: "verify",
                Lead.Source.REFERRAL: "scheme",
                Lead.Source.MANUAL: "neutral",
            }
            admin_lead_source_tiles = [
                {
                    "label": label,
                    "value": f"{lead_source_count_map.get(value, 0)} Leads",
                    "href": f"{dashboard_base_url}?tab=leads&lead_source={value}#module-workspace",
                    "accent": source_accent_map.get(value, "crm"),
                }
                for value, label in Lead.Source.choices
            ]
            admin_source_choices = list(Lead.Source.choices)
            admin_recent_leads = list(crm_dashboard.get("recent_leads", []))
            admin_recent_agents = list(crm_dashboard.get("recent_agents", []))
            admin_recent_customers_qs = Customer.objects.select_related("user", "assigned_agent")
            if company is not None:
                admin_recent_customers_qs = admin_recent_customers_qs.filter(company=company)
            admin_recent_customers = list(admin_recent_customers_qs.order_by("-updated_at", "-id")[:10])
            admin_recent_import_batches_qs = LeadImportBatch.objects.select_related("source", "created_by")
            if company is not None:
                admin_recent_import_batches_qs = admin_recent_import_batches_qs.filter(company=company)
            admin_recent_import_batches = list(admin_recent_import_batches_qs.order_by("-created_at", "-id")[:8])
            admin_import_status_counts = {
                row["status"]: row["total"]
                for row in admin_recent_import_batches_qs.values("status").annotate(total=Count("id"))
            }
            admin_failed_rows_total = admin_recent_import_batches_qs.aggregate(total=Sum("failed_rows"))["total"] or 0
            failed_batch_rows = list(
                admin_recent_import_batches_qs.filter(failed_rows__gt=0).order_by("-failed_rows", "-updated_at", "-id")[:5]
            )
            admin_failed_import_batches = []
            for batch in failed_batch_rows:
                errors = batch.error_report or []
                preview = []
                if isinstance(errors, list):
                    for item in errors[:3]:
                        if isinstance(item, dict):
                            preview.append(
                                item.get("message")
                                or item.get("error")
                                or item.get("row")
                                or item.get("detail")
                                or str(item)
                            )
                        else:
                            preview.append(str(item))
                admin_failed_import_batches.append(
                    {
                        "id": batch.id,
                        "label": batch.source_name or getattr(batch.source, "name", "") or f"Batch #{batch.id}",
                        "import_type": batch.get_import_type_display(),
                        "status": batch.get_status_display(),
                        "failed_rows": batch.failed_rows,
                        "created_leads": batch.created_leads,
                        "error_count": len(errors) if isinstance(errors, list) else 0,
                        "errors_preview": preview,
                    }
                )
            admin_duplicate_leads_qs = Lead.objects.filter(is_duplicate=True)
            if company is not None:
                admin_duplicate_leads_qs = admin_duplicate_leads_qs.filter(company=company)
            admin_duplicate_leads_count = admin_duplicate_leads_qs.count()
            admin_duplicate_leads = list(
                admin_duplicate_leads_qs.select_related("assigned_agent", "duplicate_of")
                .order_by("-created_at", "-id")[:8]
            )
            admin_unassigned_leads_qs = Lead.objects.select_related("assigned_agent", "source_config").filter(
                assigned_agent__isnull=True
            )
            if company is not None:
                admin_unassigned_leads_qs = admin_unassigned_leads_qs.filter(company=company)
            admin_unassigned_leads = list(admin_unassigned_leads_qs.order_by("-created_at", "-id")[:10])
            admin_source_kind_choices = list(LeadSource.Kind.choices)
            admin_demo_lead_rows = [
                {
                    "name": "Rahul Sharma",
                    "phone": "9000001001",
                    "email": "rahul@example.com",
                    "source_value": Lead.Source.MANUAL,
                    "source_label": "Manual",
                    "city": "Lucknow",
                    "note": "Manual entry sample",
                },
                {
                    "name": "Pooja Verma",
                    "phone": "9000001002",
                    "email": "pooja@example.com",
                    "source_value": Lead.Source.FACEBOOK_ADS,
                    "source_label": "Facebook Ads",
                    "city": "Noida",
                    "note": "Facebook lead sample",
                },
                {
                    "name": "Amit Khan",
                    "phone": "9000001003",
                    "email": "amit@example.com",
                    "source_value": Lead.Source.API,
                    "source_label": "API",
                    "city": "Kanpur",
                    "note": "API feed sample",
                },
                {
                    "name": "Neha Gupta",
                    "phone": "9000001004",
                    "email": "neha@example.com",
                    "source_value": Lead.Source.WEBSITE,
                    "source_label": "Website",
                    "city": "Gurugram",
                    "note": "Website sample",
                },
                {
                    "name": "Demo Scrape",
                    "phone": "9000001005",
                    "email": "scrape@example.com",
                    "source_value": Lead.Source.WEBSITE,
                    "source_label": "Web Scrape",
                    "city": "Delhi",
                    "note": "Web scrape sample",
                },
            ]
            admin_payload = {
                "admin_control_summary": admin_control_summary,
                "admin_control_tiles": admin_control_tiles,
                "admin_intake_tiles": admin_intake_tiles,
                "admin_tech_tiles": admin_tech_tiles,
                "admin_crm_tiles": admin_crm_tiles,
                "admin_lead_source_tiles": admin_lead_source_tiles,
                "admin_source_choices": admin_source_choices,
                "admin_recent_leads": admin_recent_leads,
                "admin_recent_agents": admin_recent_agents,
                "admin_recent_customers": admin_recent_customers,
                "admin_recent_import_batches": admin_recent_import_batches,
                "admin_import_status_counts": admin_import_status_counts,
                "admin_failed_import_batches": admin_failed_import_batches,
                "admin_duplicate_leads": admin_duplicate_leads,
                "admin_failed_rows_total": admin_failed_rows_total,
                "admin_duplicate_leads_count": admin_duplicate_leads_count,
                "admin_unassigned_leads": admin_unassigned_leads,
                "admin_source_kind_choices": admin_source_kind_choices,
                "admin_demo_lead_rows": admin_demo_lead_rows,
            }
            if admin_payload_cache_key:
                cache.set(admin_payload_cache_key, admin_payload, 45)
        except Exception:
            admin_control_summary = {
                "users": 0,
                "agents": 0,
                "customers": 0,
                "leads": 0,
                "lead_sources": 0,
                "import_batches": 0,
                "overdue_leads": 0,
                "unassigned_leads": 0,
                "active_agents": 0,
            }
            admin_control_tiles = []
            admin_intake_tiles = []
            admin_tech_tiles = []
            admin_crm_tiles = []
            admin_lead_source_tiles = []
            admin_source_choices = []
            admin_recent_leads = []
            admin_recent_agents = []
            admin_recent_customers = []
            admin_recent_import_batches = []
            admin_import_status_counts = {}
            admin_failed_import_batches = []
            admin_duplicate_leads = []
            admin_failed_rows_total = 0
            admin_duplicate_leads_count = 0
            admin_unassigned_leads = []
            admin_source_kind_choices = []
            admin_demo_lead_rows = []
    context = {
        "user": user,
        "profile": profile,
        "recent_parties": recent_parties,
        "recent_transactions": recent_transactions,
        "total_credit": total_credit_all,
        "total_debit": total_debit_all,
        "net_balance": net_balance,
        "party_cards": party_cards,
        "summary": summary,
        "snapshot": snapshot,
        "period": period,
        "greeting": greeting,
        "subscription": subscription,
        "locked_features_count": locked_features_count,
        "usage_summary": usage_summary,
        "quotation_total": quotation_total,
        "quotation_pending_approval": quotation_pending_approval,
        "quotation_converted": quotation_converted,
        "quotation_rejected": quotation_rejected,
        "high_due_customers": high_due_customers,
        "business_health": business_health,
        "business_health_level": business_health_level,
        "duplicate_invoice_alerts": duplicate_invoice_alerts,
        "agent_dashboard": agent_dashboard,
        "maps_api_key": getattr(settings, "GOOGLE_MAPS_API_KEY", ""),
        "workspace_role": workspace_role,
        "workspace_role_label": role_labels.get(workspace_role, "Workspace"),
        "platform_links": platform_links,
        "dashboard_feature_tracks": dashboard_feature_tracks_map.get(workspace_role, []),
        "dashboard_demo_steps": dashboard_demo_steps_map.get(workspace_role, []),
        "dashboard_settings_cards": dashboard_settings_cards_map.get(workspace_role, []),
        "real_estate_counts": real_estate_counts,
        "agent_profile_summary": agent_profile_summary,
        "dashboard_primary_stats": dashboard_primary_stats,
        "dashboard_module_tiles": dashboard_module_tiles,
        "dashboard_flow_steps": dashboard_flow_steps,
        "dashboard_signal_bars": dashboard_signal_bars,
        "dashboard_quick_actions": dashboard_quick_actions,
        "admin_control_summary": admin_control_summary,
        "admin_control_tiles": admin_control_tiles,
        "admin_intake_tiles": admin_intake_tiles,
        "admin_tech_tiles": admin_tech_tiles,
        "admin_crm_tiles": admin_crm_tiles,
        "admin_lead_source_tiles": admin_lead_source_tiles,
        "admin_source_choices": admin_source_choices,
        "admin_recent_leads": admin_recent_leads,
        "admin_recent_agents": admin_recent_agents,
        "admin_recent_customers": admin_recent_customers,
        "admin_recent_import_batches": admin_recent_import_batches,
        "admin_import_status_counts": admin_import_status_counts,
        "admin_failed_import_batches": admin_failed_import_batches,
        "admin_duplicate_leads": admin_duplicate_leads,
        "admin_failed_rows_total": admin_failed_rows_total,
        "admin_duplicate_leads_count": admin_duplicate_leads_count,
        "admin_unassigned_leads": admin_unassigned_leads,
        "admin_source_kind_choices": admin_source_kind_choices,
        "admin_demo_lead_rows": admin_demo_lead_rows,
        "admin_dashboard_action_url": admin_dashboard_action_url,
        "dashboard_tabs": dashboard_tabs,
        "active_dashboard_tab": active_dashboard_tab,
        "compact_dashboard_mode": compact_dashboard_mode,
        "crm_dashboard": crm_dashboard,
        "lead_rows": lead_rows,
        "lead_filters": lead_filters,
        "lead_source_choices": lead_source_choices,
        "lead_status_choices": lead_status_choices,
        "lead_stage_choices": lead_stage_choices,
        "lead_total_count": lead_total_count,
        "lead_filtered_count": lead_filtered_count,
        "lead_reset_href": lead_reset_href,
        "lead_export_href": lead_export_href,
        "lead_share_href": lead_share_href,
        "lead_email_share_href": lead_email_share_href,
        "lead_current_url": lead_current_url,
        "property_rows": property_rows,
        "property_filters": property_filters,
        "property_status_choices": property_status_choices,
        "property_type_choices": property_type_choices,
        "property_listing_type_choices": property_listing_type_choices,
        "property_total_count": property_total_count,
        "property_filtered_count": property_filtered_count,
        "property_reset_href": property_reset_href,
        "property_export_href": property_export_href,
        "property_share_href": property_share_href,
        "property_email_share_href": property_email_share_href,
        "property_current_url": property_current_url,
        "agent_rows": agent_rows,
        "agent_filters": agent_filters,
        "agent_approval_choices": agent_approval_choices,
        "agent_specialization_choices": agent_specialization_choices,
        "agent_total_count": agent_total_count,
        "agent_filtered_count": agent_filtered_count,
        "agent_reset_href": agent_reset_href,
        "agent_export_href": agent_export_href,
        "agent_share_href": agent_share_href,
        "agent_email_share_href": agent_email_share_href,
        "agent_current_url": agent_current_url,
        "deal_rows": deal_rows,
        "deal_filters": deal_filters,
        "deal_status_choices": deal_status_choices,
        "deal_stage_choices": deal_stage_choices,
        "deal_total_count": deal_total_count,
        "deal_filtered_count": deal_filtered_count,
        "deal_reset_href": deal_reset_href,
        "deal_export_href": deal_export_href,
        "deal_share_href": deal_share_href,
        "deal_email_share_href": deal_email_share_href,
        "deal_current_url": deal_current_url,
        "report_rows": report_rows,
        "report_filters": report_filters,
        "report_type_choices": report_type_choices,
        "report_total_count": report_total_count,
        "report_filtered_count": report_filtered_count,
        "report_reset_href": report_reset_href,
        "report_export_href": report_export_href,
        "report_share_href": report_share_href,
        "report_email_share_href": report_email_share_href,
        "report_current_url": report_current_url,
        "wallet_dashboard": wallet_dashboard,
        "featured_property": featured_property,
        "top_loan_products": top_loan_products,
        "top_schemes": top_schemes,
        "top_articles": top_articles,
        "recent_verifications": recent_verifications,
    }

    if dashboard_page_cache_key:
        cache.set(dashboard_page_cache_key, context, 45)

    return render(request, "accounts/dashboard.html", context)


@login_required
def admin_dashboard_action(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("Admin access required.")
    if request.method != "POST":
        return redirect(f"{reverse('accounts:dashboard')}?tab=dashboard#module-workspace")

    action = (request.POST.get("action") or "").strip().lower()
    redirect_url = f"{reverse('accounts:dashboard')}?tab=dashboard#module-workspace"
    company = getattr(request.user, "company", None)
    profile_company = getattr(getattr(request.user, "userprofile", None), "company", None)

    try:
        from agents.models import Agent
        from customers.models import Customer
        from leads.models import Lead, LeadAssignmentLog, LeadImportBatch, LeadSource
        from leads.services import assign_lead, bulk_assign_leads, ingest_lead_payload, resolve_source_config

        def _company_filter(queryset):
            if company is None:
                return queryset
            field_names = {field.name for field in queryset.model._meta.get_fields()}
            if "company" not in field_names:
                return queryset
            return queryset.filter(company=company)

        def _unique_username(base: str) -> str:
            cleaned = slugify(base or "user").replace("-", "")[:20] or "user"
            candidate = cleaned
            counter = 1
            while User.objects.filter(username=candidate).exists():
                candidate = f"{cleaned}{counter}"
                counter += 1
            return candidate

        def _toggle_user_active(user_obj, is_active: bool):
            if user_obj and user_obj.is_active != is_active:
                user_obj.is_active = is_active
                user_obj.save(update_fields=["is_active"])

        if action == "assign_lead":
            lead_id = request.POST.get("lead_id")
            agent_id = request.POST.get("agent_id")
            reason = (request.POST.get("reason") or "Dashboard lead assignment").strip()
            lead = _company_filter(Lead.objects.select_related("assigned_agent", "assigned_to").filter(pk=lead_id)).first()
            agent = _company_filter(Agent.objects.select_related("user").filter(pk=agent_id)).first()
            if not lead or not agent:
                messages.error(request, "Lead ya agent invalid hai.")
            else:
                assign_lead(
                    lead=lead,
                    agent=agent,
                    actor=request.user,
                    reason=reason,
                    assignment_type=LeadAssignmentLog.AssignmentType.MANUAL,
                )
                messages.success(request, f"{lead.name or lead.mobile or 'Lead'} assigned to {agent.name}.")
        elif action == "create_lead":
            name = (request.POST.get("name") or "").strip()
            phone = (request.POST.get("phone") or request.POST.get("mobile") or "").strip()
            email = (request.POST.get("email") or "").strip()
            if not phone and not email:
                messages.error(request, "Lead ke liye phone ya email required hai.")
            else:
                source_value = (request.POST.get("source") or "manual").strip()
                source_key = (request.POST.get("source_key") or "").strip()
                valid_sources = {value for value, _label in Lead.Source.choices}
                valid_stages = {value for value, _label in Lead.Stage.choices}
                valid_statuses = {value for value, _label in Lead.Status.choices}
                valid_interests = {value for value, _label in Lead.InterestType.choices}
                if source_value not in valid_sources:
                    source_value = Lead.Source.MANUAL
                source_config = resolve_source_config(company=company, source_key=source_key, source_value=source_value)
                lead, _ = ingest_lead_payload(
                    {
                        "name": name or phone or email or "Manual Lead",
                        "phone": phone,
                        "email": email,
                        "source": source_value,
                        "stage": (request.POST.get("stage") or Lead.Stage.NEW).strip() if (request.POST.get("stage") or Lead.Stage.NEW).strip() in valid_stages else Lead.Stage.NEW,
                        "status": (request.POST.get("status") or Lead.Status.NEW).strip() if (request.POST.get("status") or Lead.Status.NEW).strip() in valid_statuses else Lead.Status.NEW,
                        "interest_type": (request.POST.get("interest_type") or Lead.InterestType.BUY).strip() if (request.POST.get("interest_type") or Lead.InterestType.BUY).strip() in valid_interests else Lead.InterestType.BUY,
                        "city": (request.POST.get("city") or "").strip(),
                        "district": (request.POST.get("district") or "").strip(),
                        "state": (request.POST.get("state") or "").strip(),
                        "pincode": (request.POST.get("pincode") or "").strip(),
                        "budget": request.POST.get("budget") or None,
                        "notes": (request.POST.get("notes") or "").strip(),
                    },
                    company=company,
                    actor=request.user,
                    source_config=source_config,
                    auto_assign=(request.POST.get("auto_assign") or "1").strip().lower() not in {"0", "false", "off", "no"},
                )
                messages.success(request, f"Lead '{lead.name or lead.mobile or lead.id}' created.")
        elif action == "create_agent":
            name = (request.POST.get("name") or "").strip()
            email = (request.POST.get("email") or "").strip().lower()
            mobile = (request.POST.get("mobile") or "").strip()
            username = (request.POST.get("username") or "").strip()
            if not name or not email:
                messages.error(request, "Agent ke liye name aur email required hai.")
            else:
                user = User.objects.create_user(
                    username=username or _unique_username(email.split("@")[0] if "@" in email else name),
                    email=email,
                    mobile=mobile or None,
                    password=None,
                    is_active=True,
                    role="agent",
                )
                user.is_staff = False
                user.save(update_fields=["is_staff"])
                agent, _ = Agent.objects.get_or_create(
                    user=user,
                    defaults={
                        "company": profile_company,
                        "name": name,
                        "phone": mobile,
                        "city": (request.POST.get("city") or "").strip(),
                        "district": (request.POST.get("district") or "").strip(),
                        "state": (request.POST.get("state") or "").strip(),
                        "pin_code": (request.POST.get("pin_code") or "").strip(),
                        "approval_status": Agent.ApprovalStatus.PENDING,
                        "kyc_status": "pending",
                        "is_active": True,
                    },
                )
                agent.company = profile_company
                agent.name = name
                agent.phone = mobile
                agent.city = (request.POST.get("city") or "").strip()
                agent.district = (request.POST.get("district") or "").strip()
                agent.state = (request.POST.get("state") or "").strip()
                agent.pin_code = (request.POST.get("pin_code") or "").strip()
                agent.approval_status = Agent.ApprovalStatus.PENDING
                agent.kyc_status = "pending"
                agent.is_active = True
                agent.save()
                messages.success(request, f"Agent '{agent.name}' created.")
        elif action == "create_customer":
            name = (request.POST.get("name") or "").strip()
            email = (request.POST.get("email") or "").strip().lower()
            mobile = (request.POST.get("mobile") or "").strip()
            username = (request.POST.get("username") or "").strip()
            if not name or not email:
                messages.error(request, "Customer ke liye name aur email required hai.")
            else:
                user = User.objects.create_user(
                    username=username or _unique_username(email.split("@")[0] if "@" in email else name),
                    email=email,
                    mobile=mobile or None,
                    password=None,
                    is_active=True,
                    role="customer",
                )
                customer, _ = Customer.objects.get_or_create(
                    user=user,
                    defaults={
                        "company": profile_company,
                        "buyer_type": (request.POST.get("buyer_type") or Customer.BuyerType.BUYER).strip(),
                        "preferred_location": (request.POST.get("preferred_location") or "").strip(),
                        "city": (request.POST.get("city") or "").strip(),
                        "district": (request.POST.get("district") or "").strip(),
                        "state": (request.POST.get("state") or "").strip(),
                        "pin_code": (request.POST.get("pin_code") or "").strip(),
                        "metadata": {"full_name": name},
                    },
                )
                customer.company = profile_company
                customer.buyer_type = (request.POST.get("buyer_type") or Customer.BuyerType.BUYER).strip()
                customer.preferred_location = (request.POST.get("preferred_location") or "").strip()
                customer.city = (request.POST.get("city") or "").strip()
                customer.district = (request.POST.get("district") or "").strip()
                customer.state = (request.POST.get("state") or "").strip()
                customer.pin_code = (request.POST.get("pin_code") or "").strip()
                customer.metadata = {**(customer.metadata or {}), "full_name": name}
                customer.save()
                messages.success(request, f"Customer '{name}' created.")
        elif action == "update_agent":
            agent = _company_filter(Agent.objects.select_related("user").filter(pk=request.POST.get("agent_id"))).first()
            if not agent:
                messages.error(request, "Agent not found.")
            else:
                updated_fields = []
                name = (request.POST.get("name") or "").strip()
                mobile = (request.POST.get("mobile") or "").strip()
                city = (request.POST.get("city") or "").strip()
                district = (request.POST.get("district") or "").strip()
                state = (request.POST.get("state") or "").strip()
                pin_code = (request.POST.get("pin_code") or "").strip()
                specialization = (request.POST.get("specialization") or "").strip()
                approval_status = (request.POST.get("approval_status") or "").strip()
                is_active = (request.POST.get("is_active") or "").strip().lower() != "inactive"
                if name:
                    agent.name = name
                    updated_fields.append("name")
                if mobile:
                    agent.phone = mobile
                    if agent.user:
                        agent.user.mobile = mobile
                        agent.user.save(update_fields=["mobile"])
                    updated_fields.append("phone")
                if city:
                    agent.city = city
                    updated_fields.append("city")
                if district:
                    agent.district = district
                    updated_fields.append("district")
                if state:
                    agent.state = state
                    updated_fields.append("state")
                if pin_code:
                    agent.pin_code = pin_code
                    updated_fields.append("pin_code")
                valid_specializations = {value for value, _label in Agent.Specialization.choices}
                if specialization in valid_specializations:
                    agent.specialization = specialization
                    updated_fields.append("specialization")
                valid_approvals = {value for value, _label in Agent.ApprovalStatus.choices}
                if approval_status in valid_approvals:
                    agent.approval_status = approval_status
                    updated_fields.append("approval_status")
                agent.is_active = is_active
                updated_fields.append("is_active")
                if agent.user and name:
                    parts = name.split(" ", 1)
                    agent.user.first_name = parts[0]
                    agent.user.last_name = parts[1] if len(parts) > 1 else ""
                    agent.user.save(update_fields=["first_name", "last_name"])
                agent.save(update_fields=list(dict.fromkeys(updated_fields + ["updated_at"])))
                _toggle_user_active(agent.user, is_active)
                messages.success(request, f"Agent '{agent.name}' updated.")
        elif action == "update_customer":
            customer = _company_filter(Customer.objects.select_related("user").filter(pk=request.POST.get("customer_id"))).first()
            if not customer:
                messages.error(request, "Customer not found.")
            else:
                name = (request.POST.get("name") or "").strip()
                mobile = (request.POST.get("mobile") or "").strip()
                city = (request.POST.get("city") or "").strip()
                district = (request.POST.get("district") or "").strip()
                state = (request.POST.get("state") or "").strip()
                pin_code = (request.POST.get("pin_code") or "").strip()
                buyer_type = (request.POST.get("buyer_type") or "").strip()
                preferred_location = (request.POST.get("preferred_location") or "").strip()
                is_active = (request.POST.get("is_active") or "").strip().lower() != "inactive"
                if name and customer.user:
                    parts = name.split(" ", 1)
                    customer.user.first_name = parts[0]
                    customer.user.last_name = parts[1] if len(parts) > 1 else ""
                    customer.user.save(update_fields=["first_name", "last_name"])
                if mobile and customer.user:
                    customer.user.mobile = mobile
                    customer.user.save(update_fields=["mobile"])
                if buyer_type in {value for value, _label in Customer.BuyerType.choices}:
                    customer.buyer_type = buyer_type
                if preferred_location:
                    customer.preferred_location = preferred_location
                if city:
                    customer.city = city
                if district:
                    customer.district = district
                if state:
                    customer.state = state
                if pin_code:
                    customer.pin_code = pin_code
                customer.company = profile_company
                customer.save()
                _toggle_user_active(customer.user, is_active)
                messages.success(request, f"Customer '{customer}' updated.")
        elif action == "toggle_agent_status":
            agent = _company_filter(Agent.objects.select_related("user").filter(pk=request.POST.get("agent_id"))).first()
            desired = (request.POST.get("state") or "").strip().lower()
            if not agent:
                messages.error(request, "Agent not found.")
            else:
                is_active = desired != "inactive"
                agent.is_active = is_active
                agent.save(update_fields=["is_active", "updated_at"])
                _toggle_user_active(agent.user, is_active)
                messages.success(request, f"Agent '{agent.name}' {'activated' if is_active else 'deactivated'}.")
        elif action == "toggle_customer_status":
            customer = _company_filter(Customer.objects.select_related("user").filter(pk=request.POST.get("customer_id"))).first()
            desired = (request.POST.get("state") or "").strip().lower()
            if not customer:
                messages.error(request, "Customer not found.")
            else:
                is_active = desired != "inactive"
                _toggle_user_active(customer.user, is_active)
                messages.success(request, f"Customer '{customer}' {'activated' if is_active else 'deactivated'}.")
        elif action == "bulk_manage_agents":
            operation = (request.POST.get("bulk_action") or "activate").strip().lower()
            agent_ids = [item for item in request.POST.getlist("agent_ids") if item]
            agents = list(_company_filter(Agent.objects.select_related("user").filter(pk__in=agent_ids)))
            if not agents:
                messages.error(request, "Bulk agent action ke liye kam se kam ek agent select karo.")
            elif operation == "delete":
                removed = 0
                for agent in agents:
                    _toggle_user_active(agent.user, False)
                    agent.delete()
                    removed += 1
                messages.success(request, f"{removed} agents removed.")
            else:
                is_active = operation != "deactivate"
                for agent in agents:
                    agent.is_active = is_active
                    agent.save(update_fields=["is_active", "updated_at"])
                    _toggle_user_active(agent.user, is_active)
                messages.success(request, f"{len(agents)} agents {'activated' if is_active else 'deactivated'}.")
        elif action == "bulk_manage_customers":
            operation = (request.POST.get("bulk_action") or "activate").strip().lower()
            customer_ids = [item for item in request.POST.getlist("customer_ids") if item]
            customers = list(_company_filter(Customer.objects.select_related("user").filter(pk__in=customer_ids)))
            if not customers:
                messages.error(request, "Bulk customer action ke liye kam se kam ek customer select karo.")
            elif operation == "delete":
                removed = 0
                for customer in customers:
                    _toggle_user_active(customer.user, False)
                    customer.delete()
                    removed += 1
                messages.success(request, f"{removed} customers removed.")
            else:
                is_active = operation != "deactivate"
                for customer in customers:
                    _toggle_user_active(customer.user, is_active)
                messages.success(request, f"{len(customers)} customers {'activated' if is_active else 'deactivated'}.")
        elif action == "delete_agent":
            agent = _company_filter(Agent.objects.select_related("user").filter(pk=request.POST.get("agent_id"))).first()
            if not agent:
                messages.error(request, "Agent not found.")
            else:
                agent_name = agent.name or getattr(agent.user, "email", f"Agent {agent.id}")
                _toggle_user_active(agent.user, False)
                agent.delete()
                messages.success(request, f"Agent '{agent_name}' removed.")
        elif action == "delete_customer":
            customer = _company_filter(Customer.objects.select_related("user").filter(pk=request.POST.get("customer_id"))).first()
            if not customer:
                messages.error(request, "Customer not found.")
            else:
                customer_name = str(customer)
                _toggle_user_active(customer.user, False)
                customer.delete()
                messages.success(request, f"Customer '{customer_name}' removed.")
        elif action == "bulk_assign_leads":
            agent_id = request.POST.get("agent_id")
            reason = (request.POST.get("reason") or "Dashboard bulk assignment").strip()
            lead_ids = [item for item in request.POST.getlist("lead_ids") if item]
            if not lead_ids:
                raw_ids = request.POST.get("lead_ids_text", "")
                lead_ids = [item.strip() for item in raw_ids.split(",") if item.strip()]
            leads = list(
                _company_filter(Lead.objects.select_related("assigned_agent", "assigned_to").filter(pk__in=lead_ids))
            )
            agent = _company_filter(Agent.objects.select_related("user").filter(pk=agent_id)).first()
            if not leads or not agent:
                messages.error(request, "Bulk assign ke liye leads aur agent dono select karo.")
            else:
                updated = bulk_assign_leads(leads=leads, agent=agent, actor=request.user, reason=reason, auto=False)
                messages.success(request, f"{len(updated)} leads {agent.name} ko assign ho gaye.")
        elif action == "assign_by_source":
            source_value = (request.POST.get("source") or "").strip()
            agent_id = request.POST.get("agent_id")
            limit_raw = (request.POST.get("limit") or "10").strip()
            reason = (request.POST.get("reason") or "Source based dashboard assignment").strip()
            valid_sources = {value for value, _label in Lead.Source.choices}
            if source_value not in valid_sources:
                messages.error(request, "Valid source select karo.")
            else:
                try:
                    limit = max(1, min(100, int(limit_raw)))
                except Exception:
                    limit = 10
                leads_qs = _company_filter(
                    Lead.objects.select_related("assigned_agent", "assigned_to").filter(
                        source=source_value,
                        assigned_agent__isnull=True,
                    )
                ).order_by("-created_at", "-id")[:limit]
                leads = list(leads_qs)
                agent = _company_filter(Agent.objects.select_related("user").filter(pk=agent_id)).first()
                if not leads or not agent:
                    messages.error(request, "Source leads ya agent valid nahi hai.")
                else:
                    updated = bulk_assign_leads(leads=leads, agent=agent, actor=request.user, reason=reason, auto=False)
                    messages.success(request, f"{len(updated)} {dict(Lead.Source.choices).get(source_value, source_value)} leads {agent.name} ko assign ho gaye.")
        elif action == "export_demo_lead_template":
            source_value = (request.POST.get("source") or "").strip()
            valid_sources = {value for value, _label in Lead.Source.choices}
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="lead-demo-template.csv"'
            writer = csv.writer(response)
            writer.writerow(["name", "phone", "email", "source", "city", "district", "state", "pincode", "budget", "notes"])
            sample_rows = [
                ["Rahul Sharma", "9000001001", "rahul@example.com", Lead.Source.MANUAL, "Lucknow", "Lucknow", "UP", "226010", "3500000", "Manual entry sample"],
                ["Pooja Verma", "9000001002", "pooja@example.com", Lead.Source.FACEBOOK_ADS, "Noida", "Gautam Buddha Nagar", "UP", "201301", "4200000", "Facebook lead sample"],
                ["Amit Khan", "9000001003", "amit@example.com", Lead.Source.API, "Kanpur", "Kanpur Nagar", "UP", "208001", "2800000", "API feed sample"],
                ["Neha Gupta", "9000001004", "neha@example.com", Lead.Source.WEB_SITE if hasattr(Lead.Source, "WEB_SITE") else Lead.Source.WEBSITE, "Gurugram", "Gurugram", "Haryana", "122001", "5200000", "Website sample"],
                ["Demo Scrape", "9000001005", "scrape@example.com", Lead.Source.WEBSITE, "Delhi", "New Delhi", "Delhi", "110001", "6100000", "Web scrape sample"],
            ]
            if source_value in valid_sources:
                sample_rows = [row for row in sample_rows if row[3] == source_value] or sample_rows
            for row in sample_rows:
                writer.writerow(row)
            return response
        elif action == "create_lead_source":
            name = (request.POST.get("name") or "").strip()
            if not name:
                messages.error(request, "Lead source name required hai.")
            else:
                kind = (request.POST.get("kind") or LeadSource.Kind.MANUAL).strip()
                valid_kinds = {value for value, _label in LeadSource.Kind.choices}
                if kind not in valid_kinds:
                    kind = LeadSource.Kind.MANUAL
                slug = slugify((request.POST.get("slug") or name).strip())[:120] or slugify(name)[:120]
                source_value = (request.POST.get("source_value") or Lead.Source.MANUAL).strip()
                endpoint_url = (request.POST.get("endpoint_url") or "").strip()
                verify_token = (request.POST.get("verify_token") or "").strip()
                webhook_secret = (request.POST.get("webhook_secret") or "").strip()
                auto_assign_raw = (request.POST.get("auto_assign") or "").strip().lower()
                auto_assign = auto_assign_raw not in {"0", "false", "off", "no", ""}
                LeadSource.objects.update_or_create(
                    company=company,
                    slug=slug,
                    defaults={
                        "name": name,
                        "kind": kind,
                        "source_value": source_value,
                        "endpoint_url": endpoint_url,
                        "verify_token": verify_token,
                        "webhook_secret": webhook_secret,
                        "auto_assign": auto_assign,
                        "is_active": True,
                    },
                )
                messages.success(request, f"Lead source '{name}' saved.")
        elif action == "resolve_duplicate_lead":
            lead = _company_filter(Lead.objects.select_related("assigned_agent", "duplicate_of").filter(pk=request.POST.get("lead_id"))).first()
            if not lead:
                messages.error(request, "Duplicate lead not found.")
            else:
                lead.is_duplicate = False
                lead.duplicate_reason = ""
                lead.duplicate_of = None
                lead.save(update_fields=["is_duplicate", "duplicate_reason", "duplicate_of", "updated_at"])
                messages.success(request, f"Lead '{lead.name or lead.mobile or lead.id}' marked as resolved.")
        elif action == "export_duplicate_leads":
            duplicate_leads = Lead.objects.select_related("assigned_agent", "duplicate_of").filter(is_duplicate=True)
            if company is not None:
                duplicate_leads = duplicate_leads.filter(company=company)
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="duplicate-leads.csv"'
            writer = csv.writer(response)
            writer.writerow(["Lead ID", "Name", "Mobile", "Email", "Source", "Status", "Stage", "Duplicate Of", "Reason"])
            for lead in duplicate_leads.order_by("-created_at", "-id"):
                writer.writerow(
                    [
                        lead.id,
                        lead.name or "",
                        lead.mobile or "",
                        lead.email or "",
                        lead.get_source_display(),
                        lead.get_status_display(),
                        lead.get_stage_display(),
                        getattr(lead.duplicate_of, "id", "") or "",
                        lead.duplicate_reason or "",
                    ]
                )
            return response
        elif action == "export_failed_imports":
            failed_imports = LeadImportBatch.objects.select_related("source", "created_by").filter(failed_rows__gt=0)
            if company is not None:
                failed_imports = failed_imports.filter(company=company)
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="failed-import-rows.csv"'
            writer = csv.writer(response)
            writer.writerow(["Batch ID", "Source", "Import Type", "Status", "Failed Rows", "Created Leads", "Error Count", "Error Preview"])
            for batch in failed_imports.order_by("-failed_rows", "-updated_at", "-id"):
                errors = batch.error_report or []
                preview_parts = []
                if isinstance(errors, list):
                    for item in errors[:3]:
                        if isinstance(item, dict):
                            preview_parts.append(
                                item.get("message")
                                or item.get("error")
                                or item.get("row")
                                or item.get("detail")
                                or str(item)
                            )
                        else:
                            preview_parts.append(str(item))
                writer.writerow(
                    [
                        batch.id,
                        batch.source_name or getattr(batch.source, "name", "") or "",
                        batch.get_import_type_display(),
                        batch.get_status_display(),
                        batch.failed_rows,
                        batch.created_leads,
                        len(errors) if isinstance(errors, list) else 0,
                        " | ".join(preview_parts),
                    ]
                )
            return response
        else:
            messages.info(request, "No admin action selected.")
    except Exception as exc:
        messages.error(request, f"Admin action failed: {exc}")

    return redirect(redirect_url)


def _crm_lead_queryset_for_user(user):
    from customers.models import Customer
    from leads.models import Lead

    queryset = Lead.objects.select_related(
        "assigned_agent",
        "assigned_to",
        "source_config",
        "interested_property",
        "converted_customer",
    )
    company = getattr(user, "company", None)
    if company is not None:
        queryset = queryset.filter(company=company)

    if user.is_superuser or user.is_staff:
        return queryset.distinct()

    agent_profile = getattr(user, "agent_profile", None)
    if agent_profile:
        return queryset.filter(
            Q(assigned_agent=agent_profile) | Q(assignments__agent=agent_profile) | Q(created_by=user)
        ).distinct()

    customer_profile = Customer.objects.filter(user=user).first()
    lead_scope = Q(created_by=user)
    if user.email:
        lead_scope |= Q(email__iexact=user.email)
    if customer_profile:
        lead_scope |= Q(converted_customer=customer_profile)
    return queryset.filter(lead_scope).distinct()


def _lead_operation_allowed(user, lead):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or user.is_staff:
        return True
    agent_profile = getattr(user, "agent_profile", None)
    if not agent_profile:
        return False
    if lead.created_by_id == user.id:
        return True
    if lead.assigned_agent_id == agent_profile.id:
        return True
    return lead.assignments.filter(agent=agent_profile).exists()


def _lead_temperature_payload(lead):
    score = int(getattr(lead, "lead_score", 0) or getattr(lead, "score", 0) or 0)
    temperature = str(getattr(lead, "temperature", "") or "").lower() or "warm"
    config = {
        "hot": {"emoji": "🔥", "label": "Hot", "tone": "hot"},
        "warm": {"emoji": "⚡", "label": "Warm", "tone": "warm"},
        "cold": {"emoji": "❄️", "label": "Cold", "tone": "cold"},
    }.get(temperature, {"emoji": "⚡", "label": "Warm", "tone": "warm"})
    return {**config, "score": score}


def _lead_prediction_payload(lead, *, property_matches=None):
    property_matches = property_matches or []
    interaction_count = (
        lead.activities.count()
        + lead.message_logs.count()
        + lead.call_logs.count()
        + lead.voice_calls.count()
    )
    base_score = int(getattr(lead, "lead_score", 0) or getattr(lead, "score", 0) or 0)
    property_match_score = min(len(property_matches) * 6, 18)
    location_demand = 10 if (lead.pincode_text or lead.city or lead.district) else 4
    response_boost = 0
    if lead.last_contacted_at:
        response_delta = timezone.now() - lead.last_contacted_at
        if response_delta <= timedelta(hours=6):
            response_boost = 12
        elif response_delta <= timedelta(hours=24):
            response_boost = 8
        else:
            response_boost = 4
    assigned_agent = getattr(lead, "assigned_agent", None)
    agent_performance = min(int(getattr(assigned_agent, "performance_score", 0) or 0) // 4, 18)
    probability = max(
        5,
        min(
            100,
            int(
                (base_score * 0.52)
                + min(interaction_count * 5, 22)
                + property_match_score
                + location_demand
                + response_boost
                + agent_performance
            ),
        ),
    )
    if lead.status == "converted":
        probability = 100
    elif lead.status in {"closed", "lost", "inactive"}:
        probability = min(probability, 15)

    if probability >= 70:
        label = "High chance to convert"
        tone = "high"
    elif probability >= 45:
        label = "Medium chance"
        tone = "medium"
    else:
        label = "Low chance"
        tone = "low"

    if base_score >= 80:
        best_time = "10:00 AM - 12:30 PM"
    elif lead.interest_type == "buy":
        best_time = "4:00 PM - 7:00 PM"
    else:
        best_time = "11:30 AM - 2:00 PM"

    return {
        "probability": probability,
        "label": label,
        "tone": tone,
        "interaction_count": interaction_count,
        "best_time": best_time,
    }


def _lead_default_message(lead, channel):
    name = (lead.name or "there").strip() or "there"
    if channel == "email":
        return (
            f"Hello {name},\n\n"
            f"We reviewed your property enquiry for {lead.preferred_location or lead.city or 'your preferred area'}.\n"
            "I can help with options, pricing, and site visits. Reply with your preferred time.\n\n"
            "Regards,\nReal Estate CRM"
        )
    if channel == "sms":
        return f"Hi {name}, properties matching your enquiry are ready. Reply for a visit slot."
    if channel == "messenger":
        return f"Hi {name}, I am sharing the next best property options for your enquiry."
    if channel == "instagram_dm":
        return f"Hi {name}, your property enquiry is active. Want shortlisted options in your budget?"
    return f"Hi {name}, your enquiry is active. I can share matching properties and arrange a site visit."


@login_required
@feature_required("crm.leads")
def lead_workspace(request, lead_id):
    from communication.models import EmailLog, SMSLog
    from crm.models import CallLog
    from leads.models import FollowUp, Lead
    from leads.services import build_lead_timeline, match_properties_for_lead, recommend_best_agent

    lead = get_object_or_404(_crm_lead_queryset_for_user(request.user), pk=lead_id)
    property_matches = list(match_properties_for_lead(lead, limit=6))
    ai_temperature = _lead_temperature_payload(lead)
    prediction = _lead_prediction_payload(lead, property_matches=property_matches)
    recommended_agent = recommend_best_agent(lead)
    timeline_rows = build_lead_timeline(lead, limit=30)
    followup_rows = list(lead.followups.order_by("followup_date")[:8])
    message_logs = list(lead.message_logs.order_by("-created_at")[:8])
    email_logs = list(EmailLog.objects.filter(metadata__lead_id=lead.id).order_by("-created_at")[:8])
    sms_logs = list(SMSLog.objects.filter(metadata__lead_id=lead.id).order_by("-created_at")[:8])
    call_logs = list(CallLog.objects.filter(lead=lead).order_by("-created_at")[:8])
    voice_calls = list(lead.voice_calls.order_by("-created_at")[:6])
    related_scope = Q()
    if lead.mobile:
        related_scope |= Q(mobile=lead.mobile)
    if lead.email:
        related_scope |= Q(email__iexact=lead.email)
    if lead.city:
        related_scope |= Q(city__iexact=lead.city, interest_type=lead.interest_type)
    elif lead.preferred_location:
        related_scope |= Q(preferred_location__iexact=lead.preferred_location, interest_type=lead.interest_type)
    related_leads = (
        list(_crm_lead_queryset_for_user(request.user).exclude(pk=lead.pk).filter(related_scope).distinct()[:5])
        if related_scope.children
        else []
    )
    active_assignment = (
        lead.assignments.select_related("agent", "assigned_by")
        .filter(is_active=True)
        .order_by("-created_at")
        .first()
    )
    message_channel_choices = [
        ("whatsapp", "WhatsApp"),
        ("email", "Email"),
        ("sms", "SMS"),
        ("messenger", "Messenger"),
        ("instagram_dm", "Instagram DM"),
    ]
    followup_channel_choices = [
        ("whatsapp", "WhatsApp"),
        ("email", "Email"),
        ("sms", "SMS"),
        ("call", "Call"),
    ]
    map_provider = getattr(settings, "CRM_MAP_PROVIDER", "") or getattr(settings, "MAP_PROVIDER", "") or "google_maps"
    can_operate = _lead_operation_allowed(request.user, lead)
    context = {
        "lead": lead,
        "crm_dashboard": build_crm_dashboard_context(request.user),
        "ai_temperature": ai_temperature,
        "prediction": prediction,
        "property_matches": property_matches,
        "recommended_agent": recommended_agent,
        "timeline_rows": timeline_rows,
        "followup_rows": followup_rows,
        "message_logs": message_logs,
        "email_logs": email_logs,
        "sms_logs": sms_logs,
        "call_logs": call_logs,
        "voice_calls": voice_calls,
        "related_leads": related_leads,
        "active_assignment": active_assignment,
        "status_choices": Lead.Status.choices,
        "stage_choices": Lead.Stage.choices,
        "message_channel_choices": message_channel_choices,
        "followup_channel_choices": followup_channel_choices,
        "default_whatsapp_message": _lead_default_message(lead, "whatsapp"),
        "default_email_message": _lead_default_message(lead, "email"),
        "default_sms_message": _lead_default_message(lead, "sms"),
        "default_messenger_message": _lead_default_message(lead, "messenger"),
        "default_instagram_message": _lead_default_message(lead, "instagram_dm"),
        "default_followup_message": f"Hi {lead.name or 'there'}, following up on your property enquiry. Shall we schedule the next step?",
        "default_call_script": (
            f"Call {lead.name or lead.mobile}, confirm {lead.interest_type} requirement, "
            f"budget {lead.budget or 'not shared'}, and next visit slot."
        ),
        "map_provider": str(map_provider).replace("_", " ").title(),
        "can_operate": can_operate,
    }
    return render(request, "accounts/lead_workspace.html", context)


@login_required
@feature_required("crm.leads")
@require_POST
def lead_workspace_action(request, lead_id):
    from crm.models import CallLog
    from leads.models import FollowUp, Lead, LeadActivity
    from leads.services import (
        assign_lead,
        convert_lead,
        refresh_lead_score,
        recommend_best_agent,
        schedule_followup,
        send_lead_message,
    )
    from voice.models import VoiceCall
    from voice.services import start_voice_call

    lead = get_object_or_404(_crm_lead_queryset_for_user(request.user), pk=lead_id)
    if not _lead_operation_allowed(request.user, lead):
        return HttpResponseForbidden("Lead operation access required.")

    action = (request.POST.get("action") or "").strip().lower()
    return_anchor = (request.POST.get("return_anchor") or "action-center").strip() or "action-center"
    redirect_url = f"{reverse('accounts:lead_workspace', args=[lead.id])}#{return_anchor}"

    try:
        if action == "send_message":
            channel = (request.POST.get("channel") or "whatsapp").strip().lower()
            subject = (request.POST.get("subject") or "").strip()
            message_body = (request.POST.get("message") or _lead_default_message(lead, channel)).strip()
            if not message_body:
                raise ValueError("Message text is required.")
            send_lead_message(
                lead,
                channel=channel,
                message=message_body,
                subject=subject,
                actor=request.user,
                metadata={"source": "accounts.lead_workspace"},
            )
            messages.success(request, f"{channel.replace('_', ' ').title()} action logged for this lead.")
        elif action == "quick_followup":
            hours = max(int(request.POST.get("hours") or 24), 1)
            channel = (request.POST.get("channel") or FollowUp.Channel.WHATSAPP).strip().lower()
            message_body = (request.POST.get("message") or "").strip() or (
                f"Hi {lead.name or 'there'}, following up on your property enquiry."
            )
            schedule_followup(
                lead,
                when=timezone.now() + timedelta(hours=hours),
                message=message_body,
                channel=channel,
            )
            messages.success(request, f"Follow-up scheduled in {hours} hours.")
        elif action == "schedule_followup":
            raw_followup_at = (request.POST.get("followup_at") or "").strip()
            followup_at = parse_datetime(raw_followup_at) if raw_followup_at else None
            if followup_at and timezone.is_naive(followup_at):
                followup_at = timezone.make_aware(followup_at, timezone.get_current_timezone())
            if not followup_at:
                followup_at = timezone.now() + timedelta(hours=24)
            channel = (request.POST.get("channel") or FollowUp.Channel.WHATSAPP).strip().lower()
            message_body = (request.POST.get("message") or "").strip() or (
                f"Hi {lead.name or 'there'}, following up on your property enquiry."
            )
            schedule_followup(lead, when=followup_at, message=message_body, channel=channel)
            messages.success(request, "Follow-up added to the queue.")
        elif action == "add_note":
            note = (request.POST.get("note") or "").strip()
            if not note:
                raise ValueError("Note cannot be empty.")
            LeadActivity.objects.create(
                lead=lead,
                actor=request.user,
                activity_type="note",
                note=note[:1000],
                payload={"source": "accounts.lead_workspace"},
            )
            messages.success(request, "Lead note added.")
        elif action == "update_pipeline":
            status = (request.POST.get("status") or lead.status).strip()
            stage = (request.POST.get("stage") or lead.stage).strip()
            note = (request.POST.get("note") or "").strip()
            original_stage = lead.stage
            original_status = lead.status
            if status != original_status:
                lead.mark_status(status, actor=request.user, note=note)
            if stage and stage != lead.stage:
                lead.stage = stage
                lead.save(update_fields=["stage", "updated_at"])
                LeadActivity.objects.create(
                    lead=lead,
                    actor=request.user,
                    activity_type="stage_change",
                    note=note[:300],
                    payload={"from": original_stage, "to": stage},
                )
            if status == original_status and stage == original_stage and note:
                LeadActivity.objects.create(
                    lead=lead,
                    actor=request.user,
                    activity_type="pipeline_note",
                    note=note[:300],
                    payload={"status": status, "stage": stage},
                )
            messages.success(request, "Lead status and stage updated.")
        elif action == "start_call":
            script = (request.POST.get("script") or "").strip() or (
                f"Call {lead.name or lead.mobile}, confirm requirement, budget, and next action."
            )
            voice_call = start_voice_call(lead, trigger=VoiceCall.Trigger.MANUAL, script=script)
            send_lead_message(
                lead,
                channel="call",
                message="Manual call initiated from lead workspace.",
                actor=request.user,
                metadata={"voice_call_id": voice_call.id},
            )
            CallLog.objects.create(
                lead=lead,
                agent=request.user,
                direction="outbound",
                phone_number=lead.mobile,
                outcome=voice_call.status,
                telephony_provider=voice_call.provider,
                external_call_id=voice_call.provider_call_id,
                recording_url=voice_call.recording_url,
                note=voice_call.summary or script[:300],
                metadata={"voice_call_id": voice_call.id, "source": "accounts.lead_workspace"},
            )
            if voice_call.status == VoiceCall.Status.FAILED:
                messages.warning(request, "Call log created, but provider call could not start. Check voice credentials.")
            else:
                messages.success(request, "Lead call triggered.")
        elif action == "refresh_ai":
            refresh_lead_score(lead)
            messages.success(request, "AI lead score refreshed.")
        elif action == "reassign_best_agent":
            best_agent = recommend_best_agent(lead)
            if not best_agent:
                raise ValueError("No matching agent available.")
            assign_lead(
                lead,
                agent=best_agent,
                actor=request.user,
                reason="Reassigned from lead workspace.",
                match_level="manual",
                assignment_type="reassign",
            )
            messages.success(request, f"Lead assigned to {best_agent.name or best_agent.user.username}.")
        elif action == "convert":
            amount_text = (request.POST.get("deal_amount") or "").strip()
            deal_amount = Decimal(amount_text) if amount_text else None
            result = convert_lead(
                lead,
                actor=request.user,
                deal_amount=deal_amount,
                customer_name=(request.POST.get("customer_name") or "").strip(),
                customer_email=(request.POST.get("customer_email") or "").strip(),
                customer_phone=(request.POST.get("customer_phone") or "").strip(),
                note=(request.POST.get("note") or "").strip(),
            )
            messages.success(request, f"Lead converted. Deal #{result['deal'].id} created.")
        else:
            messages.error(request, "Unknown lead action.")
    except Exception as exc:
        messages.error(request, f"Lead action failed: {exc}")

    return redirect(redirect_url)


def _crm_property_queryset_for_user(user):
    from customers.models import Customer
    from leads.models import Property

    queryset = Property.objects.select_related("assigned_agent", "owner", "builder", "company")
    company = getattr(user, "company", None)
    if company is not None:
        queryset = queryset.filter(company=company)

    if user.is_superuser or user.is_staff:
        return queryset.distinct()

    agent_profile = getattr(user, "agent_profile", None)
    if agent_profile:
        return queryset.filter(Q(assigned_agent=agent_profile) | Q(owner=user)).distinct()

    customer_profile = Customer.objects.filter(user=user).first()
    scope = Q()
    if customer_profile:
        if customer_profile.city:
            scope |= Q(city__iexact=customer_profile.city)
        if customer_profile.district:
            scope |= Q(district__iexact=customer_profile.district)
        if customer_profile.pin_code:
            scope |= Q(pin_code=customer_profile.pin_code)
    return queryset.filter(scope).distinct() if scope.children else queryset.none()


def _crm_deal_queryset_for_user(user):
    from customers.models import Customer
    from deals.models import Deal

    queryset = Deal.objects.select_related("lead", "agent", "customer", "property", "company")
    company = getattr(user, "company", None)
    if company is not None:
        queryset = queryset.filter(company=company)

    if user.is_superuser or user.is_staff:
        return queryset.distinct()

    agent_profile = getattr(user, "agent_profile", None)
    if agent_profile:
        return queryset.filter(agent=agent_profile).distinct()

    customer_profile = Customer.objects.filter(user=user).first()
    scope = Q(customer__user=user)
    if customer_profile:
        scope |= Q(customer=customer_profile)
    if user.email:
        scope |= Q(lead__email__iexact=user.email)
    return queryset.filter(scope).distinct()


def _crm_agent_queryset_for_user(user):
    from agents.models import Agent
    from customers.models import Customer

    queryset = Agent.objects.select_related("user", "company").prefetch_related("coverage_areas")
    if user.is_superuser or user.is_staff:
        return queryset.distinct()

    agent_profile = getattr(user, "agent_profile", None)
    if agent_profile:
        return queryset.filter(pk=agent_profile.pk)

    customer_profile = Customer.objects.filter(user=user).first()
    if customer_profile and customer_profile.assigned_agent_id:
        return queryset.filter(pk=customer_profile.assigned_agent_id)
    return queryset.none()


def _build_csv_response(filename, headers, rows):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return response


def _crm_activity_queryset_for_user(user):
    from customers.models import Customer
    from leads.models import LeadActivity

    queryset = LeadActivity.objects.select_related("lead", "actor", "lead__assigned_agent", "lead__company")
    company = getattr(user, "company", None)
    if company is not None:
        queryset = queryset.filter(lead__company=company)

    if user.is_superuser or user.is_staff:
        return queryset.distinct()

    agent_profile = getattr(user, "agent_profile", None)
    if agent_profile:
        return queryset.filter(Q(lead__assigned_agent=agent_profile) | Q(actor=user)).distinct()

    customer_profile = Customer.objects.filter(user=user).first()
    scope = Q(actor=user) | Q(lead__created_by=user)
    if user.email:
        scope |= Q(lead__email__iexact=user.email)
    if customer_profile:
        scope |= Q(lead__converted_customer=customer_profile)
    return queryset.filter(scope).distinct()


def _default_workspace_context(request, *, title, kicker, copy, actions=None, badges=None, stats=None, main_sections=None, side_sections=None):
    return {
        "workspace_title": title,
        "workspace_kicker": kicker,
        "workspace_copy": copy,
        "workspace_actions": actions or [],
        "workspace_badges": badges or [],
        "workspace_stats": stats or [],
        "workspace_sections_main": main_sections or [],
        "workspace_sections_side": side_sections or [],
        "crm_dashboard": build_crm_dashboard_context(request.user),
        "map_provider": (getattr(settings, "CRM_MAP_PROVIDER", "") or getattr(settings, "MAP_PROVIDER", "") or "google_maps").replace("_", " ").title(),
    }


@login_required
@feature_required("crm.properties")
@require_http_methods(["GET", "POST"])
def property_workspace(request, property_id):
    from billing.invoice_engine import create_invoice_for_lead
    from billing.models import Invoice
    from deals.models import Deal
    from deals.models_commission import Commission
    from deals.services import settle_deal_commission
    from leads.models import Lead, Property, PropertyImage, PropertyMedia, PropertyVideo
    from payments.models import PaymentOrder
    from payments.services.gateway import build_checkout_context, create_payment_order

    property_obj = get_object_or_404(
        _crm_property_queryset_for_user(request.user).prefetch_related("images", "videos"),
        pk=property_id,
    )
    inquiry_rows = list(
        property_obj.inquiries.select_related("assigned_agent", "created_by").order_by("-updated_at")[:10]
    )
    deal_rows = list(property_obj.deals.select_related("lead", "agent", "customer", "commission").order_by("-updated_at")[:8])
    primary_deal = deal_rows[0] if deal_rows else None
    latest_invoice = None
    latest_payment_order = None
    latest_commission = getattr(primary_deal, "commission", None) if primary_deal else None
    csrf_token = get_token(request)

    def _is_admin_actor(user):
        return bool(user.is_superuser or getattr(user, "is_staff", False) or getattr(user, "role", "") in {"admin", "super_admin", "state_admin", "district_admin", "area_admin"})

    def _make_map_query():
        if property_obj.latitude is not None and property_obj.longitude is not None:
            return f"{property_obj.latitude},{property_obj.longitude}"
        parts = [property_obj.title, property_obj.location, property_obj.city, property_obj.district, property_obj.state]
        return ", ".join(part for part in parts if part)

    map_query = _make_map_query()
    encoded_map_query = urllib.parse.quote_plus(map_query)
    google_map_embed_url = f"https://www.google.com/maps?q={encoded_map_query}&z=15&output=embed" if map_query else ""
    google_map_url = f"https://www.google.com/maps/search/?api=1&query={encoded_map_query}" if map_query else "https://www.google.com/maps"
    mapmyindia_url = f"https://www.mappls.com/?q={encoded_map_query}" if map_query else "https://www.mappls.com"

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "upload_property_image":
            image_file = request.FILES.get("image")
            image_url = (request.POST.get("image_url") or "").strip()
            caption = (request.POST.get("caption") or "").strip()
            sort_order_raw = (request.POST.get("sort_order") or "0").strip()
            is_primary = (request.POST.get("is_primary") or "").strip().lower() in {"1", "true", "yes", "on"}
            if not image_file and not image_url:
                messages.error(request, "Image file ya image URL dono me se ek provide karo.")
            else:
                try:
                    sort_order = max(0, int(sort_order_raw))
                except Exception:
                    sort_order = 0
                if is_primary:
                    PropertyImage.objects.filter(property=property_obj, is_primary=True).update(is_primary=False)
                image = PropertyImage.objects.create(
                    property=property_obj,
                    image=image_file,
                    image_url=image_url,
                    caption=caption,
                    sort_order=sort_order,
                    is_primary=is_primary,
                )
                PropertyMedia.objects.create(
                    property=property_obj,
                    media_type=PropertyMedia.MediaType.IMAGE,
                    file=image_file,
                    external_url=image_url,
                    caption=caption,
                    sort_order=sort_order,
                )
                messages.success(request, "Property image saved.")
        elif action == "upload_property_video":
            video_file = request.FILES.get("video")
            video_url = (request.POST.get("video_url") or "").strip()
            caption = (request.POST.get("caption") or "").strip()
            if not video_file and not video_url:
                messages.error(request, "Video file ya video URL provide karo.")
            else:
                video = PropertyVideo.objects.create(property=property_obj, video=video_file, video_url=video_url, caption=caption)
                PropertyMedia.objects.create(
                    property=property_obj,
                    media_type=PropertyMedia.MediaType.VIDEO,
                    file=video_file,
                    external_url=video_url,
                    caption=caption,
                )
                messages.success(request, "Property video saved.")
        elif action == "generate_payment_link":
            if not _is_admin_actor(request.user):
                messages.error(request, "Only admins can generate payment links.")
            else:
                deal_id = request.POST.get("deal_id") or (primary_deal.id if primary_deal else "")
                deal = None
                if deal_id:
                    deal = get_object_or_404(
                        Deal.objects.select_related("lead", "agent", "customer", "property", "commission").filter(property=property_obj),
                        pk=deal_id,
                    )
                amount_raw = (request.POST.get("amount") or "").strip()
                gateway = (request.POST.get("gateway") or PaymentOrder.Gateway.RAZORPAY).lower()
                if not deal:
                    messages.error(request, "Payment link ke liye ek deal select karo.")
                else:
                    try:
                        amount = Decimal(amount_raw) if amount_raw else Decimal(str(deal.deal_amount or 0))
                    except Exception:
                        amount = Decimal(str(deal.deal_amount or 0))
                    invoice = create_invoice_for_lead(
                        deal.lead,
                        deal=deal,
                        actor=request.user,
                        amount=amount,
                        source_note="Property workspace payment link",
                    )
                    if invoice is None:
                        messages.error(request, "Invoice generate nahi ho paayi.")
                    else:
                        payment_order = getattr(invoice, "payment_order", None)
                        if payment_order is None:
                            payment_order = create_payment_order(
                                user=invoice.user,
                                wallet=getattr(invoice.user, "wallet", None),
                                amount=amount or invoice.total_amount,
                                gateway=gateway,
                                purpose=PaymentOrder.Purpose.PROPERTY_BOOKING,
                                order=None,
                                callback_url=request.build_absolute_uri(reverse("payments:webhook", args=[gateway])),
                                return_url=request.build_absolute_uri(reverse("accounts:property_workspace", args=[property_obj.id])),
                                metadata={"invoice_id": invoice.id, "deal_id": deal.id, "property_id": property_obj.id},
                            )
                            invoice.payment_order = payment_order
                            invoice.save(update_fields=["payment_order"])
                        latest_invoice = invoice
                        latest_payment_order = payment_order
                        messages.success(request, f"Payment link ready for {invoice.invoice_number}.")
        elif action == "release_commission":
            if not _is_admin_actor(request.user):
                messages.error(request, "Only admins can release commission.")
            else:
                deal_id = request.POST.get("deal_id") or (primary_deal.id if primary_deal else "")
                if not deal_id:
                    messages.error(request, "Commission release ke liye deal select karo.")
                else:
                    deal = get_object_or_404(
                        Deal.objects.select_related("lead", "agent", "customer", "property", "commission").filter(property=property_obj),
                        pk=deal_id,
                    )
                    latest_invoice = deal.lead.billing_invoices.order_by("-created_at").first() if deal.lead_id else None
                    paid = bool(latest_invoice and latest_invoice.status == Invoice.Status.PAID)
                    if latest_invoice and getattr(latest_invoice, "payment_order_id", None):
                        paid = paid or latest_invoice.payment_order.status == PaymentOrder.Status.PAID
                    if not paid:
                        messages.error(request, "Commission release ke liye payment received hona chahiye.")
                    else:
                        commission = settle_deal_commission(
                            deal,
                            actor=request.user,
                            settled=True,
                            credit_agent_wallet=True,
                            payment_invoice_number=latest_invoice.invoice_number if latest_invoice else "",
                            note=f"Property workspace release for deal {deal.id}",
                        )
                        latest_commission = commission
                        messages.success(request, f"Commission released for deal #{deal.id} and credited to agent wallet.")

    similar_scope = Q(city__iexact=property_obj.city) | Q(district__iexact=property_obj.district)
    similar_rows = list(
        _crm_property_queryset_for_user(request.user)
        .exclude(pk=property_obj.pk)
        .filter(similar_scope)
        .order_by("-updated_at")[:6]
    ) if property_obj.city or property_obj.district else []
    local_lead_count = Lead.objects.filter(
        Q(interested_property=property_obj) | Q(city__iexact=property_obj.city, property_type=property_obj.property_type)
    ).distinct().count()

    property_image_rows = [
        {
            "title": image.caption or f"Image #{image.id}",
            "href": image.image_url or (image.image.url if getattr(image, "image", None) and getattr(image.image, "url", "") else ""),
            "subtitle": f"Primary | Sort {image.sort_order}" if image.is_primary else f"Sort {image.sort_order}",
            "meta": "Image",
            "thumb_url": image.image_url or (image.image.url if getattr(image, "image", None) and getattr(image.image, "url", "") else ""),
            "is_primary": image.is_primary,
            "media_kind": "image",
        }
        for image in property_obj.images.all().order_by("-is_primary", "sort_order", "-created_at")[:8]
    ]
    property_video_rows = [
        {
            "title": video.caption or f"Video #{video.id}",
            "href": video.video_url or (video.video.url if getattr(video, "video", None) and getattr(video.video, "url", "") else ""),
            "subtitle": "Property video",
            "meta": "Video",
            "thumb_url": property_image_rows[0]["thumb_url"] if property_image_rows else "",
            "poster_url": property_image_rows[0]["thumb_url"] if property_image_rows else "",
            "is_primary": False,
            "media_kind": "video",
        }
        for video in property_obj.videos.all().order_by("-created_at")[:8]
    ]
    media_rows = property_image_rows + property_video_rows
    featured_image = property_image_rows[0] if property_image_rows else None
    featured_video = property_video_rows[0] if property_video_rows else None
    media_thumb_html = "".join(
        str(
            format_html(
                '<a class="obj-thumb-chip obj-lightbox-trigger" href="{}" target="_blank" rel="noopener" onclick="if (window.ObjLightbox) return window.ObjLightbox.open(this);" data-lightbox-kind="{}" data-lightbox-src="{}" data-lightbox-title="{}" data-lightbox-meta="{}" data-lightbox-poster="{}">'
                '<span>{}</span><strong>{}</strong><small>{}</small></a>',
                row["href"],
                row.get("media_kind") or "image",
                row["href"],
                row["title"],
                row.get("subtitle") or row.get("meta") or "",
                row.get("poster_url") or row.get("thumb_url") or row["href"],
                "Video" if row.get("media_kind") == "video" else "Image",
                row["title"],
                row.get("subtitle") or row.get("meta") or "",
            )
        )
        for row in media_rows[:6]
    )
    media_slider_items_html = "".join(
        str(
            format_html(
                '<div class="carousel-item{}">'
                '<div class="obj-media-slide-card">'
                '{media}'
                '<div class="obj-media-slide-copy">'
                '<div>'
                '<span class="obj-label">{kind}</span>'
                '<strong>{title}</strong>'
                '<small>{meta}</small>'
                '</div>'
                '<button type="button" class="eco-action-btn obj-preview-action obj-lightbox-trigger" onclick="if (window.ObjLightbox) return window.ObjLightbox.open(this);" data-lightbox-kind="{lightbox_kind}" data-lightbox-src="{src}" data-lightbox-title="{title}" data-lightbox-meta="{subtitle}" data-lightbox-poster="{poster}">Preview</button>'
                '</div>'
                '</div>'
                '</div>',
                " active" if idx == 0 else "",
                media=format_html(
                    '<img src="{}" alt="{}" loading="lazy">',
                    row.get("thumb_url") or row["href"],
                    row["title"],
                )
                if row.get("media_kind") != "video"
                else format_html(
                    '<div class="obj-media-slide-video">'
                    '<img src="{}" alt="{}" loading="lazy">'
                    '<span class="obj-mini-overlay primary"><i class="bi bi-play-circle"></i>Video Preview</span>'
                    '</div>',
                    row.get("poster_url") or row.get("thumb_url") or row["href"],
                    row["title"],
                ),
                kind="Image" if row.get("media_kind") != "video" else "Video",
                title=row["title"],
                meta=row.get("subtitle") or row.get("meta") or "",
                lightbox_kind=row.get("media_kind") or "image",
                src=row["href"],
                subtitle=row.get("subtitle") or row.get("meta") or "",
                poster=row.get("poster_url") or row.get("thumb_url") or row["href"],
            )
        )
        for idx, row in enumerate(media_rows[:5])
    )
    media_slider_indicators_html = "".join(
        str(
            format_html(
                '<button type="button" data-bs-target="#propertyMediaCarousel" data-bs-slide-to="{}" class="{}" aria-label="Slide {}"></button>',
                idx,
                "active" if idx == 0 else "",
                idx + 1,
            )
        )
        for idx, _ in enumerate(media_rows[:5])
    )
    media_slider_html = format_html(
        '<div class="obj-media-carousel-shell">'
        '<div class="obj-head">'
        '<div>'
        '<span class="obj-label">Media Slider</span>'
        '<h2>Auto Preview</h2>'
        '</div>'
        '<div class="obj-badges">'
        '<span class="obj-badge">Auto Rotate</span>'
        '<span class="obj-badge">Click Preview</span>'
        '</div>'
        '</div>'
        '<div id="propertyMediaCarousel" class="carousel slide obj-media-carousel" data-bs-ride="carousel" data-bs-interval="2800" data-bs-pause="hover">'
        '<div class="carousel-indicators obj-media-indicators">{}</div>'
        '<div class="carousel-inner">{}</div>'
        '<button class="carousel-control-prev obj-media-control" type="button" data-bs-target="#propertyMediaCarousel" data-bs-slide="prev">'
        '<span class="carousel-control-prev-icon" aria-hidden="true"></span><span class="visually-hidden">Previous</span>'
        '</button>'
        '<button class="carousel-control-next obj-media-control" type="button" data-bs-target="#propertyMediaCarousel" data-bs-slide="next">'
        '<span class="carousel-control-next-icon" aria-hidden="true"></span><span class="visually-hidden">Next</span>'
        '</button>'
        '</div>'
        '</div>',
        mark_safe(media_slider_indicators_html) if media_slider_indicators_html else mark_safe(""),
        mark_safe(media_slider_items_html) if media_slider_items_html else mark_safe(""),
    )

    deal_options_html = "".join(
        str(
            format_html(
                '<option value="{}"{}>Deal #{} | {} | Rs {}</option>',
                deal.id,
                " selected" if primary_deal and deal.id == primary_deal.id else "",
                deal.id,
                deal.status.title(),
                deal.deal_amount,
            )
        )
        for deal in deal_rows
    )
    gateway_options_html = "".join(
        str(format_html('<option value="{}">{}</option>', gateway, label))
        for gateway, label in PaymentOrder.Gateway.choices
    )
    current_amount_value = primary_deal.deal_amount if primary_deal else property_obj.price
    def _person_label(person, fallback):
        if not person:
            return fallback
        user_obj = getattr(person, "user", None)
        if user_obj:
            full_name = getattr(user_obj, "get_full_name", lambda: "")()
            return full_name or getattr(user_obj, "email", "") or fallback
        full_name = getattr(person, "get_full_name", lambda: "")()
        return full_name or getattr(person, "email", "") or fallback

    primary_customer_label = _person_label(getattr(primary_deal, "customer", None), "Pending")
    primary_lead_obj = getattr(primary_deal, "lead", None) if primary_deal else None
    if primary_lead_obj:
        primary_lead_label = primary_lead_obj.name or primary_lead_obj.mobile or f"Lead #{primary_lead_obj.id}"
    else:
        primary_lead_label = "Pending"
    primary_agent_label = getattr(primary_deal, "agent", None).name if primary_deal and primary_deal.agent_id else "Pending"
    primary_status_label = primary_deal.status.title() if primary_deal else "Pending"
    primary_payment_label = latest_invoice.get_status_display() if latest_invoice else "Pending"
    primary_commission_label = "Settled" if latest_commission and latest_commission.settled else "Pending"
    deal_mapping_html = format_html(
        '<div class="obj-custom-block" style="display:grid;gap:12px;">'
        '<div class="obj-empty">Is section me property ka exact deal mapping dikh raha hai: kis lead, customer, aur agent ke saath deal bani.</div>'
        '<div class="obj-meta">'
        '<div><span>Property</span><strong>{}</strong></div>'
        '<div><span>Lead</span><strong>{}</strong></div>'
        '<div><span>Customer</span><strong>{}</strong></div>'
        '<div><span>Agent</span><strong>{}</strong></div>'
        '<div><span>Deal Amount</span><strong>Rs {}</strong></div>'
        '<div><span>Status</span><strong>{}</strong></div>'
        '<div><span>Payment</span><strong>{}</strong></div>'
        '<div><span>Commission</span><strong>{}</strong></div>'
        '</div>'
        '<div class="obj-actions">'
        '<a class="obj-btn" href="{}">Open Deal Workspace</a>'
        '<a class="obj-btn dark" href="{}">Open Lead CRM</a>'
        '</div>'
        '</div>',
        property_obj.title,
        primary_lead_label,
        primary_customer_label,
        primary_agent_label,
        primary_deal.deal_amount if primary_deal else property_obj.price,
        primary_status_label,
        primary_payment_label,
        primary_commission_label,
        reverse("accounts:deal_workspace", args=[primary_deal.id]) if primary_deal else "",
        reverse("accounts:lead_workspace", args=[primary_deal.lead_id]) if primary_deal and primary_deal.lead_id else "",
    )
    map_card_html = format_html(
        '<div class="obj-custom-block" style="display:grid;gap:12px;">'
        '<iframe title="Google Maps" src="{}" loading="lazy" referrerpolicy="no-referrer-when-downgrade" style="width:100%;min-height:280px;border:0;border-radius:16px;background:#e2e8f0;"></iframe>'
        '<div class="obj-actions">'
        '<a class="obj-btn" target="_blank" rel="noopener" href="{}">Open Google Maps</a>'
        '<a class="obj-btn dark" target="_blank" rel="noopener" href="{}">MapMyIndia Demo</a>'
        '</div>'
        '<div class="obj-empty">Location query: {}</div>'
        '</div>',
        google_map_embed_url or "about:blank",
        google_map_url,
        mapmyindia_url,
        map_query or "Not available",
    )
    media_upload_html = format_html(
        '<div class="obj-custom-block" style="display:grid;gap:12px;">'
        '{}'
        '<div class="obj-media-showcase">'
        '<div class="obj-media-showcase-head">'
        '<div>'
        '<span class="obj-label">Media Showcase</span>'
        '<h3>Featured Image + Video</h3>'
        '</div>'
        '<div class="obj-badges">'
        '<span class="obj-badge">Primary: {}</span>'
        '<span class="obj-badge">Media Count: {}</span>'
        '</div>'
        '</div>'
        '<div class="obj-media-showcase-grid">'
        '<a class="obj-media-feature obj-lightbox-trigger" href="{}" target="_blank" rel="noopener" onclick="if (window.ObjLightbox) return window.ObjLightbox.open(this);" data-lightbox-kind="image" data-lightbox-src="{}" data-lightbox-title="{}" data-lightbox-meta="Featured image" data-lightbox-poster="{}">'
        '{}'
        '<span class="obj-mini-overlay primary"><i class="bi bi-image"></i>Featured Image</span>'
        '</a>'
        '<div class="obj-media-feature obj-lightbox-trigger" role="button" tabindex="0" onclick="if (window.ObjLightbox) return window.ObjLightbox.open(this);" data-lightbox-kind="video" data-lightbox-src="{}" data-lightbox-title="{}" data-lightbox-meta="Walkthrough video" data-lightbox-poster="{}">'
        '{}'
        '<span class="obj-mini-overlay"><i class="bi bi-play-circle"></i>Walkthrough Preview</span>'
        '</div>'
        '</div>'
        '<div class="obj-thumb-strip">{}</div>'
        '</div>'
        '<form method="post" enctype="multipart/form-data" class="eco-lead-toolbar" style="margin:0;">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
        '<input type="hidden" name="action" value="upload_property_image">'
        '<div class="eco-lead-filter-grid">'
        '<div class="eco-field span-2"><label for="property_image_file">Image File</label><input id="property_image_file" type="file" name="image" accept="image/*"></div>'
        '<div class="eco-field span-2"><label for="property_image_url">Image URL</label><input id="property_image_url" type="url" name="image_url" placeholder="https://example.com/property.jpg"></div>'
        '<div class="eco-field span-2"><label for="property_image_caption">Caption</label><input id="property_image_caption" type="text" name="caption" placeholder="Front view, sample shot"></div>'
        '<div class="eco-field"><label for="property_image_sort">Sort Order</label><input id="property_image_sort" type="number" min="0" name="sort_order" value="0"></div>'
        '<div class="eco-field"><label for="property_image_primary">Primary</label><select id="property_image_primary" name="is_primary"><option value="0">No</option><option value="1">Yes</option></select></div>'
        '</div>'
        '<div class="eco-lead-toolbar-foot"><div class="eco-lead-count"><strong>Image</strong><span>upload demo</span></div><div class="eco-inline-actions"><button type="submit" class="eco-action-btn"><i class="bi bi-image"></i>Save Image</button></div></div>'
        '</form>'
        '<form method="post" enctype="multipart/form-data" class="eco-lead-toolbar" style="margin:0;">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
        '<input type="hidden" name="action" value="upload_property_video">'
        '<div class="eco-lead-filter-grid">'
        '<div class="eco-field span-2"><label for="property_video_file">Video File</label><input id="property_video_file" type="file" name="video" accept="video/*"></div>'
        '<div class="eco-field span-2"><label for="property_video_url">Video URL</label><input id="property_video_url" type="url" name="video_url" placeholder="https://example.com/walkthrough.mp4"></div>'
        '<div class="eco-field span-2"><label for="property_video_caption">Caption</label><input id="property_video_caption" type="text" name="caption" placeholder="Walkthrough tour, sample clip"></div>'
        '</div>'
        '<div class="eco-lead-toolbar-foot"><div class="eco-lead-count"><strong>Video</strong><span>upload demo</span></div><div class="eco-inline-actions"><button type="submit" class="eco-action-btn"><i class="bi bi-camera-video"></i>Save Video</button></div></div>'
        '</form>'
        '</div>',
        media_slider_html,
        featured_image["title"] if featured_image else "None",
        len(media_rows),
        featured_image["href"] if featured_image else "about:blank",
        featured_image["href"] if featured_image else "about:blank",
        featured_image["title"] if featured_image else "Featured image",
        featured_image["thumb_url"] if featured_image else "about:blank",
        format_html('<img src="{}" alt="{}" loading="lazy">', featured_image["thumb_url"], featured_image["title"]) if featured_image else format_html('<div class="obj-mini-media-fallback"><i class="bi bi-image"></i></div>'),
        featured_video["href"] if featured_video else "about:blank",
        featured_video["title"] if featured_video else "Walkthrough video",
        featured_video.get("poster_url") if featured_video else "about:blank",
        format_html(
            '<video controls playsinline preload="metadata"><source src="{}"></video>',
            featured_video["href"],
        ) if featured_video else format_html('<div class="obj-mini-media-fallback"><i class="bi bi-file-earmark-play"></i></div>'),
        mark_safe(media_thumb_html) if media_thumb_html else format_html('<div class="obj-empty">No media yet.</div>'),
        csrf_token,
        csrf_token,
    )
    if _is_admin_actor(request.user):
        payment_html = format_html(
            '<div class="obj-custom-block" style="display:grid;gap:12px;">'
            '<form method="post" class="eco-lead-toolbar" style="margin:0;">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
            '<input type="hidden" name="action" value="generate_payment_link">'
            '<div class="eco-lead-filter-grid">'
            '<div class="eco-field span-2"><label for="property_payment_deal">Deal</label><select id="property_payment_deal" name="deal_id" required><option value="">Select deal</option>{}</select></div>'
            '<div class="eco-field"><label for="property_payment_amount">Amount</label><input id="property_payment_amount" type="number" step="0.01" min="0" name="amount" value="{}"></div>'
            '<div class="eco-field"><label for="property_payment_gateway">Gateway</label><select id="property_payment_gateway" name="gateway">{}</select></div>'
            '</div>'
            '<div class="eco-lead-toolbar-foot"><div class="eco-lead-count"><strong>Payment</strong><span>invoice + link</span></div><div class="eco-inline-actions"><button type="submit" class="eco-action-btn"><i class="bi bi-credit-card"></i>Generate Link</button></div></div>'
            '</form>'
            '<form method="post" class="eco-lead-toolbar" style="margin:0;">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
            '<input type="hidden" name="action" value="release_commission">'
            '<div class="eco-lead-filter-grid">'
            '<div class="eco-field span-2"><label for="property_commission_deal">Deal</label><select id="property_commission_deal" name="deal_id" required><option value="">Select deal</option>{}</select></div>'
            '</div>'
            '<div class="eco-lead-toolbar-foot"><div class="eco-lead-count"><strong>Commission</strong><span>release after payment</span></div><div class="eco-inline-actions"><button type="submit" class="eco-action-btn"><i class="bi bi-check2-circle"></i>Release Commission</button></div></div>'
            '</form>'
            '</div>',
            csrf_token,
            mark_safe(deal_options_html),
            current_amount_value,
            mark_safe(gateway_options_html),
            csrf_token,
            mark_safe(deal_options_html),
        )
    else:
        payment_html = format_html(
            '<div class="obj-empty">Payment link and commission release are admin-only. Admin dashboard se lead payment collect aur commission settle ki ja sakti hai.</div>'
        )
    context = _default_workspace_context(
        request,
        title=property_obj.title,
        kicker="Property Workspace",
        copy="Property inventory, enquiries, conversion status, assigned agent, geo signal, aur nearby matching demand yahan visible hai.",
        actions=[
            {"label": "Back To Properties", "href": f"{reverse('accounts:dashboard')}?tab=properties#module-workspace"},
            {"label": "Google Map", "href": google_map_url},
            {"label": "MapMyIndia Demo", "href": mapmyindia_url},
            {"label": "Assigned Agent", "href": reverse("accounts:agent_workspace", args=[property_obj.assigned_agent_id]) if property_obj.assigned_agent_id else ""},
            {"label": "Admin Record", "href": f"/superadmin/leads/property/{property_obj.id}/change/" if request.user.is_staff else ""},
        ],
        badges=[
            {"label": "City", "value": property_obj.city or "-"},
            {"label": "Type", "value": property_obj.property_type.title()},
            {"label": "Status", "value": property_obj.status.title()},
            {"label": "Map", "value": (getattr(settings, "CRM_MAP_PROVIDER", "") or getattr(settings, "MAP_PROVIDER", "") or "google_maps").replace("_", " ").title()},
            {"label": "Media", "value": f"{len(media_rows)} Items"},
            {"label": "Invoice", "value": latest_invoice.invoice_number if latest_invoice else "Pending"},
            {"label": "Payment", "value": latest_invoice.get_status_display() if latest_invoice else "Pending"},
            {"label": "Commission", "value": "Settled" if latest_commission and latest_commission.settled else "Pending"},
        ],
        stats=[
            {"label": "Price", "value": f"Rs {property_obj.price}", "note": property_obj.listing_type.title()},
            {"label": "Inquiries", "value": property_obj.inquiries.count(), "note": "Leads linked to this property"},
            {"label": "Deals", "value": property_obj.deals.count(), "note": "Open + closed property deals"},
            {"label": "Views", "value": property_obj.views.count(), "note": f"Local demand signal {local_lead_count}"},
        ],
        main_sections=[
            {
                "kicker": "Inquiry Pipeline",
                "title": "Lead Queue For This Property",
                "items": [
                    {
                        "title": lead.name or lead.mobile,
                        "href": reverse("accounts:lead_workspace", args=[lead.id]),
                        "subtitle": f"{lead.get_status_display()} | {lead.get_stage_display()} | Rs {lead.budget or 0}",
                        "meta": lead.assigned_agent.name if lead.assigned_agent_id else "Unassigned",
                    }
                    for lead in inquiry_rows
                ],
                "empty": "Is property par abhi koi lead attached nahi hai.",
            },
            {
                "kicker": "Deal Flow",
                "title": "Property Deals",
                "items": [
                    {
                        "title": deal.lead.name if deal.lead_id and deal.lead else f"Deal #{deal.id}",
                        "href": reverse("accounts:deal_workspace", args=[deal.id]),
                        "subtitle": f"Rs {deal.deal_amount} | {deal.status.title()} | {deal.stage.title()}",
                        "meta": (
                            f"Customer: {_person_label(getattr(deal, 'customer', None), 'Pending')} | "
                            f"Agent: {deal.agent.name if deal.agent_id else '-'}"
                        ),
                    }
                    for deal in deal_rows
                ],
                "empty": "Is property ke liye abhi koi deal workspace available nahi hai.",
            },
        ],
        side_sections=[
            {
                "kicker": "Property Profile",
                "title": "Identity + Geo",
                "kv_rows": [
                    {"label": "Builder", "value": property_obj.builder.company_name if property_obj.builder_id and property_obj.builder else "Independent"},
                    {"label": "Location", "value": property_obj.location or property_obj.city or "-"},
                    {"label": "District", "value": property_obj.district or "-"},
                    {"label": "Pin Code", "value": property_obj.pin_code or "-"},
                    {"label": "Assigned Agent", "value": property_obj.assigned_agent.name if property_obj.assigned_agent_id else "Not assigned"},
                    {"label": "Bedrooms", "value": property_obj.bedrooms or "-"},
                ],
            },
            {
                "kicker": "Similar Stock",
                "title": "Nearby Properties",
                "items": [
                    {
                        "title": item.title,
                        "href": reverse("accounts:property_workspace", args=[item.id]),
                        "subtitle": f"{item.city or '-'} | Rs {item.price}",
                        "meta": item.status.title(),
                    }
                    for item in similar_rows
                ],
                "empty": "Nearby inventory suggestions yahan dikhenge.",
            },
            {
                "kicker": "Live Map",
                "title": "Google + MapMyIndia",
                "html": map_card_html,
            },
            {
                "kicker": "Media Vault",
                "title": "Images + Video Uploads",
                "html": media_upload_html,
                "cards": media_rows,
                "mosaic": True,
                "empty": "Is property ke media uploads yahan preview honge.",
            },
            {
                "kicker": "Deal Mapping",
                "title": "Property + Lead + Customer + Agent",
                "html": deal_mapping_html,
                "kv_rows": [
                    {"label": "Property", "value": property_obj.title},
                    {"label": "Lead", "value": primary_lead_label},
                    {"label": "Customer", "value": primary_customer_label},
                    {"label": "Agent", "value": primary_agent_label},
                    {"label": "Status", "value": primary_status_label},
                    {"label": "Payment", "value": primary_payment_label},
                ],
                "empty": "Deal mapping yahan clearly dikhai dega.",
            },
            {
                "kicker": "Payment Desk",
                "title": "Invoice + Commission Release",
                "html": payment_html,
                "kv_rows": [
                    {"label": "Primary Deal", "value": f"Deal #{primary_deal.id}" if primary_deal else "No deal"},
                    {"label": "Latest Invoice", "value": latest_invoice.invoice_number if latest_invoice else "Not generated"},
                    {"label": "Payment", "value": latest_invoice.get_status_display() if latest_invoice else "Pending"},
                    {"label": "Commission", "value": "Settled" if latest_commission and latest_commission.settled else "Pending"},
                ],
                "empty": "Payment और commission flow yahan start hoga.",
            },
        ],
    )
    context["workspace_summary_tiles"] = [
        {"label": "Media", "value": len(media_rows), "note": "Uploaded assets"},
        {"label": "Primary Image", "value": sum(1 for row in property_image_rows if row.get("is_primary")), "note": "Featured shots"},
        {"label": "Videos", "value": len(property_video_rows), "note": "Walkthroughs"},
        {"label": "Invoice", "value": latest_invoice.invoice_number if latest_invoice else "Pending", "note": "Payment billing"},
        {"label": "Payment", "value": latest_invoice.get_status_display() if latest_invoice else "Pending", "note": "Gateway status"},
        {"label": "Commission", "value": "Settled" if latest_commission and latest_commission.settled else "Pending", "note": "Release state"},
    ]
    context["can_manage_property_finance"] = _is_admin_actor(request.user)
    context["property_map_query"] = map_query
    context["property_image_rows"] = property_image_rows
    context["property_video_rows"] = property_video_rows
    context["property_media_rows"] = media_rows
    context["primary_deal"] = primary_deal
    context["latest_invoice"] = latest_invoice
    context["latest_payment_order"] = latest_payment_order
    context["latest_commission"] = latest_commission
    context["property"] = property_obj
    return render(request, "accounts/object_workspace.html", context)


@login_required
@feature_required("crm.deals")
def deal_workspace(request, deal_id):
    from deals.models import Payment

    deal = get_object_or_404(_crm_deal_queryset_for_user(request.user), pk=deal_id)
    payment_rows = list(deal.payments.select_related("agent", "customer", "approved_by").order_by("-created_at")[:10])
    def _customer_label(customer):
        if not customer:
            return "Pending"
        customer_user = getattr(customer, "user", None)
        full_name = getattr(customer_user, "get_full_name", lambda: "")() if customer_user else ""
        return full_name or getattr(customer_user, "email", "") or f"Customer #{getattr(customer, 'id', '')}"

    def _lead_label(lead):
        if not lead:
            return "Pending"
        return lead.name or lead.mobile or f"Lead #{lead.id}"

    def _property_label(property_obj):
        if not property_obj:
            return "Not mapped"
        return property_obj.title

    context = _default_workspace_context(
        request,
        title=f"Deal #{deal.id}",
        kicker="Deal Workspace",
        copy="Deal amount, commission, payout status, customer payment flow, linked lead, aur agent performance yahan ek jagah visible hai.",
        actions=[
            {"label": "Back To Deals", "href": f"{reverse('accounts:dashboard')}?tab=deals#module-workspace"},
            {"label": "Lead CRM", "href": reverse("accounts:lead_workspace", args=[deal.lead_id]) if deal.lead_id else ""},
            {"label": "Agent Dashboard", "href": reverse("accounts:agent_workspace", args=[deal.agent_id]) if deal.agent_id else ""},
        ],
        badges=[
            {"label": "Status", "value": deal.status.title()},
            {"label": "Stage", "value": deal.stage.title()},
            {"label": "Customer", "value": _customer_label(deal.customer)},
            {"label": "Property", "value": _property_label(deal.property)},
        ],
        stats=[
            {"label": "Deal Amount", "value": f"Rs {deal.deal_amount}", "note": "Gross deal value"},
            {"label": "Commission", "value": f"Rs {deal.commission_amount}", "note": f"Rate {deal.commission_rate}%"},
            {"label": "Payments", "value": len(payment_rows), "note": "Customer + payout records"},
            {"label": "Closing Date", "value": deal.closing_date or "-", "note": deal.closed_at.strftime('%d %b %Y %H:%M') if deal.closed_at else "Open"},
        ],
        main_sections=[
            {
                "kicker": "Deal Mapping",
                "title": "Property + Lead + Customer + Agent",
                "kv_rows": [
                    {"label": "Property", "value": _property_label(deal.property)},
                    {"label": "Lead", "value": _lead_label(deal.lead)},
                    {"label": "Customer", "value": _customer_label(deal.customer)},
                    {"label": "Agent", "value": deal.agent.name if deal.agent_id else "Pending"},
                    {"label": "Status", "value": deal.status.title()},
                    {"label": "Stage", "value": deal.stage.title()},
                ],
                "empty": "Is deal ka mapping yahan clearly dikhai dega.",
            },
            {
                "kicker": "Payment Ledger",
                "title": "Deal Payments",
                "items": [
                    {
                        "title": f"{payment.payment_type.replace('_', ' ').title()} | Rs {payment.amount}",
                        "href": f"/superadmin/deals/payment/{payment.id}/change/" if request.user.is_staff else "",
                        "subtitle": f"{payment.direction.title()} | {payment.status.title()} | {payment.reference or 'No ref'}",
                        "meta": payment.agent.name if payment.agent_id else (payment.customer.user.email if payment.customer_id and payment.customer else "-"),
                    }
                    for payment in payment_rows
                ],
                "empty": "Is deal ke payment rows abhi empty hain.",
            },
            {
                "kicker": "Linked Records",
                "title": "Connected CRM Objects",
                "items": [
                    {
                        "title": deal.lead.name or deal.lead.mobile,
                        "href": reverse("accounts:lead_workspace", args=[deal.lead_id]),
                        "subtitle": f"{deal.lead.get_status_display()} | {deal.lead.get_stage_display()}",
                        "meta": "Lead CRM",
                    },
                    *(
                        [{
                            "title": deal.property.title,
                            "href": reverse("accounts:property_workspace", args=[deal.property_id]),
                            "subtitle": f"{deal.property.city or '-'} | Rs {deal.property.price}",
                            "meta": "Property Workspace",
                        }]
                        if deal.property_id and deal.property else []
                    ),
                ],
                "empty": "Linked CRM records available nahi hain.",
            },
        ],
        side_sections=[
            {
                "kicker": "Commission",
                "title": "Split + Settlement",
                "kv_rows": [
                    {"label": "Company Share", "value": f"{deal.company_share_percent}%"},
                    {"label": "Agent Share", "value": f"{deal.agent_share_percent}%"},
                    {"label": "Commission Total", "value": getattr(getattr(deal, "commission", None), "total_amount", deal.commission_amount)},
                    {"label": "Agent Amount", "value": getattr(getattr(deal, "commission", None), "agent_amount", "-")},
                    {"label": "Admin Amount", "value": getattr(getattr(deal, "commission", None), "admin_amount", "-")},
                    {"label": "Settled", "value": "Yes" if getattr(getattr(deal, "commission", None), "settled", False) else "No"},
                ],
            },
            {
                "kicker": "Payout Signals",
                "title": "Payment Summary",
                "kv_rows": [
                    {"label": "Inbound", "value": sum(payment.amount for payment in payment_rows if payment.direction == Payment.Direction.INBOUND)},
                    {"label": "Outbound", "value": sum(payment.amount for payment in payment_rows if payment.direction == Payment.Direction.OUTBOUND)},
                    {"label": "Pending", "value": sum(payment.amount for payment in payment_rows if payment.status == Payment.Status.PENDING)},
                    {"label": "Paid", "value": sum(payment.amount for payment in payment_rows if payment.status == Payment.Status.PAID)},
                ],
            },
            {
                "kicker": "Linked Chain",
                "title": "Property Trace",
                "items": [
                    {
                        "title": _property_label(deal.property),
                        "href": reverse("accounts:property_workspace", args=[deal.property_id]) if deal.property_id else "",
                        "subtitle": f"{deal.property.city or '-'} | Rs {deal.property.price}" if deal.property else "Not mapped",
                        "meta": "Property",
                    },
                    {
                        "title": _lead_label(deal.lead),
                        "href": reverse("accounts:lead_workspace", args=[deal.lead_id]) if deal.lead_id else "",
                        "subtitle": f"{deal.lead.get_status_display()} | {deal.lead.get_stage_display()}" if deal.lead else "Pending",
                        "meta": "Lead",
                    },
                    {
                        "title": _customer_label(deal.customer),
                        "href": "",
                        "subtitle": "Mapped customer profile",
                        "meta": "Customer",
                    },
                ],
            },
        ],
    )
    context["deal"] = deal
    return render(request, "accounts/object_workspace.html", context)


@login_required
@feature_required("crm.agents")
def agent_workspace(request, agent_id):
    from deals.models import Deal, Payment
    from agents.hierarchy import ensure_wallet
    from leads.models import Lead

    agent = get_object_or_404(_crm_agent_queryset_for_user(request.user), pk=agent_id)
    assigned_leads = list(Lead.objects.filter(assigned_agent=agent).order_by("-updated_at")[:10])
    deal_rows = list(Deal.objects.filter(agent=agent).select_related("lead", "property").order_by("-updated_at")[:8])
    payout_rows = list(
        Payment.objects.filter(agent=agent).select_related("deal", "lead").order_by("-created_at")[:10]
    )
    wallet = ensure_wallet(agent)
    coverage_rows = list(agent.coverage_areas.filter(is_active=True).order_by("-is_primary", "state", "district")[:8])
    context = _default_workspace_context(
        request,
        title=agent.name or getattr(agent.user, "username", f"Agent {agent.id}"),
        kicker="Agent Workspace",
        copy="Agent profile, coverage zones, lead pipeline, deal closure, payouts, wallet balance, aur live location signals yahan visible hain.",
        actions=[
            {"label": "Back To Agents", "href": f"{reverse('accounts:dashboard')}?tab=agents#module-workspace"},
            {"label": "Wallet Dashboard", "href": reverse("accounts:wallet_workspace")},
            {"label": "Admin Record", "href": f"/superadmin/agents/agent/{agent.id}/change/" if request.user.is_staff else ""},
        ],
        badges=[
            {"label": "Approval", "value": agent.approval_status.title()},
            {"label": "KYC", "value": "Verified" if agent.kyc_verified else "Pending"},
            {"label": "Specialization", "value": agent.specialization.title()},
            {"label": "Map", "value": (getattr(settings, "CRM_MAP_PROVIDER", "") or getattr(settings, "MAP_PROVIDER", "") or "google_maps").replace("_", " ").title()},
        ],
        stats=[
            {"label": "Open Leads", "value": Lead.objects.filter(assigned_agent=agent).exclude(status__in=[Lead.Status.CLOSED, Lead.Status.CONVERTED, Lead.Status.LOST]).count(), "note": "Active routing load"},
            {"label": "Deals", "value": len(deal_rows), "note": "Recent linked deals"},
            {"label": "Wallet", "value": f"Rs {wallet.balance}", "note": f"Locked Rs {wallet.locked_balance}"},
            {"label": "Payouts", "value": f"Rs {sum(payment.amount for payment in payout_rows if payment.direction == Payment.Direction.OUTBOUND)}", "note": "Agent payout queue"},
        ],
        main_sections=[
            {
                "kicker": "Assigned Leads",
                "title": "Agent CRM Queue",
                "items": [
                    {
                        "title": lead.name or lead.mobile,
                        "href": reverse("accounts:lead_workspace", args=[lead.id]),
                        "subtitle": f"{lead.get_status_display()} | {lead.get_stage_display()} | Rs {lead.budget or 0}",
                        "meta": lead.city or lead.preferred_location or "-",
                    }
                    for lead in assigned_leads
                ],
                "empty": "Agent ke paas abhi koi active lead nahi hai.",
            },
            {
                "kicker": "Deal Performance",
                "title": "Agent Deals",
                "items": [
                    {
                        "title": f"Deal #{deal.id} | Rs {deal.deal_amount}",
                        "href": reverse("accounts:deal_workspace", args=[deal.id]),
                        "subtitle": f"{deal.status.title()} | {deal.stage.title()}",
                        "meta": deal.lead.name if deal.lead_id and deal.lead else "-",
                    }
                    for deal in deal_rows
                ],
                "empty": "Recent deal records yahan dikhenge.",
            },
        ],
        side_sections=[
            {
                "kicker": "Coverage",
                "title": "Geo Zones",
                "items": [
                    {
                        "title": coverage.pin_code or coverage.city or coverage.district or coverage.state or f"Area {coverage.id}",
                        "href": f"/superadmin/agents/agentcoveragearea/{coverage.id}/change/" if request.user.is_staff else "",
                        "subtitle": " | ".join([part for part in [coverage.village, coverage.tehsil, coverage.city, coverage.district, coverage.state] if part]),
                        "meta": "Primary" if coverage.is_primary else "Secondary",
                    }
                    for coverage in coverage_rows
                ],
                "empty": "Coverage zones mapped nahi hain.",
            },
            {
                "kicker": "Wallet + Location",
                "title": "Ops Snapshot",
                "kv_rows": [
                    {"label": "Balance", "value": wallet.balance},
                    {"label": "Total Earned", "value": wallet.total_earned},
                    {"label": "Withdrawn", "value": wallet.total_withdrawn},
                    {"label": "Current Lat", "value": agent.current_latitude or agent.last_latitude or "-"},
                    {"label": "Current Lng", "value": agent.current_longitude or agent.last_longitude or "-"},
                    {"label": "Last Ping", "value": agent.last_ping_at or "-"},
                ],
            },
        ],
    )
    context["agent"] = agent
    context["agent_wallet"] = wallet
    return render(request, "accounts/object_workspace.html", context)


def _wallet_workspace_payload(user, *, base_url=""):
    cache_key = f"wallet_workspace_payload:{getattr(user, 'pk', user)}:{getattr(getattr(user, 'agent_profile', None), 'pk', 'none')}:{base_url}"
    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        return cached_payload

    from agents.hierarchy import ensure_wallet
    from deals.models import Payment
    from rewards.models import ReferralEvent, RewardRule, ScratchCard, SpinHistory, SpinRewardOption
    from rewards.services import build_referral_share_context, get_or_create_reward_coin, issue_scratch_cards
    from wallet.models import WalletAccount, WalletLedger, WalletTransfer, WithdrawRequest
    from wallet.services import get_wallet_summary, sync_profile_payment_accounts

    sync_profile_payment_accounts(user)
    wallet_summary = get_wallet_summary(user)
    user_wallet = wallet_summary["wallet"]
    agent_profile = getattr(user, "agent_profile", None)
    agent_wallet = ensure_wallet(agent_profile) if agent_profile else None

    withdraw_rows = list(
        user_wallet.withdraw_requests.select_related("destination_account", "processed_by").order_by("-requested_at")[:10]
    )
    user_txn_rows = list(
        user_wallet.transactions.select_related("counterparty_wallet", "counterparty_wallet__user").order_by("-created_at")[:12]
    )
    ledger_rows = list(
        WalletLedger.objects.select_related("transaction", "actor").filter(wallet=user_wallet).order_by("-created_at")[:10]
    )
    agent_txn_rows = list(agent_profile.wallet_transactions.order_by("-created_at")[:10]) if agent_profile else []
    transfer_rows = list(
        WalletTransfer.objects.select_related(
            "sender_wallet",
            "receiver_wallet",
            "sender_wallet__user",
            "receiver_wallet__user",
            "sender_account",
            "receiver_account",
        )
        .filter(Q(sender_wallet=user_wallet) | Q(receiver_wallet=user_wallet))
        .order_by("-created_at")[:10]
    )
    linked_accounts = list(
        WalletAccount.objects.select_related("linked_wallet")
        .filter(user=user)
        .order_by("-is_default", "-updated_at")[:12]
    )
    reward_coin = get_or_create_reward_coin(user)
    reward_txn_rows = list(reward_coin.transactions.order_by("-created_at")[:12])
    reward_rules = list(RewardRule.objects.filter(is_active=True).order_by("key"))
    spin_options = list(SpinRewardOption.objects.filter(is_active=True).order_by("-weight", "id"))
    referral_rows = list(
        ReferralEvent.objects.select_related("referrer", "referred_user", "referrer_reward", "invitee_reward")
        .filter(Q(referrer=user) | Q(referred_user=user))
        .order_by("-created_at")[:12]
    )
    scratch_rows = list(ScratchCard.objects.filter(user=user).order_by("-created_at")[:10])
    spin_rows = list(SpinHistory.objects.select_related("option").filter(user=user).order_by("-created_at")[:10])

    if getattr(settings, "DESKTOP_MODE", False) or getattr(settings, "RUNNING_RUNSERVER", False):
        seeded = False
        if reward_coin.available_spins <= 0 and not spin_rows:
            reward_coin.available_spins = 1
            reward_coin.save(update_fields=["available_spins", "updated_at"])
            seeded = True
        if reward_coin.available_scratch_cards <= 0 and not scratch_rows:
            issue_scratch_cards(user, count=1, metadata={"source": "desktop_demo"})
            seeded = True
        if seeded:
            reward_coin.refresh_from_db()
            scratch_rows = list(ScratchCard.objects.filter(user=user).order_by("-created_at")[:10])
            spin_rows = list(SpinHistory.objects.select_related("option").filter(user=user).order_by("-created_at")[:10])
    payout_rows = list(Payment.objects.filter(agent=agent_profile).order_by("-created_at")[:10]) if agent_profile else []
    pending_withdraw_rows = (
        list(
            WithdrawRequest.objects.select_related("user", "wallet", "destination_account")
            .filter(status__in=[WithdrawRequest.Status.PENDING, WithdrawRequest.Status.APPROVED])
            .order_by("-requested_at")[:12]
        )
        if user.is_staff or user.is_superuser
        else []
    )

    credit_total = sum((txn.amount for txn in user_txn_rows if txn.entry_type == "credit"), Decimal("0.00"))
    debit_total = sum((txn.amount for txn in user_txn_rows if txn.entry_type == "debit"), Decimal("0.00"))

    return {
        "user_wallet": user_wallet,
        "wallet_summary": wallet_summary,
        "wallet_credit_total": credit_total,
        "wallet_debit_total": debit_total,
        "wallet_ledger_rows": ledger_rows,
        "agent_wallet": agent_wallet,
        "withdraw_rows": withdraw_rows,
        "pending_withdraw_rows": pending_withdraw_rows,
        "user_txn_rows": user_txn_rows,
        "agent_txn_rows": agent_txn_rows,
        "transfer_rows": transfer_rows,
        "linked_accounts": linked_accounts,
        "reward_coin": reward_coin,
        "reward_rules": reward_rules,
        "reward_txn_rows": reward_txn_rows,
        "spin_options": [
            {
                "id": option.id,
                "label": option.label,
                "reward_type": option.reward_type,
                "coin_amount": option.coin_amount,
                "wallet_amount": str(option.wallet_amount),
                "weight": option.weight,
            }
            for option in spin_options
        ],
        "referral_rows": referral_rows,
        "referral_share": build_referral_share_context(user, base_url=base_url or getattr(settings, "BASE_URL", "")),
        "scratch_rows": scratch_rows,
        "spin_rows": spin_rows,
        "payout_rows": payout_rows,
    }
    cache.set(cache_key, payload, 60)
    return payload


def _wallet_workspace_cache_key(user, *, base_url=""):
    return f"wallet_workspace_payload:{getattr(user, 'pk', user)}:{getattr(getattr(user, 'agent_profile', None), 'pk', 'none')}:{base_url}"


def _wallet_tabs_for_user(user, wallet_base_url):
    wallet_tabs = [
        {"key": "dashboard", "label": "Wallet Dashboard", "href": f"{wallet_base_url}?tab=dashboard"},
        {"key": "transactions", "label": "Transactions", "href": f"{wallet_base_url}?tab=transactions"},
        {"key": "spin", "label": "Spin Wheel", "href": f"{wallet_base_url}?tab=spin"},
        {"key": "rewards", "label": "Rewards", "href": f"{wallet_base_url}?tab=rewards"},
        {"key": "referrals", "label": "Refer & Earn", "href": f"{wallet_base_url}?tab=referrals"},
        {"key": "scratch", "label": "Scratch Card", "href": f"{wallet_base_url}?tab=scratch"},
    ]
    return wallet_tabs


def _wallet_access_mode(user):
    role = (getattr(user, "role", "") or "").strip().lower()
    if user.is_superuser or user.is_staff:
        return "full"
    if role == "agent":
        return "agent_spin"
    if user_has_feature(user, "crm.wallet"):
        return "full"
    return "denied"


@login_required
def wallet_workspace(request):
    from urllib.parse import urlencode

    access_mode = _wallet_access_mode(request.user)
    if access_mode == "denied":
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "locked", "message": "Wallet workspace is disabled for your plan."}, status=403)
        return redirect("billing:upgrade_plan")

    payload = _wallet_workspace_payload(request.user, base_url=request.build_absolute_uri("/").rstrip("/"))
    active_wallet_tab = (request.GET.get("tab") or "dashboard").strip().lower()
    wallet_base_url = reverse("accounts:wallet_workspace")
    allowed_wallet_tabs = {tab["key"] for tab in _wallet_tabs_for_user(request.user, wallet_base_url)}
    if active_wallet_tab not in allowed_wallet_tabs:
        active_wallet_tab = "dashboard"
    wallet_tabs = _wallet_tabs_for_user(request.user, wallet_base_url)
    statement_filters = {
        "start_date": (request.GET.get("start_date") or "").strip(),
        "end_date": (request.GET.get("end_date") or "").strip(),
        "entry_type": (request.GET.get("entry_type") or "").strip(),
        "source": (request.GET.get("source") or "").strip(),
    }
    statement_query = urlencode({key: value for key, value in statement_filters.items() if value})
    statement_suffix = f"&{statement_query}" if statement_query else ""
    context = {
        **payload,
        "active_wallet_tab": active_wallet_tab,
        "wallet_tabs": wallet_tabs,
        "wallet_action_url": reverse("accounts:wallet_workspace_action"),
        "wallet_spin_url": reverse("accounts:wallet_spin_api"),
        "wallet_scratch_reveal_url": reverse("accounts:wallet_scratch_reveal_api"),
        "wallet_scratch_claim_url": reverse("accounts:wallet_scratch_claim_api"),
        "wallet_statement_csv_url": f"{reverse('wallet-statement')}?format=csv{statement_suffix}",
        "wallet_statement_xlsx_url": f"{reverse('wallet-statement')}?format=xlsx{statement_suffix}",
        "wallet_statement_pdf_url": f"{reverse('wallet-statement')}?format=pdf{statement_suffix}",
        "statement_filters": statement_filters,
        "active_dashboard_tab": "wallet",
    }
    return render(request, "accounts/wallet_workspace.html", context)


@login_required
@require_POST
def wallet_workspace_action(request):
    from rewards.models import ScratchCard
    from rewards.services import award_daily_login_reward, claim_scratch_card, convert_coins_to_wallet, get_or_create_reward_coin, reveal_scratch_card, spin_wheel
    from wallet.models import Wallet, WalletAccount, WithdrawRequest
    from wallet.services import (
        approve_withdrawal,
        create_linked_account,
        credit_wallet,
        mark_withdrawal_paid,
        reject_withdrawal,
        request_withdrawal,
        sync_profile_payment_accounts,
        transfer_between_wallets,
    )

    action = (request.POST.get("action") or "").strip().lower()
    active_tab = (request.POST.get("active_tab") or "dashboard").strip().lower()
    redirect_url = f"{reverse('accounts:wallet_workspace')}?tab={active_tab}"
    force_json_actions = {"spin", "reveal_scratch", "claim_scratch"}
    wants_json = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.POST.get("response_format") == "json"
        or action in force_json_actions
    )
    access_mode = _wallet_access_mode(request.user)
    cache_key = _wallet_workspace_cache_key(
        request.user,
        base_url=request.build_absolute_uri("/").rstrip("/"),
    )
    if access_mode == "denied":
        if wants_json:
            return JsonResponse({"status": "locked", "message": "Wallet workspace is disabled for your plan."}, status=403)
        messages.error(request, "Wallet workspace is disabled for your plan.")
        return redirect("billing:upgrade_plan")

    try:
        agent_allowed_actions = {"spin", "claim_daily_login", "convert_coins", "reveal_scratch", "claim_scratch"}
        if access_mode == "agent_spin" and action not in agent_allowed_actions:
            raise ValueError("Only rewards actions are available in your agent wallet view")

        if action == "spin":
            if access_mode not in {"full", "agent_spin"}:
                raise ValueError("Spin wheel is not available for your plan")
            spin_history = spin_wheel(request.user)
            reward_coin = get_or_create_reward_coin(request.user)
            spin_label = getattr(getattr(spin_history, "option", None), "label", "reward")
            if wants_json:
                return JsonResponse(
                    {
                        "success": True,
                        "spin": {
                            "id": spin_history.id,
                            "label": spin_label,
                            "reward_type": spin_history.reward_type,
                            "coins_awarded": spin_history.coins_awarded,
                            "wallet_amount": str(spin_history.wallet_amount),
                        },
                        "remaining_spins": reward_coin.available_spins,
                    }
                )
            messages.success(request, f"Spin completed. You won {spin_label}.")
        elif action == "add_money":
            amount = Decimal(request.POST.get("amount") or "0")
            credit_wallet(
                request.user,
                amount,
                source="add_money",
                reference="wallet_workspace",
                narration=request.POST.get("note") or "Manual wallet top-up",
                actor=request.user,
            )
            messages.success(request, "Wallet balance updated.")
        elif action == "transfer":
            amount = Decimal(request.POST.get("amount") or "0")
            recipient_wallet_code = (request.POST.get("recipient_wallet_code") or "").strip().upper()
            recipient_wallet = Wallet.objects.select_related("user").filter(wallet_code=recipient_wallet_code).first()
            if not recipient_wallet:
                raise ValueError("Recipient wallet code not found")
            sender_account = WalletAccount.objects.filter(user=request.user, pk=request.POST.get("sender_account_id")).first() if request.POST.get("sender_account_id") else None
            receiver_account = WalletAccount.objects.filter(user=recipient_wallet.user, pk=request.POST.get("receiver_account_id")).first() if request.POST.get("receiver_account_id") else None
            transfer_between_wallets(
                request.user,
                recipient_wallet.user,
                amount,
                note=request.POST.get("note") or "Wallet transfer",
                sender_account=sender_account,
                receiver_account=receiver_account,
                actor=request.user,
            )
            messages.success(request, "Wallet transfer completed.")
        elif action == "withdraw":
            amount = Decimal(request.POST.get("amount") or "0")
            destination_account = WalletAccount.objects.filter(user=request.user, pk=request.POST.get("destination_account_id")).first() if request.POST.get("destination_account_id") else None
            request_withdrawal(request.user, amount, destination_account=destination_account)
            messages.success(request, "Withdrawal request submitted.")
        elif action == "convert_coins":
            coins = int(request.POST.get("coins") or "0")
            convert_coins_to_wallet(request.user, coins)
            messages.success(request, "Coins converted to wallet balance.")
        elif action == "claim_daily_login":
            result = award_daily_login_reward(request.user)
            if result:
                messages.success(request, "Daily login reward claimed.")
            else:
                messages.info(request, "Daily login reward already claimed today.")
        elif action == "reveal_scratch":
            card = get_object_or_404(ScratchCard, pk=request.POST.get("card_id"), user=request.user)
            card = reveal_scratch_card(request.user, card)
            if wants_json:
                return JsonResponse(
                    {
                        "success": True,
                        "scratch": {
                            "id": card.id,
                            "reference_id": str(card.reference_id) if card.reference_id else "",
                            "status": card.status,
                            "title": card.title,
                        },
                    }
                )
            messages.success(request, "Scratch card revealed.")
        elif action == "claim_scratch":
            card = get_object_or_404(ScratchCard, pk=request.POST.get("card_id"), user=request.user)
            card = claim_scratch_card(request.user, card)
            if wants_json:
                return JsonResponse(
                    {
                        "success": True,
                        "scratch": {
                            "id": card.id,
                            "reference_id": str(card.reference_id) if card.reference_id else "",
                            "status": card.status,
                            "title": card.title,
                        },
                    }
                )
            messages.success(request, "Scratch reward claimed.")
        elif action == "sync_accounts":
            sync_profile_payment_accounts(request.user)
            messages.success(request, "Bank, UPI, and internal wallet accounts synced.")
        elif action == "add_account":
            account_type = (request.POST.get("account_type") or "").strip().lower()
            create_linked_account(
                request.user,
                account_type=account_type,
                label=request.POST.get("label") or "",
                beneficiary_name=request.POST.get("beneficiary_name") or "",
                bank_name=request.POST.get("bank_name") or "",
                account_number=request.POST.get("account_number") or "",
                ifsc_code=request.POST.get("ifsc_code") or "",
                upi_id=request.POST.get("upi_id") or "",
                is_default=bool(request.POST.get("is_default")),
                status="verified" if request.user.is_staff else "pending",
            )
            messages.success(request, "Linked account saved.")
        elif action == "approve_withdrawal":
            if not (request.user.is_staff or request.user.is_superuser):
                raise ValueError("Only admin can approve withdrawals")
            withdraw_request = get_object_or_404(WithdrawRequest, pk=request.POST.get("withdraw_request_id"))
            approve_withdrawal(withdraw_request, approver=request.user, payout_reference=request.POST.get("payout_reference") or "")
            messages.success(request, "Withdrawal approved.")
        elif action == "reject_withdrawal":
            if not (request.user.is_staff or request.user.is_superuser):
                raise ValueError("Only admin can reject withdrawals")
            withdraw_request = get_object_or_404(WithdrawRequest, pk=request.POST.get("withdraw_request_id"))
            reject_withdrawal(withdraw_request, approver=request.user, reason=request.POST.get("rejection_reason") or "")
            messages.success(request, "Withdrawal rejected and locked balance released.")
        elif action == "mark_withdrawal_paid":
            if not (request.user.is_staff or request.user.is_superuser):
                raise ValueError("Only admin can settle withdrawals")
            withdraw_request = get_object_or_404(WithdrawRequest, pk=request.POST.get("withdraw_request_id"))
            mark_withdrawal_paid(withdraw_request, approver=request.user, payout_reference=request.POST.get("payout_reference") or "")
            messages.success(request, "Withdrawal marked as paid.")
        else:
            messages.error(request, "Unknown wallet action.")
    except Exception as exc:
        if wants_json:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
        messages.error(request, str(exc))
    finally:
        cache.delete(cache_key)
    return redirect(redirect_url)


if settings.DESKTOP_MODE or settings.RUNNING_RUNSERVER:
    wallet_workspace_action = csrf_exempt(wallet_workspace_action)


@login_required
@require_POST
def wallet_spin_api(request):
    from rewards.services import get_or_create_reward_coin, spin_wheel

    access_mode = _wallet_access_mode(request.user)
    cache_key = _wallet_workspace_cache_key(
        request.user,
        base_url=request.build_absolute_uri("/").rstrip("/"),
    )
    try:
        if access_mode == "denied":
            return JsonResponse({"success": False, "error": "Wallet workspace is disabled for your plan."}, status=403)
        if access_mode not in {"full", "agent_spin"}:
            return JsonResponse({"success": False, "error": "Spin wheel is not available for your plan."}, status=403)

        spin_history = spin_wheel(request.user)
        reward_coin = get_or_create_reward_coin(request.user)
        spin_label = getattr(getattr(spin_history, "option", None), "label", "reward")
        return JsonResponse(
            {
                "success": True,
                "spin": {
                    "id": spin_history.id,
                    "label": spin_label,
                    "reward_type": spin_history.reward_type,
                    "coins_awarded": spin_history.coins_awarded,
                    "wallet_amount": str(spin_history.wallet_amount),
                },
                "remaining_spins": reward_coin.available_spins,
            }
        )
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    finally:
        cache.delete(cache_key)


@login_required
@require_POST
def wallet_scratch_reveal_api(request):
    from rewards.models import ScratchCard
    from rewards.services import reveal_scratch_card

    access_mode = _wallet_access_mode(request.user)
    cache_key = _wallet_workspace_cache_key(
        request.user,
        base_url=request.build_absolute_uri("/").rstrip("/"),
    )
    try:
        if access_mode == "denied":
            return JsonResponse({"success": False, "error": "Wallet workspace is disabled for your plan."}, status=403)
        card = get_object_or_404(ScratchCard, pk=request.POST.get("card_id"), user=request.user)
        card = reveal_scratch_card(request.user, card)
        return JsonResponse(
            {
                "success": True,
                "scratch": {
                    "id": card.id,
                    "reference_id": str(card.reference_id) if card.reference_id else "",
                    "status": card.status,
                    "title": card.title,
                },
            }
        )
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    finally:
        cache.delete(cache_key)


@login_required
@require_POST
def wallet_scratch_claim_api(request):
    from rewards.models import ScratchCard
    from rewards.services import claim_scratch_card

    access_mode = _wallet_access_mode(request.user)
    cache_key = _wallet_workspace_cache_key(
        request.user,
        base_url=request.build_absolute_uri("/").rstrip("/"),
    )
    try:
        if access_mode == "denied":
            return JsonResponse({"success": False, "error": "Wallet workspace is disabled for your plan."}, status=403)
        card = get_object_or_404(ScratchCard, pk=request.POST.get("card_id"), user=request.user)
        card = claim_scratch_card(request.user, card)
        return JsonResponse(
            {
                "success": True,
                "scratch": {
                    "id": card.id,
                    "reference_id": str(card.reference_id) if card.reference_id else "",
                    "status": card.status,
                    "title": card.title,
                },
            }
        )
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    finally:
        cache.delete(cache_key)


@login_required
@feature_required("crm.reports")
def reports_workspace(request):
    crm_dashboard = build_crm_dashboard_context(request.user)
    def _lead_label(lead):
        if not lead:
            return "Pending"
        return lead.name or lead.mobile or f"Lead #{lead.id}"

    def _customer_label(customer):
        if not customer:
            return "Pending"
        customer_user = getattr(customer, "user", None)
        full_name = getattr(customer_user, "get_full_name", lambda: "")() if customer_user else ""
        return full_name or getattr(customer_user, "email", "") or f"Customer #{getattr(customer, 'id', '')}"

    context = _default_workspace_context(
        request,
        title="Reports Workspace",
        kicker="Analytics + Monitoring Dashboard",
        copy="Lead pipeline, conversation health, import activity, assignment pressure, aur conversion visibility yahan full monitoring mode me available hai.",
        actions=[
            {"label": "Back To Reports Tab", "href": f"{reverse('accounts:dashboard')}?tab=reports#module-workspace"},
            {"label": "Lead Queue", "href": f"{reverse('accounts:dashboard')}?tab=leads#module-workspace"},
            {"label": "Admin Logs", "href": "/superadmin/leads/leadactivity/" if request.user.is_staff else ""},
        ],
        badges=[
            {"label": "Conversion", "value": f"{crm_dashboard['snapshot']['conversion_rate']}%"},
            {"label": "Conversations", "value": crm_dashboard["active_conversations"]},
            {"label": "Follow Ups Due", "value": crm_dashboard["followups_due"]},
            {"label": "Unassigned", "value": crm_dashboard["unassigned_leads"]},
        ],
        stats=[
            {"label": "Total Leads", "value": crm_dashboard["total_leads"], "note": "Live CRM volume"},
            {"label": "Converted", "value": crm_dashboard["converted_leads"], "note": "Closed lead count"},
            {"label": "Imports", "value": crm_dashboard["import_batch_count"], "note": "Recent capture batches"},
            {"label": "Assignments", "value": crm_dashboard["auto_assigned_count"], "note": "Auto + manual routing"},
        ],
        main_sections=[
            {
                "kicker": "Deal Trace",
                "title": "Property-to-Deal Map",
                "items": [
                    {
                        "title": f"Deal #{deal.id} | {deal.property.title if deal.property_id and deal.property else 'Not mapped'}",
                        "href": reverse("accounts:deal_workspace", args=[deal.id]),
                        "subtitle": f"Lead: {_lead_label(deal.lead)} | Customer: {_customer_label(deal.customer)}",
                        "meta": deal.agent.name if deal.agent_id else "Unassigned",
                    }
                    for deal in crm_dashboard["recent_deals"]
                ],
                "empty": "Recent property deals yahan dikhengi.",
            },
            {
                "kicker": "Pipeline",
                "title": "Stage Breakdown",
                "items": [
                    {
                        "title": row["label"],
                        "subtitle": f"{row['value']} leads | {row['percentage']}% coverage",
                        "meta": row["tone"].title(),
                    }
                    for row in crm_dashboard["pipeline_rows"]
                ],
                "empty": "Pipeline analytics abhi available nahi hai.",
            },
            {
                "kicker": "Conversations",
                "title": "Recent Communication Logs",
                "items": [
                    {
                        "title": activity.lead.name or activity.lead.mobile,
                        "href": reverse("accounts:lead_workspace", args=[activity.lead_id]),
                        "subtitle": f"{activity.activity_type.replace('_', ' ').title()} | {activity.created_at.strftime('%d %b %Y %H:%M')}",
                        "meta": getattr(activity.actor, "email", "") or getattr(activity.actor, "username", "") or "System",
                    }
                    for activity in crm_dashboard["recent_conversations"]
                ],
                "empty": "Conversation log abhi empty hai.",
            },
        ],
        side_sections=[
            {
                "kicker": "Capture",
                "title": "Import Queue",
                "items": [
                    {
                        "title": batch.source_name or batch.import_type.replace("_", " ").title(),
                        "subtitle": f"{batch.created_leads} created | {batch.duplicate_rows} duplicates",
                        "meta": batch.status.title(),
                    }
                    for batch in crm_dashboard["recent_import_batches"]
                ],
                "empty": "Import batches yahan dikhengi.",
            },
            {
                "kicker": "Deal Snapshot",
                "title": "Recent Deal Identity",
                "kv_rows": [
                    {"label": "Mapped Deals", "value": len(crm_dashboard["recent_deals"])},
                    {"label": "Property Links", "value": sum(1 for deal in crm_dashboard["recent_deals"] if getattr(deal, "property_id", None))},
                    {"label": "Customer Links", "value": sum(1 for deal in crm_dashboard["recent_deals"] if getattr(deal, "customer_id", None))},
                    {"label": "Agent Links", "value": sum(1 for deal in crm_dashboard["recent_deals"] if getattr(deal, "agent_id", None))},
                ],
                "items": [
                    {
                        "title": f"Deal #{deal.id}",
                        "href": reverse("accounts:deal_workspace", args=[deal.id]),
                        "subtitle": f"{deal.property.title if deal.property_id and deal.property else 'Not mapped'} | {deal.status.title()} | {deal.stage.title()}",
                        "meta": deal.agent.name if deal.agent_id else "Unassigned",
                    }
                    for deal in crm_dashboard["recent_deals"][:5]
                ],
                "empty": "Recent deal mapping yahan show hoga.",
            },
            {
                "kicker": "Assignment",
                "title": "Routing Pressure",
                "kv_rows": [
                    {"label": "Auto Assigned", "value": crm_dashboard["auto_assigned_count"]},
                    {"label": "Active Agents", "value": crm_dashboard["active_agents"]},
                    {"label": "Pending Response", "value": crm_dashboard["snapshot"]["pending_response_count"]},
                    {"label": "Duplicates", "value": crm_dashboard["duplicate_leads"]},
                ],
                "items": [
                    {
                        "title": assignment.lead.name or assignment.lead.mobile,
                        "href": reverse("accounts:lead_workspace", args=[assignment.lead_id]),
                        "subtitle": f"{assignment.assignment_type.title()} | {assignment.matched_on or 'manual'}",
                        "meta": assignment.agent.name if assignment.agent_id else "Unassigned",
                    }
                    for assignment in crm_dashboard["recent_assignments"]
                ],
                "empty": "Assignment events abhi available nahi hain.",
            },
        ],
    )
    context["crm_dashboard"] = crm_dashboard
    return render(request, "accounts/object_workspace.html", context)


@login_required
@feature_required("crm.settings")
def settings_workspace(request):
    from billing.models import Invoice
    from core_settings.services import build_ai_hints, get_settings_payload, get_status_cards
    from kyc.models import KYCProfile
    from rewards.models import ReferralEvent
    from rewards.services import build_referral_share_context, get_or_create_reward_coin
    from wallet.services import get_wallet_summary, sync_profile_payment_accounts

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if not profile.plan:
        basic_plan = Plan.objects.filter(name__iexact="Basic").first()
        if basic_plan:
            profile.plan = basic_plan
            profile.save(update_fields=["plan"])

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            selected_plan = form.cleaned_data.get("plan")
            user = request.user
            user.email = form.cleaned_data.get("email", user.email)
            user.first_name = form.cleaned_data.get("full_name", user.first_name)
            user.save(update_fields=["email", "first_name"])
            form.save()
            sync_profile_payment_accounts(request.user)

            if selected_plan and selected_plan.name.lower() != "basic":
                has_active = Subscription.objects.filter(
                    user=request.user, plan=selected_plan, status="active"
                ).exists()
                if not has_active:
                    messages.info(request, f"Redirecting to payment for {selected_plan.name} plan...")
                    return redirect(f"/billing/checkout/?plan_id={selected_plan.id}")

            messages.success(request, "Workspace saved successfully.")
            return redirect("accounts:settings_workspace")
        messages.error(request, "Please correct the highlighted fields and try again.")
    else:
        form = UserProfileForm(instance=profile)

    workspace_role = (
        "admin"
        if (request.user.is_superuser or request.user.is_staff)
        else "agent"
        if getattr(request.user, "agent_profile", None)
        else "customer"
    )
    role_labels = {
        "admin": "Admin Command Center",
        "agent": "Agent Self-Service Hub",
        "customer": "Customer Settings Studio",
    }
    role_copy = {
        "admin": "Company profile, automation switches, security posture, billing, aur advanced engine settings ab ek single control surface me available hain.",
        "agent": "Profile, KYC readiness, communication tools, workspace preferences, aur commission-facing controls ek jagah se manage karo.",
        "customer": "Identity, alerts, preferences, wallet, plan, aur property journey related settings ko simple self-service flow me manage karo.",
    }

    subscription = get_active_subscription(request.user)
    effective_plan = getattr(subscription, "plan", None) or profile.plan
    locked_count = get_locked_feature_count(request.user)
    usage_summary = get_usage_summary(request.user)
    wallet_summary = get_wallet_summary(request.user)
    linked_account_count = len(wallet_summary["linked_accounts"])
    kyc_profile, _ = KYCProfile.objects.get_or_create(
        user=request.user,
        defaults={"full_name": profile.full_name or request.user.get_full_name() or request.user.username or request.user.email},
    )
    reward_coin = get_or_create_reward_coin(request.user)
    invoice_rows = list(Invoice.objects.filter(user=request.user).order_by("-issued_at")[:5])
    invoice_count = Invoice.objects.filter(user=request.user).count()
    referral_rows = list(
        ReferralEvent.objects.select_related("referrer", "referred_user")
        .filter(Q(referrer=request.user) | Q(referred_user=request.user))
        .order_by("-created_at")[:6]
    )

    settings_payload = get_settings_payload(request.user)
    ai_hints = build_ai_hints(settings_payload)
    advanced_status = get_status_cards(settings_payload)

    setting_lookup = {}
    total_setting_count = 0
    for category in settings_payload.get("categories", []):
        for setting in category.get("settings", []):
            setting_lookup[setting["key"]] = setting
            total_setting_count += 1

    quick_control_meta = {
        "user_2fa_enabled": "OTP-based login security ko ek click me control karo.",
        "user_theme": "Workspace ka visual mode choose karo.",
        "user_language": "Preferred interface language set karo.",
        "wa_enabled": "WhatsApp automations on/off yahin se manage karo.",
        "ai_tools_enabled": "AI tools ke global helpers ko control karo.",
        "portal_enabled": "Customer/supplier portal access ready rakho.",
        "khata_auto_reminders_enabled": "Automatic due reminders ko live rakho.",
        "filing_reminders": "Tax and compliance reminders miss na hon.",
    }
    quick_controls = []
    for key, description in quick_control_meta.items():
        setting = setting_lookup.get(key)
        if setting:
            quick_controls.append(
                {
                    "key": key,
                    "label": setting["label"],
                    "description": description,
                    "data_type": setting["data_type"],
                    "value": setting.get("value"),
                    "options": setting.get("options") or [],
                }
            )

    def _filled(value):
        return bool(str(value or "").strip())

    profile_checks = [
        request.user.email,
        profile.full_name,
        profile.mobile,
        profile.business_name,
        profile.business_type,
        profile.address,
        profile.gst_number,
    ]
    filled_profile_fields = sum(1 for value in profile_checks if _filled(value))
    total_profile_fields = len(profile_checks)
    profile_completion = int(round((filled_profile_fields / total_profile_fields) * 100)) if total_profile_fields else 0

    plan_permissions = effective_plan.get_permissions() if effective_plan else None
    plan_capabilities = [
        {"label": "Reports", "enabled": bool(getattr(plan_permissions, "allow_reports", False))},
        {"label": "Analytics", "enabled": bool(getattr(plan_permissions, "allow_analytics", False))},
        {"label": "WhatsApp", "enabled": bool(getattr(plan_permissions, "allow_whatsapp", False))},
        {"label": "Email", "enabled": bool(getattr(plan_permissions, "allow_email", False))},
        {"label": "API", "enabled": bool(getattr(plan_permissions, "allow_api_access", False))},
        {"label": "Advanced Settings", "enabled": bool(getattr(plan_permissions, "allow_settings", False))},
    ]
    advanced_status_cards = [
        {"label": "Company Setup", "value": advanced_status.get("company_config_status", "Missing")},
        {"label": "Tax Setup", "value": advanced_status.get("tax_setup_status", "Missing")},
        {"label": "Printer Readiness", "value": advanced_status.get("printer_ready_status", "Not Ready")},
        {"label": "WhatsApp Connection", "value": advanced_status.get("whatsapp_connected_status", "Not Connected")},
    ]

    context = {
        "workspace_title": "Settings Workspace",
        "workspace_role": workspace_role,
        "workspace_role_label": role_labels.get(workspace_role, "Workspace"),
        "workspace_copy": role_copy.get(workspace_role, role_copy["customer"]),
        "form": form,
        "profile": profile,
        "subscription": subscription,
        "effective_plan": effective_plan,
        "plan_capabilities": plan_capabilities,
        "locked_features_count": locked_count,
        "usage_summary": usage_summary,
        "wallet_summary": wallet_summary,
        "linked_account_count": linked_account_count,
        "kyc_profile": kyc_profile,
        "reward_coin": reward_coin,
        "invoice_rows": invoice_rows,
        "invoice_count": invoice_count,
        "referral_rows": referral_rows,
        "referral_share": build_referral_share_context(request.user, base_url=request.build_absolute_uri("/").rstrip("/")),
        "settings_payload": settings_payload,
        "settings_category_count": len(settings_payload.get("categories", [])),
        "settings_total_count": total_setting_count,
        "quick_controls": quick_controls,
        "advanced_status_cards": advanced_status_cards,
        "ai_hints": ai_hints,
        "profile_completion": profile_completion,
        "filled_profile_fields": filled_profile_fields,
        "total_profile_fields": total_profile_fields,
        "channel_backend": (
            getattr(settings, "CHANNEL_LAYERS", {})
            .get("default", {})
            .get("BACKEND", "channels.layers.InMemoryChannelLayer")
            .split(".")[-1]
        ),
        "celery_mode": "Local Sync" if getattr(settings, "DISABLE_CELERY", False) else "Redis Async",
        "map_provider": (getattr(settings, "CRM_MAP_PROVIDER", "") or getattr(settings, "MAP_PROVIDER", "") or "google_maps").replace("_", " ").title(),
    }
    return render(request, "accounts/settings_workspace.html", context)


# ---------------------------------------------------
# Role Dashboard Router
# ---------------------------------------------------
@login_required
def role_dashboard(request):
    return role_based_redirect(request.user)

# -----------------------------------------
# Party ledger: main view (with filters)
# -----------------------------------------
# --- SUMMARY FUNCTION FOR DASHBOARD ---
def get_party_summary(party):
    orders = []
    invoices = []
    payments = []
    if Order and Invoice and Payment:
        try:
            orders = Order.objects.filter(party=party)
            invoices = Invoice.objects.filter(order__party=party)
            payments = Payment.objects.filter(invoice__order__party=party)
        except (OperationalError, ProgrammingError):
            orders = []
            invoices = []
            payments = []
    txns = Transaction.objects.filter(party=party)

    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    # Orders
    for o in orders:
        amount = o.total_amount() if hasattr(o, "total_amount") else Decimal("0.00")
        total_debit += amount

    # Invoices
    for inv in invoices:
        total_debit += inv.amount

    # Payments
    for p in payments:
        total_credit += p.amount

    # Manual Txns
    for t in txns:
        if t.txn_type == "debit":
            total_debit += t.amount
        else:
            total_credit += t.amount

    balance = total_debit - total_credit

    return {
        "debit": total_debit,
        "credit": total_credit,
        "balance": balance,
    }

# ---------------------------------------------------
# Helper to normalize dates
# ---------------------------------------------------
def normalize_date(d):
    # If already date, return
    if isinstance(d, date) and not isinstance(d, datetime):
        return d

    # If datetime, convert to date
    if isinstance(d, datetime):
        return d.date()

    # If string, convert safely
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except:
        try:
            return datetime.strptime(d, "%Y-%m-%d %H:%M:%S").date()
        except:
            return date.today()  # fallback)

# ---------------------------------------------------
# Party Ledger (Busy-Style with Running Balance)
# ---------------------------------------------------
def _parse_iso_date(value: str | None) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        return None


def _build_party_ledger_entries(
    *,
    party: Party,
    date_from: date | None,
    date_to: date | None,
) -> tuple[list[dict], Decimal, Decimal, Decimal]:
    """
    Build Busy-style party ledger rows with a running balance.

    Running balance is computed as: opening_balance + Σ(credit - debit)
    so it stays correct even when filtering by date range.
    """
    base_qs = LedgerEntry.objects.filter(party=party).order_by("date", "id").only(
        "date",
        "txn_type",
        "amount",
        "invoice_no",
        "description",
        "credit",
        "debit",
        "notes",
        "source",
    )

    opening_balance = Decimal("0.00")
    if date_from:
        opening_totals = LedgerEntry.objects.filter(party=party, date__date__lt=date_from).aggregate(
            c=Sum("credit"),
            d=Sum("debit"),
        )
        opening_credit = opening_totals.get("c") or Decimal("0.00")
        opening_debit = opening_totals.get("d") or Decimal("0.00")
        opening_balance = opening_credit - opening_debit

    if date_from:
        base_qs = base_qs.filter(date__date__gte=date_from)
    if date_to:
        base_qs = base_qs.filter(date__date__lte=date_to)

    rows: list[dict] = []
    total_credit = Decimal("0.00")
    total_debit = Decimal("0.00")
    running = opening_balance

    for e in base_qs:
        credit = e.credit or Decimal("0.00")
        debit = e.debit or Decimal("0.00")

        total_credit += credit
        total_debit += debit
        running += credit - debit

        rows.append(
            {
                "date": e.date,
                "source": e.source,
                "txn_type": e.txn_type,
                "amount": e.amount,
                "invoice_no": e.invoice_no,
                "description": e.description or e.notes or "",
                "credit": credit,
                "debit": debit,
                "balance": running,
            }
        )

    rows.reverse()  # newest first for UI
    closing_balance = running
    return rows, total_credit, total_debit, closing_balance


@login_required
def party_ledger(request, party_id):

    party = get_object_or_404(Party, id=party_id, owner=request.user)

    date_from_raw = request.GET.get("from")
    date_to_raw = request.GET.get("to")
    date_from = _parse_iso_date(date_from_raw)
    date_to = _parse_iso_date(date_to_raw)

    all_rows, total_credit, total_debit, closing_balance = _build_party_ledger_entries(
        party=party,
        date_from=date_from,
        date_to=date_to,
    )

    paginator = Paginator(all_rows, 20)
    page = int(request.GET.get("page", 1))
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # --------------------------
    # CONTEXT
    # --------------------------
    context = {
        "party": party,
        "entries": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "balance": closing_balance,
        "whatsapp_url": whatsapp_message_url(
            party.mobile,
            f"Your current balance is ₹{closing_balance}"
        ),
    }

    return render(request, "accounts/party_ledger.html", context)

@login_required
def ledger_list(request):
    parties_qs = Party.objects.filter(owner=request.user).order_by("name")
    if PARTY_DEFER_FIELDS:
        parties_qs = parties_qs.defer(*PARTY_DEFER_FIELDS)
    parties = parties_qs

    selected_party = (request.GET.get("party") or "").strip()
    from_date = (request.GET.get("from_date") or "").strip()
    to_date = (request.GET.get("to_date") or "").strip()
    invoice = (request.GET.get("invoice") or "").strip()

    qs = LedgerEntry.objects.filter(party__owner=request.user).select_related("party").order_by("-date", "-id")

    party_obj = None
    if selected_party:
        party_obj_qs = Party.objects.filter(id=selected_party, owner=request.user)
        if PARTY_DEFER_FIELDS:
            party_obj_qs = party_obj_qs.defer(*PARTY_DEFER_FIELDS)
        party_obj = party_obj_qs.first()
        if not party_obj:
            return HttpResponseForbidden("You do not have permission to view this party.")
        qs = qs.filter(party=party_obj)

    if from_date:
        try:
            qs = qs.filter(date__date__gte=datetime.fromisoformat(from_date).date())
        except Exception:
            from_date = ""

    if to_date:
        try:
            qs = qs.filter(date__date__lte=datetime.fromisoformat(to_date).date())
        except Exception:
            to_date = ""

    if invoice:
        qs = qs.filter(invoice_no__icontains=invoice)

    totals = qs.aggregate(
        total_debit=Sum(Case(When(txn_type="debit", then=F("amount")), default=0, output_field=FloatField())),
        total_credit=Sum(Case(When(txn_type="credit", then=F("amount")), default=0, output_field=FloatField())),
    )
    total_debit = float(totals.get("total_debit") or 0)
    total_credit = float(totals.get("total_credit") or 0)
    closing_balance = total_credit - total_debit

    paginator = Paginator(qs, 25)
    page_number = request.GET.get("page", 1)
    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    party_cards = []
    if not selected_party:
        # Summaries for quick navigation (Busy/Tally style).
        for p in parties:
            p_qs = LedgerEntry.objects.filter(party=p).order_by("-date", "-id")
            p_tot = p_qs.aggregate(
                total_debit=Sum(Case(When(txn_type="debit", then=F("amount")), default=0, output_field=FloatField())),
                total_credit=Sum(Case(When(txn_type="credit", then=F("amount")), default=0, output_field=FloatField())),
            )
            p_debit = float(p_tot.get("total_debit") or 0)
            p_credit = float(p_tot.get("total_credit") or 0)
            party_cards.append(
                {
                    "party": p,
                    "total_debit": p_debit,
                    "total_credit": p_credit,
                    "balance": p_credit - p_debit,
                    "recent": list(p_qs.select_related("party")[:3]),
                }
            )

    return render(
        request,
        "accounts/ledger_list.html",
        {
            "parties": parties,
            "party": party_obj,
            "entries": page_obj.object_list,
            "page_obj": page_obj,
            "selected_party": selected_party,
            "from_date": from_date,
            "to_date": to_date,
            "invoice": invoice,
            "totals": {"total_debit": total_debit, "total_credit": total_credit, "balance": closing_balance},
            "closing_balance": closing_balance,
            "party_cards": party_cards,
        },
    )

#---------------------------------------------------
# AJAX Load More (Busy style)
# ---------------------------------------------------
@login_required
def party_ledger_load_more(request, party_id):

    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({"error": "Only AJAX allowed"}, status=400)

    party = get_object_or_404(Party, id=party_id, owner=request.user)

    date_from = _parse_iso_date(request.GET.get("from"))
    date_to = _parse_iso_date(request.GET.get("to"))

    all_rows, _, _, _ = _build_party_ledger_entries(
        party=party,
        date_from=date_from,
        date_to=date_to,
    )

    page = int(request.GET.get("page", 1))
    paginator = Paginator(all_rows, 20)

    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        return JsonResponse({"html": "", "has_next": False})

    html = render_to_string("accounts/ledger_entries.html", {
        "entries": page_obj.object_list
    })

    return JsonResponse({"html": html, "has_next": page_obj.has_next()})


# ---------------------------------------------------
# PDF Export – Busy Format
# ---------------------------------------------------
@login_required
def party_ledger_pdf(request, party_id):

    party = get_object_or_404(Party, id=party_id, owner=request.user)

    date_from = _parse_iso_date(request.GET.get("from"))
    date_to = _parse_iso_date(request.GET.get("to"))

    rows_desc, total_credit, total_debit, closing_balance = _build_party_ledger_entries(
        party=party,
        date_from=date_from,
        date_to=date_to,
    )
    entries = list(reversed(rows_desc))

    context = {
        "party": party,
        "entries": entries,
        "total_credit": total_credit,
        "total_debit": total_debit,
        "balance": closing_balance,
        "generated_on": timezone.now(),
    }

    pdf_bytes = render_to_pdf_bytes("accounts/party_ledger_pdf.html", context, request=request)

    if pdf_bytes:
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp['Content-Disposition'] = f'attachment; filename="ledger_{party.id}.pdf"'
        return resp

    # fallback if pdf generation fails
    return render(request, "accounts/party_ledger_pdf.html", context)

@login_required
def staff_dashboard(request):
    return render(request, "accounts/staff_dashboard.html")


# ---------------------------------------------------
# Collector Dashboard
# ---------------------------------------------------
@login_required
def collector_dashboard(request):
    agent = getattr(request.user, "field_agent_profile", None)
    if not agent or not agent.is_active:
        return HttpResponseForbidden("Collector access required.")
    if CollectorVisit is None or OfflineMessage is None or CompanySettings is None:
        messages.info(request, "Collector workspace is not available in this lightweight build.")
        return redirect("accounts:dashboard")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "visit_update":
            visit_id = request.POST.get("visit_id")
            status = request.POST.get("status")
            collected_amount = request.POST.get("collected_amount")
            payment_mode = request.POST.get("payment_mode")
            notes = request.POST.get("visit_notes")

            visit = get_object_or_404(CollectorVisit, id=visit_id, agent=agent)
            try:
                collected_val = Decimal(str(collected_amount or "0"))
            except Exception:
                collected_val = Decimal("0")

            visit.status = status or visit.status
            visit.collected_amount = collected_val
            visit.payment_mode = payment_mode or visit.payment_mode
            visit.notes = notes or visit.notes
            visit.marked_at = timezone.now()
            visit.save(update_fields=["status", "collected_amount", "payment_mode", "notes", "marked_at"])

            messages.success(request, "Visit updated successfully.")
            return redirect("accounts:collector_dashboard")

        if action != "create_order":
            messages.error(request, "Invalid action.")
            return redirect("accounts:collector_dashboard")

        party_id = request.POST.get("party_id")
        notes = request.POST.get("notes")
        products = request.POST.getlist("product_id[]")
        raw_names = request.POST.getlist("raw_name[]")
        qtys = request.POST.getlist("qty[]")
        prices = request.POST.getlist("price[]")

        if not party_id:
            messages.error(request, "Please select a party.")
            return redirect("accounts:collector_dashboard")

        party = agent.assigned_parties.filter(id=party_id).first()
        if not party:
            messages.error(request, "Party not assigned to you.")
            return redirect("accounts:collector_dashboard")

        from commerce.models import Order, OrderItem, Product

        with transaction.atomic():
            order = Order.objects.create(
                owner=agent.owner,
                party=party,
                order_type="SALE",
                status="pending",
                notes=notes or f"Agent order by {agent.user.get_full_name() or agent.user.email}",
                order_source="Agent",
                assigned_to=agent.user,
                agent=agent,
                placed_by="user",
                discount_type=(request.POST.get("discount_type") or "none").lower(),
                discount_value=Decimal(str(request.POST.get("discount_value") or "0")),
                tax_percent=Decimal(str(request.POST.get("tax_percent") or "0")),
            )

            valid_items = 0
            for product_id, raw_name, qty, price in zip(products, raw_names, qtys, prices):
                try:
                    qty_val = int(qty or 0)
                    price_val = Decimal(str(price or "0"))
                except Exception:
                    continue

                if qty_val <= 0 or price_val <= 0:
                    continue

                product = None
                if product_id:
                    product = Product.objects.filter(id=product_id).first()

                raw_label = raw_name or (product.name if product else "Agent Item")
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    qty=qty_val,
                    price=price_val,
                    raw_name=raw_label,
                )
                valid_items += 1

            if valid_items == 0:
                messages.error(request, "Please add at least one valid item.")
                return redirect("accounts:collector_dashboard")

            # Recompute totals after items creation
            order.compute_totals()
            order.save(update_fields=["discount_amount", "tax_amount"])

        # Auto send WhatsApp confirmation (best effort)
        settings_obj = CompanySettings.objects.first()
        if settings_obj and settings_obj.enable_auto_whatsapp and party.whatsapp_number:
            try:
                message = (
                    f"Order #{order.id} received. Total ₹{order.total_amount()}. "
                    f"Agent: {agent.user.get_full_name() or agent.user.email}."
                )
                send_whatsapp_message(to=party.whatsapp_number.lstrip("+"), message=message)
            except Exception:
                OfflineMessage.objects.create(
                    party=party,
                    recipient_name=party.name,
                    recipient_mobile=party.whatsapp_number,
                    message=message,
                    channel="whatsapp",
                    status="pending"
                )

        # Email + SMS (queue) best effort
        if party.email:
            try:
                from django.core.mail import send_mail
                send_mail(
                    subject=f"Order #{order.id} Confirmation",
                    message=f"Order #{order.id} received. Total ₹{order.total_amount()}.",
                    from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, "DEFAULT_FROM_EMAIL") else None,
                    recipient_list=[party.email],
                    fail_silently=True
                )
            except Exception:
                pass

        if party.mobile:
            OfflineMessage.objects.create(
                party=party,
                recipient_name=party.name,
                recipient_mobile=party.mobile,
                message=f"Order #{order.id} received. Total ₹{order.total_amount()}.",
                channel="sms",
                status="pending"
            )

        messages.success(request, f"Order #{order.id} created. Total ₹{order.total_amount()}.")
        return redirect("accounts:collector_dashboard")

    today = timezone.now().date()
    visits_today = CollectorVisit.objects.filter(
        agent=agent,
        visit_date=today
    ).select_related("party").order_by("party__name")

    # Auto-generate visit plan if none exists for today
    if not visits_today.exists():
        for party in agent.assigned_parties.all():
            summary = get_party_summary(party)
            expected = summary.get("balance") if summary else 0
            if expected and expected > 0:
                CollectorVisit.objects.get_or_create(
                    agent=agent,
                    party=party,
                    visit_date=today,
                    defaults={
                        "expected_amount": expected,
                        "status": "planned"
                    }
                )

        visits_today = CollectorVisit.objects.filter(
            agent=agent,
            visit_date=today
        ).select_related("party").order_by("party__name")

    total_expected = visits_today.aggregate(
        total=Sum("expected_amount")
    )["total"] or Decimal("0.00")

    total_collected = visits_today.aggregate(
        total=Sum("collected_amount")
    )["total"] or Decimal("0.00")

    from commerce.models import Product, Order
    products = Product.objects.filter(owner=agent.owner).order_by("name")
    recent_agent_orders = Order.objects.filter(agent=agent).select_related("party").order_by("-created_at")[:10]

    visit_counts = {
        "planned": visits_today.filter(status="planned").count(),
        "visited": visits_today.filter(status="visited").count(),
        "partial": visits_today.filter(status="partial").count(),
        "not_available": visits_today.filter(status="not_available").count(),
        "cancelled": visits_today.filter(status="cancelled").count(),
    }

    context = {
        "agent": agent,
        "visits_today": visits_today,
        "total_expected": total_expected,
        "total_collected": total_collected,
        "today": today,
        "products": products,
        "recent_agent_orders": recent_agent_orders,
        "visit_counts": visit_counts,
    }

    return render(request, "accounts/collector_dashboard.html", context)


# ---------------------------------------------------
# Party Dashboard
# ---------------------------------------------------
@login_required
def party_dashboard(request):
    user = request.user

    mobile = None
    if user.mobile:
        mobile = user.mobile
    else:
        profile = KhataProfile.objects.filter(user=user).first()
        mobile = profile.mobile if profile else None

    party = None
    if mobile:
        party_qs = Party.objects.filter(mobile=mobile)
        if PARTY_DEFER_FIELDS:
            party_qs = party_qs.defer(*PARTY_DEFER_FIELDS)
        party = party_qs.first()
        if not party:
            party_qs = Party.objects.filter(whatsapp_number=mobile)
            if PARTY_DEFER_FIELDS:
                party_qs = party_qs.defer(*PARTY_DEFER_FIELDS)
            party = party_qs.first()

    summary = None
    invoices = []
    payments = []

    if party:
        summary = get_party_summary(party)
        if Invoice:
            try:
                invoices = Invoice.objects.filter(order__party=party).order_by("-created_at")[:10]
            except (OperationalError, ProgrammingError):
                invoices = []
        if Payment:
            try:
                payments = Payment.objects.filter(invoice__order__party=party).order_by("-created_at")[:10]
            except (OperationalError, ProgrammingError):
                payments = []

    context = {
        "party": party,
        "summary": summary,
        "invoices": invoices,
        "payments": payments,
    }

    return render(request, "accounts/party_dashboard.html", context)

# ----------------- EDIT PROFILE -----------------
@login_required
def edit_profile(request):
    from billing.models import Invoice
    from kyc.models import KYCProfile
    from rewards.models import ReferralEvent
    from rewards.services import build_referral_share_context, get_or_create_reward_coin
    from wallet.services import get_wallet_summary, sync_profile_payment_accounts

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if not profile.plan:
        basic_plan = Plan.objects.filter(name__iexact="Basic").first()
        if basic_plan:
            profile.plan = basic_plan
            profile.save()

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            selected_plan = form.cleaned_data.get("plan")
            user = request.user
            user.email = form.cleaned_data.get("email", user.email)
            user.first_name = form.cleaned_data.get("full_name", user.first_name)
            user.save(update_fields=["email", "first_name"])
            form.save()
            sync_profile_payment_accounts(request.user)

            if selected_plan and selected_plan.name.lower() != "basic":
                has_active = Subscription.objects.filter(
                    user=request.user, plan=selected_plan, status="active"
                ).exists()
                if not has_active:
                    messages.info(request, f"Redirecting to payment for {selected_plan.name} plan...")
                    return redirect(f"/billing/checkout/?plan_id={selected_plan.id}")

            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:edit_profile")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserProfileForm(instance=profile)

    admin_profile = UserProfile.objects.filter(user__is_superuser=True).first()
    subscription = get_active_subscription(request.user)
    locked_count = get_locked_feature_count(request.user)
    usage_summary = get_usage_summary(request.user)
    wallet_summary = get_wallet_summary(request.user)
    kyc_profile, _ = KYCProfile.objects.get_or_create(
        user=request.user,
        defaults={"full_name": profile.full_name or request.user.get_full_name() or request.user.username},
    )
    reward_coin = get_or_create_reward_coin(request.user)
    invoice_rows = list(Invoice.objects.filter(user=request.user).order_by("-issued_at")[:5])
    referral_rows = list(
        ReferralEvent.objects.select_related("referrer", "referred_user")
        .filter(Q(referrer=request.user) | Q(referred_user=request.user))
        .order_by("-created_at")[:6]
    )
    context = {
        "form": form,
        "profile": profile,
        "admin_logo": admin_profile.profile_picture.url if admin_profile and admin_profile.profile_picture else None,
        "admin_name": admin_profile.business_name if admin_profile else "",
        "admin_address": admin_profile.address if admin_profile else "",
        "admin_gst": admin_profile.gst_number if admin_profile else "",
        "admin_contact": admin_profile.mobile if admin_profile else "",
        "plan_name": profile.plan.name if profile.plan else "Basic",
        "subscription": subscription,
        "locked_features_count": locked_count,
        "usage_summary": usage_summary,
        "wallet_summary": wallet_summary,
        "kyc_profile": kyc_profile,
        "reward_coin": reward_coin,
        "invoice_rows": invoice_rows,
        "invoice_count": Invoice.objects.filter(user=request.user).count(),
        "referral_rows": referral_rows,
        "referral_share": build_referral_share_context(request.user, base_url=request.build_absolute_uri("/").rstrip("/")),
    }

    return render(request, "accounts/edit_profile.html", context)


def _signup_referral_context(request):
    referral_code = (
        request.POST.get("referral_code")
        or request.GET.get("ref")
        or request.session.get("signup_referral_code")
        or ""
    ).strip().upper()
    if referral_code:
        request.session["signup_referral_code"] = referral_code
    else:
        request.session.pop("signup_referral_code", None)
    inviter = (
        User.objects.filter(referral_code__iexact=referral_code)
        .only("id", "email", "first_name", "username", "referral_code")
        .first()
        if referral_code
        else None
    )
    return referral_code, inviter

# ----------------- SIGNUP -----------------
def signup_view(request):
    # Limit system to a small number of non-staff users for testing.
    # Admin/staff can still create users via admin if needed.
    # NOTE: Desktop EXE ships with a bundled SQLite that may contain demo/sample users.
    # Enforcing this limit in DESKTOP_MODE can unintentionally block real signups.
    referral_code, referral_inviter = _signup_referral_context(request)
    if request.method == "POST" and not getattr(settings, "DESKTOP_MODE", False):
        try:
            max_users = int(getattr(settings, "MAX_TEST_USERS", 10))
        except Exception:
            max_users = 10
        if User.objects.filter(is_staff=False, is_superuser=False).count() >= max_users:
            messages.error(request, f"Signup disabled: testing limit reached ({max_users} users).")
            return redirect("accounts:login")

    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            try:
                desktop_bypass = bool(getattr(settings, "DESKTOP_MODE", False) and getattr(settings, "OTP_BYPASS", False))
                referred_by = referral_inviter if referral_code else None
                if referral_code and referred_by is None:
                    form.add_error(None, "Referral code is invalid.")
                    return render(
                        request,
                        "accounts/signup.html",
                        {"form": form, "referral_code": referral_code, "referral_inviter": None},
                    )
                with transaction.atomic():
                    user = form.save(commit=False)
                    if referred_by:
                        user.referred_by = referred_by
                    # Desktop OTP-bypass: avoid multi-step OTP/session flow in embedded WebViews.
                    user.is_active = desktop_bypass
                    user.is_otp_verified = desktop_bypass
                    user.save()

                    otp = None
                    if not desktop_bypass:
                        otp = OTP.create_for(
                            user=user,
                            purpose="signup",
                            email=user.email,
                            mobile=form.cleaned_data.get("mobile"),
                        )

                # Create khataapp profile OUTSIDE transaction to avoid FK constraint issues
                try:
                    profile = KhataProfile.objects.get(user=user)
                except KhataProfile.DoesNotExist:
                    profile = KhataProfile.objects.create(
                        user=user,
                        created_from="signup",
                        plan=None,
                        mobile=form.cleaned_data.get("mobile"),
                        full_name=user.get_full_name() or user.username
                    )
                # Auto-assign default plan (if configured) else Free plan + subscription.
                # Note: subscriptions are the source of truth for `get_effective_plan()`.
                try:
                    from core_settings.models import CompanySettings as KhataCompanySettings
                    from billing.services import upgrade_subscription

                    cs = KhataCompanySettings.objects.select_related("default_plan").order_by("id").first()
                    default_plan = getattr(cs, "default_plan", None)
                    if default_plan and getattr(default_plan, "active", True):
                        upgrade_subscription(user, default_plan)
                    else:
                        ensure_free_plan(user)
                except Exception:
                    try:
                        ensure_free_plan(user)
                    except Exception:
                        pass

                if desktop_bypass:
                    user.backend = "django.contrib.auth.backends.ModelBackend"
                    login(request, user)
                    request.session.pop("signup_referral_code", None)
                    messages.success(request, "Account created successfully.")
                    return role_based_redirect(user)

                # OTP sending outside transaction
                if otp is not None and user.email:
                    send_email_otp(user.email, otp.code)
                if otp is not None and profile.mobile:
                    send_sms_otp(profile.mobile, otp.code)

                request.session["otp_user_id"] = user.id
                request.session["otp_purpose"] = "signup"
                request.session.pop("signup_referral_code", None)

                messages.success(request, "OTP sent. Please verify your account.")
                return redirect("accounts:verify_otp")

            except Exception as e:
                messages.error(request, f"Signup failed: {e}")
                return redirect("accounts:signup")

    else:
        form = SignupForm()

    return render(
        request,
        "accounts/signup.html",
        {"form": form, "referral_code": referral_code, "referral_inviter": referral_inviter},
    )

# ----------------- LOGIN -----------------
def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            role = str(form.cleaned_data.get("role") or "user").strip().lower()
            identifier = form.cleaned_data["identifier"]
            password = form.cleaned_data["password"]
            use_otp = form.cleaned_data.get("use_otp", True)
            if getattr(settings, "OTP_BYPASS", False):
                use_otp = False

            # ----------------- PORTAL LOGIN (Customer/Supplier) -----------------
            if role in {"customer", "supplier"}:
                # Portal availability (admin settings)
                try:
                    from portal.services import customer_portal_enabled, portal_enabled, supplier_portal_enabled

                    if not portal_enabled():
                        messages.error(request, "Portal login is currently disabled by admin settings.")
                        return render(request, "accounts/login.html", {"form": form})
                    if role == "customer" and not customer_portal_enabled():
                        messages.error(request, "Customer portal is currently disabled by admin settings.")
                        return render(request, "accounts/login.html", {"form": form})
                    if role == "supplier" and not supplier_portal_enabled():
                        messages.error(request, "Supplier portal is currently disabled by admin settings.")
                        return render(request, "accounts/login.html", {"form": form})
                except Exception:
                    # Never block ERP login because of portal settings read errors.
                    pass

                # Portal accounts use username + password (no OTP).
                if not password:
                    messages.error(request, "Password is required for portal login.")
                    return render(request, "accounts/login.html", {"form": form})
                try:
                    from portal.models import PortalUser
                except Exception:
                    messages.error(request, "Portal module unavailable.")
                    return render(request, "accounts/login.html", {"form": form})

                pu = PortalUser.objects.select_related("party", "owner").filter(username__iexact=identifier, role=role).first()
                if not pu or not pu.is_active or not pu.check_password(password):
                    messages.error(request, "Invalid portal credentials.")
                    return render(request, "accounts/login.html", {"form": form})

                try:
                    request.session.cycle_key()
                except Exception:
                    pass
                request.session["portal_user_id"] = pu.id
                request.session["portal_role"] = pu.role
                try:
                    pu.touch_login()
                except Exception:
                    pass

                messages.success(request, "Portal login successful.")
                if getattr(pu, "must_change_password", False):
                    return redirect("portal:change_password")
                if pu.role == "supplier":
                    return redirect("portal:supplier_dashboard")
                return redirect("portal:customer_dashboard")

            # Find user by mobile or email
            user = None
            mobile_for_otp = None
            
            profile = KhataProfile.objects.filter(mobile=identifier).select_related("user").first()
            if profile:
                user = profile.user
                mobile_for_otp = profile.mobile
            else:
                # Try email
                try:
                    user = User.objects.get(email__iexact=identifier)
                except User.DoesNotExist:
                    user = None

                # Try username fallback
                if user is None:
                    try:
                        user = User.objects.get(username__iexact=identifier)
                    except User.DoesNotExist:
                        user = None

                if user:
                    user_profile = KhataProfile.objects.filter(user=user).first()
                    mobile_for_otp = user_profile.mobile if user_profile else None
                else:
                    messages.error(request, "User not found")
                    return render(request, "accounts/login.html", {"form": form})

            # Ensure user is not None before proceeding
            if not user:
                messages.error(request, "User not found")
                return render(request, "accounts/login.html", {"form": form})

            # Role guardrails (UI selection)
            if role == "admin" and not (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)):
                messages.error(request, "This account does not have admin access.")
                return render(request, "accounts/login.html", {"form": form})

            # ---- OTP LOGIN ----
            if use_otp:
                # Preserve desired redirect for OTP verification step.
                try:
                    if role == "admin" and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)):
                        request.session["post_otp_redirect"] = "/superadmin/"
                    else:
                        request.session.pop("post_otp_redirect", None)
                except Exception:
                    pass

                # Desktop convenience: in OTP bypass mode, skip the OTP step entirely.
                # This avoids session/cookie edge cases in embedded desktop WebViews.
                if getattr(settings, "DESKTOP_MODE", False) and getattr(settings, "OTP_BYPASS", False):
                    user.is_active = True
                    user.is_otp_verified = True
                    user.save(update_fields=["is_active", "is_otp_verified"])

                    user.backend = "django.contrib.auth.backends.ModelBackend"
                    login(request, user)
                    if role == "admin" and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)):
                        return redirect("/superadmin/")
                    return role_based_redirect(user)

                otp = OTP.create_for(
                    user=user,
                    purpose="login",
                    email=user.email,
                    mobile=mobile_for_otp,
                )

                if user.email:
                    send_email_otp(user.email, otp.code)
                if mobile_for_otp:
                    send_sms_otp(mobile_for_otp, otp.code)

                request.session["otp_user_id"] = user.id
                request.session["otp_purpose"] = "login"

                messages.info(request, "OTP sent. Please verify.")
                return redirect("accounts:verify_otp")

            # ---- NORMAL PASSWORD LOGIN ----
            if not password:
                messages.error(request, "Password is required when OTP login is off.")
                return render(request, "accounts/login.html", {"form": form})

            # Our custom User model uses email as USERNAME_FIELD.
            user_auth = authenticate(request, username=user.get_username(), password=password)
            if user_auth:
                login(request, user_auth)
                if role == "admin" and (getattr(user_auth, "is_staff", False) or getattr(user_auth, "is_superuser", False)):
                    return redirect("/superadmin/")
                return role_based_redirect(user_auth)

            # If credentials are correct but the user is inactive, ModelBackend returns None.
            # Surface a clearer error and route to OTP verification.
            if user.check_password(password) and not user.is_active:
                messages.error(request, "Verify OTP first")
                request.session["otp_user_id"] = user.id
                request.session["otp_purpose"] = "login"
                return redirect("accounts:verify_otp")

            messages.error(request, "Invalid credentials")

    else:
        initial = {}
        role_q = str(request.GET.get("role") or "").strip().lower()
        if role_q in {"user", "admin", "customer", "supplier", "agent"}:
            initial["role"] = role_q
        form = LoginForm(initial=initial or None)

    return render(request, "accounts/login.html", {"form": form})


# ----------------- OTP VERIFY -----------------
def verify_otp_view(request):

    user_id = request.session.get("otp_user_id")

    if not user_id:
        messages.error(request, "Session expired. Please login again.")
        return redirect("accounts:login")

    user = get_object_or_404(User, id=user_id)

    # ✅ TEMPORARY BYPASS (Render free deploy helper)
    if getattr(settings, "OTP_BYPASS", False):
        user.is_active = True
        user.is_otp_verified = True
        user.save(update_fields=["is_active", "is_otp_verified"])

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        request.session.pop("otp_user_id", None)
        request.session.pop("otp_purpose", None)

        messages.warning(request, "⚠ OTP bypass mode active (temporary).")

        next_url = request.session.pop("post_otp_redirect", None)
        if isinstance(next_url, str) and next_url.startswith("/"):
            return redirect(next_url)
        if user.is_superuser:
            return redirect("/superadmin/")
        return redirect("/accounts/dashboard/")


    # ✅ NORMAL FLOW (PRODUCTION SAFE)
    if request.method == "POST":
        form = OTPForm(request.POST)

        if form.is_valid():
            code = form.cleaned_data["code"]

            otp = OTP.objects.filter(
                user=user,
                verified=False,
                expires_at__gte=timezone.now()
            ).order_by("-created_at").first()

            if not otp:
                messages.error(request, "OTP expired. Please resend.")
                return redirect("accounts:verify_otp")

            if otp.code != code:
                messages.error(request, "Invalid OTP.")
                return redirect("accounts:verify_otp")

            otp.verified = True
            otp.save(update_fields=["verified"])

            user.is_active = True
            user.is_otp_verified = True
            user.save(update_fields=["is_active", "is_otp_verified"])

            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)

            request.session.pop("otp_user_id", None)
            request.session.pop("otp_purpose", None)

            messages.success(request, "Account verified successfully.")

            next_url = request.session.pop("post_otp_redirect", None)
            if isinstance(next_url, str) and next_url.startswith("/"):
                return redirect(next_url)
            if user.is_superuser:
                return redirect("/superadmin/")
            else:
                return redirect("accounts:role_dashboard")

    else:
        form = OTPForm()

    return render(request, "accounts/verify_otp.html", {
        "form": form,
        "user": user
    })


# ----------------- LOGOUT -----------------
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


# ---------------------------------------------------
# Login via Secure Link (WhatsApp First)
# ---------------------------------------------------
def login_link_view(request, token):
    if LoginLink is None:
        messages.error(request, "Secure login links are unavailable in this lightweight build.")
        return redirect("accounts:login")
    link = get_object_or_404(LoginLink, token=token, is_active=True)
    if not link.is_valid():
        messages.error(request, "Link expired or invalid. Please request a new link.")
        return redirect("accounts:login")

    user = link.user

    mobile_for_otp = None
    profile = KhataProfile.objects.filter(user=user).first()
    if profile and profile.mobile:
        mobile_for_otp = profile.mobile
    elif user.mobile:
        mobile_for_otp = user.mobile

    otp = OTP.create_for(
        user=user,
        purpose="login",
        email=user.email,
        mobile=mobile_for_otp,
    )

    if user.email:
        send_email_otp(user.email, otp.code)
    if mobile_for_otp:
        send_sms_otp(mobile_for_otp, otp.code)

    link.last_used_at = timezone.now()
    link.save(update_fields=["last_used_at"])

    request.session["otp_user_id"] = user.id
    request.session["otp_purpose"] = "login"

    messages.info(request, "OTP sent. Please verify to continue.")
    return redirect("accounts:verify_otp")


# ----------------- PROFILE SETTINGS (Legacy Support) -----------------
@login_required
def profile_settings(request):
    """Optional: keep for backward compatibility"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:dashboard")
    else:
        form = UserProfileForm(instance=profile)

    return render(request, "accounts/profile_settings.html", {"form": form})


# ----------------- SUBSCRIBE PLAN -----------------
@login_required
def subscribe_plan(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.plan = plan
    profile.save()
    messages.success(request, f"Subscribed to {plan.name} plan.")
    return redirect("accounts:dashboard")

@login_required
def upgrade_plan(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    user = request.user

    # ✅ Create unpaid invoice
    invoice = Invoice.objects.create(
        user=user,
        plan=plan,
        amount=plan.price_per_month,
        status="pending"
    )

    # Redirect to your payment gateway (Razorpay, Stripe, etc.)
    return redirect(f"/billing/pay/{invoice.id}/")

@login_required
def daily_summary_view(request):
    user = request.user

    # Always ensure user is a valid User object
    if not isinstance(user, User):
        user = User.objects.filter(username=user).first()
        if not user:
            return HttpResponse("Invalid user. Contact admin.")

    today = date.today()

    summary = DailySummary.objects.filter(user=user, date=today).first()

    if summary is None:
        transactions = Transaction.objects.filter(
            party__user=user,
            date=today
        )

        total_debit = transactions.filter(txn_type="debit").aggregate(total=Sum("amount"))["total"] or 0
        total_credit = transactions.filter(txn_type="credit").aggregate(total=Sum("amount"))["total"] or 0

        balance = total_debit - total_credit

        summary = DailySummary.objects.create(
            user=user,
            date=today,
            total_credit=total_credit,
            total_debit=total_debit,
            balance=balance,
            total_transactions=transactions.count(),
        )

    return render(request, "accounts/daily_summary.html", {"summary": summary})


# -------------------------------------------------------
# SAFE UPDATE FUNCTION – WILL NEVER CRASH OR TAKE STRING
# -------------------------------------------------------

def update_daily_summary(user, refresh=False):

    # 1. Convert anything to User object safely
    if isinstance(user, User):
        pass
    elif isinstance(user, int):
        user = User.objects.filter(id=user).first()
    elif isinstance(user, str):
        user = User.objects.filter(username=user).first()
    else:
        return None

    if not user:
        return None

    today = timezone.now().date()
    cache_key = f"daily_summary:{user.pk}:{today.isoformat()}"
    if not refresh:
        cached_summary = cache.get(cache_key)
        if cached_summary is not None:
            return cached_summary
        summary = DailySummary.objects.filter(user=user, date=today).first()
        if summary is not None:
            cache.set(cache_key, summary, 120)
            return summary

    transactions = Transaction.objects.filter(
        party__user=user,
        date=today
    )

    total_credit = transactions.filter(txn_type='credit').aggregate(total=Sum('amount'))['total'] or 0
    total_debit = transactions.filter(txn_type='debit').aggregate(total=Sum('amount'))['total'] or 0
    balance = total_debit - total_credit

    summary, created = DailySummary.objects.get_or_create(
        user=user,
        date=today,
        defaults={
            'total_credit': total_credit,
            'total_debit': total_debit,
            'balance': balance,
            'total_transactions': transactions.count(),
        }
    )

    summary.total_credit = total_credit
    summary.total_debit = total_debit
    summary.balance = balance
    summary.total_transactions = transactions.count()
    summary.save()
    cache.set(cache_key, summary, 120)

    return summary

@login_required
def business_snapshot_view(request):
    selected = parse_date(request.GET.get("date") or "") or now().date()
    snapshot = build_business_snapshot(request.user, selected)
    return render(
        request,
        "accounts/business_snapshot.html",
        {"snapshot": snapshot, "selected_date": selected}
    )

@login_required
def loyalty_dashboard(request):
    loyalty_account = LoyaltyPoints.objects.filter(user=request.user).select_related("program", "current_tier").first()
    program = LoyaltyProgram.objects.filter(is_active=True).first()
    tiers = MembershipTier.objects.filter(is_active=True).order_by("min_points_required")
    offers = [o for o in SpecialOffer.objects.filter(is_active=True) if o.is_valid_for_user(request.user)]
    return render(
        request,
        "accounts/loyalty_dashboard.html",
        {
            "loyalty_account": loyalty_account,
            "program": program,
            "tiers": tiers,
            "offers": offers,
        },
    )

# -------------------------------------------------------
# SAFE UPDATE FUNCTION – WILL NEVER CRASH OR TAKE STRING
# -------------------------------------------------------
@login_required
def create_expense(request):
    categories = ExpenseCategory.objects.filter(created_by=request.user)

    if request.method == "POST":
        category_name = request.POST.get("new_category")
        category_id = request.POST.get("category")
        expense_date = request.POST.get("expense_date")
        description = request.POST.get("description")
        amount_paid = request.POST.get("amount_paid")

        if category_name:
            category = ExpenseCategory.objects.create(
                name=category_name,
                created_by=request.user
            )
        else:
            if not category_id:
                messages.error(request, "Please select a category or create a new one.")
                return render(request, "accounts/expense_create.html", {
                    "categories": categories,
                    "today": now().date()
                })
            category = ExpenseCategory.objects.filter(id=category_id, created_by=request.user).first()
            if not category:
                messages.error(request, "Invalid category selected.")
                return render(request, "accounts/expense_create.html", {
                    "categories": categories,
                    "today": now().date()
                })

        Expense.objects.create(
            expense_number=f"EXP-{uuid.uuid4().hex[:6].upper()}",
            expense_date=expense_date,
            category=category,
            description=description,
            amount_paid=amount_paid,
            created_by=request.user
        )

        return redirect("accounts:expense_list")

    return render(request, "accounts/expense_create.html", {
        "categories": categories,
        "today": now().date()
    })

@login_required
def expense_list(request):
    expenses = Expense.objects.filter(created_by=request.user).order_by("-expense_date")
    return render(request, "accounts/expense_list.html", {
        "expenses": expenses
    })

@login_required
@require_POST
def redeem_points(request):
    """
    Redeem loyalty points securely.
    Supports web, mobile app, API clients.
    """

    # -------------------------
    # 1️⃣ Parse JSON safely
    # -------------------------
    try:
        payload = json.loads(request.body.decode("utf-8"))
        points = int(payload.get("points", 0))
        description = payload.get(
            "description",
            "Points redeemed by user"
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON payload"},
            status=400
        )
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "Points must be a valid number"},
            status=400
        )

    # -------------------------
    # 2️⃣ Validate points
    # -------------------------
    if points <= 0:
        return JsonResponse(
            {"error": "Points must be greater than zero"},
            status=400
        )

    # -------------------------
    # 3️⃣ Atomic transaction (SAFE)
    # -------------------------
    try:
        with transaction.atomic():

            # User profile
            profile = UserProfile.objects.select_for_update().get(
                user=request.user
            )

            # Loyalty account
            loyalty = LoyaltyPoints.objects.select_for_update().get(
                user=request.user
            )

            if loyalty.available_points < points:
                return JsonResponse(
                    {"error": "Insufficient reward points"},
                    status=400
                )

            # Redeem using model method (BEST PRACTICE)
            loyalty.redeem_points(
                points=points,
                description=description
            )

            # Optional sync with profile (if you use both)
            profile.reward_points = loyalty.available_points
            profile.save(update_fields=["reward_points"])

    except UserProfile.DoesNotExist:
        return JsonResponse(
            {"error": "User profile not found"},
            status=404
        )

    except LoyaltyPoints.DoesNotExist:
        return JsonResponse(
            {"error": "Loyalty account not found"},
            status=404
        )

    except Exception as e:
        return JsonResponse(
            {"error": "Something went wrong", "details": str(e)},
            status=500
        )

    # -------------------------
    # 4️⃣ Success response
    # -------------------------
    return JsonResponse({
        "success": True,
        "message": f"{points} points redeemed successfully",
        "remaining_points": loyalty.available_points,
    })
