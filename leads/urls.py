from django.urls import include, path
from rest_framework.routers import DefaultRouter

from realstateproject.lazy_views import lazy_view, lazy_viewset

router = DefaultRouter()
router.register("leads", lazy_viewset("leads.views.LeadViewSet"), basename="leads")
router.register("lead-activities", lazy_viewset("leads.views.LeadActivityViewSet"), basename="lead-activities")
router.register("assignments", lazy_viewset("leads.views.LeadAssignmentViewSet"), basename="lead-assignments-current")
router.register("lead-assignments", lazy_viewset("leads.views.LeadAssignmentLogViewSet"), basename="lead-assignments")
router.register("sources", lazy_viewset("leads.views.LeadSourceViewSet"), basename="lead-sources")
router.register("import-batches", lazy_viewset("leads.views.LeadImportBatchViewSet"), basename="lead-import-batches")
router.register("properties", lazy_viewset("leads.views.PropertyViewSet"), basename="properties")
router.register("property-media", lazy_viewset("leads.views.PropertyMediaViewSet"), basename="property-media")
router.register("property-locations", lazy_viewset("leads.views.PropertyLocationViewSet"), basename="property-locations")
router.register("property-images", lazy_viewset("leads.views.PropertyImageViewSet"), basename="property-images")
router.register("property-videos", lazy_viewset("leads.views.PropertyVideoViewSet"), basename="property-videos")
router.register("property-features", lazy_viewset("leads.views.PropertyFeatureViewSet"), basename="property-features")
router.register("builders", lazy_viewset("leads.views.BuilderViewSet"), basename="builders")
router.register("projects", lazy_viewset("leads.views.PropertyProjectViewSet"), basename="projects")
router.register("property-views", lazy_viewset("leads.views.PropertyViewLogViewSet"), basename="property-views")
router.register("followups", lazy_viewset("leads.views.FollowUpLeadViewSet"), basename="lead-followups")
router.register("documents", lazy_viewset("leads.views.LeadDocumentViewSet"), basename="lead-documents")
router.register("agreements", lazy_viewset("leads.views.AgreementViewSet"), basename="agreements")

urlpatterns = [
    path("create/", lazy_view("leads.views.LeadCaptureAPIView"), name="lead-capture"),
    path("assign/geo/", lazy_view("leads.views.LeadGeoAssignAPIView"), name="lead-geo-assign"),
    path("photo-to-lead/", lazy_view("leads.views.PhotoToLeadAPIView"), name="photo-to-lead"),
    path("lead/lock/", lazy_view("leads.views.LeadLockAPIView"), name="lead-lock"),
    path("lead/unlock/", lazy_view("leads.views.LeadUnlockAPIView"), name="lead-unlock"),
    path("webhooks/<slug:source_key>/", lazy_view("leads.views.LeadWebhookAPIView"), name="lead-webhook"),
    path("properties/list/", lazy_view("leads.views.PropertyViewSet", as_view_kwargs={"get": "list"}), name="property-list-alias"),
    path("properties/create/", lazy_view("leads.views.PropertyViewSet", as_view_kwargs={"post": "create"}), name="property-create-alias"),
    path("builders/create/", lazy_view("leads.views.BuilderViewSet", as_view_kwargs={"post": "create"}), name="builder-create-alias"),
    path("projects/list/", lazy_view("leads.views.PropertyProjectViewSet", as_view_kwargs={"get": "list"}), name="project-list-alias"),
    path("projects/create/", lazy_view("leads.views.PropertyProjectViewSet", as_view_kwargs={"post": "create"}), name="project-create-alias"),
    path("emi/", lazy_view("leads.views.EMICalculatorAPIView"), name="emi-calculator"),
    path("process-followups/", lazy_view("leads.views.FollowUpProcessorAPIView"), name="lead-followups-process"),
    path("", include(router.urls)),
]
