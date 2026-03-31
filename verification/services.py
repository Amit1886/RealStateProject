from __future__ import annotations


def apply_verified_badge(property_obj, *, verified: bool):
    metadata = property_obj.metadata or {}
    badges = list(metadata.get("badges") or [])
    if verified and "verified_property" not in badges:
        badges.append("verified_property")
    if not verified:
        badges = [badge for badge in badges if badge != "verified_property"]
    metadata["badges"] = badges
    property_obj.metadata = metadata
    property_obj.save(update_fields=["metadata", "updated_at"])

