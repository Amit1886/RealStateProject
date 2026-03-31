from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import KYCProfile


@override_settings(MEDIA_ROOT="c:/Users/hp/Pictures/PROJECTREALSTATE/RealStateproject/test_media")
class KYCFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="kyc@example.com",
            password="pass12345",
            username="kycuser",
            mobile="9000000551",
        )
        self.staff = User.objects.create_user(
            email="kyc-admin@example.com",
            password="pass12345",
            username="kycadmin",
            mobile="9000000552",
            is_staff=True,
        )

    def test_user_can_submit_kyc_profile(self):
        self.client.force_login(self.user)
        document = SimpleUploadedFile("pan.txt", b"demo-pan-file", content_type="text/plain")
        response = self.client.post(
            reverse("kyc:dashboard"),
            {
                "full_name": "KYC User",
                "pan_number": "ABCDE1234F",
                "aadhaar_number_masked": "123412341234",
                "document_type": "pan",
                "document_file": document,
                "document_number_masked": "ABCDE1234F",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        profile = KYCProfile.objects.get(user=self.user)
        self.assertEqual(profile.status, KYCProfile.Status.PENDING)
        self.assertEqual(profile.aadhaar_number_masked, "XXXXXXXX1234")
        self.assertEqual(profile.documents.count(), 1)

    def test_staff_can_approve_kyc(self):
        profile = KYCProfile.objects.create(user=self.user, full_name="KYC User", status=KYCProfile.Status.PENDING)
        self.client.force_login(self.staff)
        response = self.client.post(reverse("kyc:review_profile", args=[profile.id]), {"action": "approve"}, follow=True)
        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.status, KYCProfile.Status.VERIFIED)
