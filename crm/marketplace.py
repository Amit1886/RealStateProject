from django.db import models

from leads.models import Property, PropertyProject


def list_marketplace(approved_only=True):
    qs = PropertyProject.objects.all()
    if approved_only:
        qs = qs.filter(approved=True)
    return list(
        qs.values("id", "title", "location", "price_range", "description", "builder_id", "approved")
    )


def assign_project_to_lead(project_id, lead):
    project = PropertyProject.objects.filter(id=project_id, approved=True).first()
    if not project:
        return None
    # store in lead metadata
    meta = lead.metadata or {}
    meta["project_id"] = project.id
    lead.metadata = meta
    lead.save(update_fields=["metadata", "updated_at"])
    return project
