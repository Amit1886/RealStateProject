from __future__ import annotations

from django.utils import timezone

from leads.models import Lead, Property

from .models import Article


def recommend_properties_for_article(article: Article, *, user=None, limit=4):
    queryset = Property.objects.exclude(status=Property.Status.REJECTED)
    if article.related_city:
        queryset = queryset.filter(city__iexact=article.related_city)
    if article.related_property_type:
        queryset = queryset.filter(property_type=article.related_property_type)
    if user and getattr(user, "company", None):
        queryset = queryset.filter(company__in=[user.company, None])
    return queryset.order_by("-created_at")[:limit]


def capture_content_lead(*, article: Article, user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    defaults = {
        "company": getattr(user, "company", None),
        "created_by": user,
        "email": user.email or "",
        "mobile": getattr(user, "mobile", "") or "",
        "preferred_location": article.related_city or "",
        "property_type": article.related_property_type or "",
        "source": Lead.Source.WEBSITE,
        "status": Lead.Status.NEW,
        "stage": Lead.Stage.NEW,
        "notes": f"Auto-created from article read: {article.title}",
        "last_contacted_at": timezone.now(),
    }
    lead, _ = Lead.objects.get_or_create(
        company=getattr(user, "company", None),
        created_by=user,
        email=user.email or "",
        source=Lead.Source.WEBSITE,
        defaults={
            **defaults,
            "name": user.get_full_name() or user.username or user.email,
        },
    )
    return lead

