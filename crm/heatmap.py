from django.db import models

from leads.models import Lead


def heatmap_points(filters=None):
    filters = filters or {}
    qs = Lead.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    if city := filters.get("city"):
        qs = qs.filter(preferred_location__iexact=city)
    if prop_type := filters.get("property_type"):
        qs = qs.filter(property_type=prop_type)
    if since := filters.get("since"):
        qs = qs.filter(created_at__gte=since)
    return list(qs.values("latitude", "longitude"))
