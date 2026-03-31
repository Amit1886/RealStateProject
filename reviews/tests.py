from rest_framework.test import APITestCase

from accounts.models import SaaSRole, User
from leads.models import Property
from reviews.models import Review


class ReviewApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="reviewer@example.com",
            username="reviewer",
            mobile="9000000003",
            password="Customer@123",
            role=SaaSRole.CUSTOMER,
        )
        self.property = Property.objects.create(
            title="Review Test Flat",
            price="2500000.00",
            city="Basti",
            location="Civil Lines",
            property_type=Property.Type.FLAT,
            owner=self.user,
        )
        self.client.force_authenticate(self.user)

    def test_customer_can_create_property_review(self):
        response = self.client.post(
            "/api/v1/reviews/property-reviews/",
            {
                "property": self.property.id,
                "rating": 5,
                "review_text": "Great listing",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Review.objects.filter(property=self.property).count(), 1)
