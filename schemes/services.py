from __future__ import annotations

from decimal import Decimal

from .models import Scheme, UserSchemeMatch


def calculate_match_score(*, scheme: Scheme, income, location: str, ownership_status: str) -> int:
    score = 40
    income_value = Decimal(str(income or 0))
    if scheme.income_limit <= 0 or income_value <= scheme.income_limit:
        score += 25
    location_text = (location or "").strip().lower()
    if scheme.city and scheme.city.lower() in location_text:
        score += 20
    elif scheme.district and scheme.district.lower() in location_text:
        score += 15
    elif scheme.state and scheme.state.lower() in location_text:
        score += 10
    if scheme.ownership_status in {Scheme.OwnershipStatus.ANY, ownership_status}:
        score += 15
    return min(score, 100)


def get_matching_schemes(*, income, location: str, ownership_status: str, company=None):
    schemes = Scheme.objects.filter(active=True)
    if company is not None:
        schemes = schemes.filter(company__in=[company, None])
    matches = []
    for scheme in schemes:
        if scheme.income_limit and Decimal(str(income or 0)) > scheme.income_limit:
            continue
        if scheme.ownership_status not in {Scheme.OwnershipStatus.ANY, ownership_status or Scheme.OwnershipStatus.ANY}:
            continue
        score = calculate_match_score(
            scheme=scheme,
            income=income,
            location=location,
            ownership_status=ownership_status,
        )
        matches.append((scheme, score))
    return sorted(matches, key=lambda item: item[1], reverse=True)


def create_scheme_matches(*, user, income, location, ownership_status, property_obj=None, company=None):
    matches = []
    for scheme, score in get_matching_schemes(
        income=income,
        location=location,
        ownership_status=ownership_status,
        company=company,
    )[:5]:
        match, _ = UserSchemeMatch.objects.update_or_create(
            user=user,
            scheme=scheme,
            property=property_obj,
            defaults={
                "company": company,
                "income": income,
                "location": location,
                "ownership_status": ownership_status,
                "match_score": score,
            },
        )
        matches.append(match)
    return matches

