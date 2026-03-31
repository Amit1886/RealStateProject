from decimal import Decimal

from django.test import TestCase

from accounts.models import SaaSRole, User
from agents.models import Agent
from customers.models import Customer
from intelligence.models import InvestorProfile, PremiumLeadListing, PropertyAlertSubscription
from intelligence.services import (
    dispatch_property_alerts_for_property,
    ingest_aggregated_listing,
    purchase_lead_listing,
    refresh_investor_matches_for_property,
)
from leads.models import Lead, Property
from notifications.models import Notification
from wallet.services import credit, get_or_create_wallet


class IntelligenceServiceTests(TestCase):
    def setUp(self):
        self.customer_user = User.objects.create_user(
            email="intel-customer@example.com",
            username="intel-customer",
            mobile="9100000001",
            password="Customer@123",
            role=SaaSRole.CUSTOMER,
        )
        self.customer, _ = Customer.objects.get_or_create(user=self.customer_user)
        self.agent_user = User.objects.create_user(
            email="intel-agent@example.com",
            username="intel-agent",
            mobile="9100000002",
            password="Agent@123",
            role=SaaSRole.AGENT,
        )
        self.agent = Agent.objects.get(user=self.agent_user)
        self.agent.name = "Intel Agent"
        self.agent.city = "Basti"
        self.agent.district = "Basti"
        self.agent.state = "Uttar Pradesh"
        self.agent.pin_code = "272001"
        self.agent.approval_status = Agent.ApprovalStatus.APPROVED
        self.agent.save()

    def test_aggregated_listing_detects_duplicates(self):
        payload = {
            "title": "2 BHK Apartment in Basti",
            "location": "Civil Lines",
            "city": "Basti",
            "district": "Basti",
            "state": "Uttar Pradesh",
            "pin_code": "272001",
            "price": "3000000",
            "property_type": "apartment",
            "area_sqft": "1200",
            "source": "partner_feed",
            "source_reference": "abc-1",
        }
        first = ingest_aggregated_listing(payload)
        second = ingest_aggregated_listing({**payload, "source_reference": "abc-2"})
        self.assertFalse(first.is_duplicate)
        self.assertTrue(second.is_duplicate)
        self.assertEqual(first.matched_property_id, second.matched_property_id)
        self.assertTrue(first.matched_property.aggregated_property)

    def test_investor_match_created_for_high_roi_property(self):
        investor = InvestorProfile.objects.create(
            user=self.customer_user,
            name="Investor One",
            email=self.customer_user.email,
            phone=self.customer_user.mobile,
            investment_budget=Decimal("5000000"),
            preferred_cities=["Basti"],
            property_type_preferences=["apartment"],
            min_roi_percent=Decimal("8.00"),
        )
        property_obj = Property.objects.create(
            title="Investment Flat",
            price=Decimal("2800000"),
            city="Basti",
            location="Civil Lines",
            district="Basti",
            state="Uttar Pradesh",
            property_type=Property.Type.APARTMENT,
            metadata={"expected_roi_percent": "12"},
        )
        matches = refresh_investor_matches_for_property(property_obj)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].investor, investor)

    def test_property_alert_dispatch_creates_notification(self):
        PropertyAlertSubscription.objects.create(
            customer=self.customer,
            city="Basti",
            property_type=Property.Type.APARTMENT,
            channels=["in_app"],
            trigger_types=["new_property"],
        )
        property_obj = Property.objects.create(
            title="Alert Flat",
            price=Decimal("2500000"),
            city="Basti",
            location="Civil Lines",
            district="Basti",
            state="Uttar Pradesh",
            property_type=Property.Type.APARTMENT,
        )
        dispatch_property_alerts_for_property(property_obj, trigger="new_property")
        self.assertGreaterEqual(Notification.objects.filter(user=self.customer_user).count(), 1)

    def test_premium_lead_purchase_assigns_and_debits_wallet(self):
        lead = Lead.objects.create(
            name="Marketplace Lead",
            mobile="9100000003",
            city="Basti",
            district="Basti",
            state="Uttar Pradesh",
        )
        listing = PremiumLeadListing.objects.create(
            lead=lead,
            category=PremiumLeadListing.Category.HOT,
            price=Decimal("500"),
        )
        credit(self.agent_user, Decimal("1000"), source="seed")
        purchase = purchase_lead_listing(listing, buyer_agent=self.agent, actor_user=self.agent_user)
        wallet = get_or_create_wallet(self.agent_user)
        lead.refresh_from_db()
        listing.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("500"))
        self.assertEqual(listing.status, PremiumLeadListing.Status.SOLD)
        self.assertEqual(lead.assigned_agent_id, self.agent.id)
        self.assertEqual(purchase.amount, Decimal("500"))
