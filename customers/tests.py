from django.test import TestCase
from rest_framework.test import APITestCase

from accounts.models import SaaSRole, User
from customers.models import Customer
from agents.models import AgentCoverageArea
from leads.models import Lead, Property
from saas_core.models import Company


class CustomerSignalTests(TestCase):
    def test_customer_profile_created_for_customer_role(self):
        user = User.objects.create_user(
            email="customer-signal@example.com",
            username="customer-signal",
            mobile="9000000001",
            password="Customer@123",
            role=SaaSRole.CUSTOMER,
        )
        self.assertTrue(Customer.objects.filter(user=user).exists())


class CustomerDashboardTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Customer Dashboard Realty")
        self.customer_user = User.objects.create_user(
            email="customer-dashboard@example.com",
            username="customer-dashboard",
            mobile="9555555555",
            password="Customer@123",
            role=SaaSRole.CUSTOMER,
            company=self.company,
        )
        self.agent_user = User.objects.create_user(
            email="agent-dashboard@example.com",
            username="agent-dashboard",
            mobile="9666666666",
            password="Agent@123",
            role=SaaSRole.AGENT,
            company=self.company,
        )
        self.agent = self.agent_user.agent_profile
        self.agent.name = "Dashboard Agent"
        self.agent.phone = self.agent_user.mobile
        self.agent.city = "Jaipur"
        self.agent.district = "Jaipur"
        self.agent.state = "Rajasthan"
        self.agent.pin_code = "302001"
        self.agent.approval_status = self.agent.ApprovalStatus.APPROVED
        self.agent.save()
        AgentCoverageArea.objects.create(
            agent=self.agent,
            city="Jaipur",
            district="Jaipur",
            state="Rajasthan",
            pin_code="302001",
            is_primary=True,
        )
        self.customer = self.customer_user.customer_profile
        self.customer.company = self.company
        self.customer.assigned_agent = self.agent
        self.customer.city = "Jaipur"
        self.customer.district = "Jaipur"
        self.customer.state = "Rajasthan"
        self.customer.pin_code = "302001"
        self.customer.save()
        self.lead = Lead.objects.create(
            company=self.company,
            name="Dashboard Buyer",
            mobile=self.customer_user.mobile,
            email=self.customer_user.email,
            city="Jaipur",
            district="Jaipur",
            state="Rajasthan",
            pincode_text="302001",
            assigned_agent=self.agent,
            assigned_to=self.agent_user,
            converted_customer=self.customer,
            status=Lead.Status.CONVERTED,
            stage=Lead.Stage.CONVERTED,
        )
        Property.objects.create(
            title="Jaipur Villa",
            price="4500000.00",
            city="Jaipur",
            district="Jaipur",
            state="Rajasthan",
            pin_code="302001",
            property_type="villa",
            listing_type="sale",
            status="approved",
            company=self.company,
            assigned_agent=self.agent,
        )
        Property.objects.create(
            title="Delhi Flat",
            price="5500000.00",
            city="Delhi",
            district="Delhi",
            state="Delhi",
            pin_code="110001",
            property_type="flat",
            listing_type="sale",
            status="approved",
            company=self.company,
            assigned_agent=self.agent,
        )
        self.client.force_authenticate(self.customer_user)

    def test_dashboard_returns_only_local_properties(self):
        response = self.client.get("/api/v1/customers/customers/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["lead"]["id"], self.lead.id)
        self.assertEqual(len(response.data["nearby_properties"]), 1)
        self.assertEqual(response.data["nearby_properties"][0]["title"], "Jaipur Villa")
