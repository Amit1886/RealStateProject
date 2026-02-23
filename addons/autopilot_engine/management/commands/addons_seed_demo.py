from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed demo provider configs (Razorpay/WhatsApp/IVR/Courier) to show end-to-end flow."

    def add_arguments(self, parser):
        parser.add_argument("--branch-code", default="default")
        parser.add_argument("--apply", action="store_true", help="Actually write demo rows (default is dry-run).")

    def handle(self, *args, **options):
        branch_code = options["branch_code"]
        apply = bool(options["apply"])

        if not apply:
            self.stdout.write(self.style.WARNING("Dry-run (no DB changes). Use --apply to create demo rows."))

        seeded = []

        # E-commerce payment gateways
        try:
            from addons.ecommerce_engine.models import PaymentGatewayConfig

            rows = [
                {
                    "provider": PaymentGatewayConfig.Provider.RAZORPAY,
                    "key_id": "rzp_test_DEMO_KEYID",
                    "key_secret": "DEMO_KEYSECRET",
                    "webhook_secret": "DEMO_WEBHOOK_SECRET",
                    "extra": {"note": "Demo Razorpay config. Replace with real credentials."},
                },
                {
                    "provider": PaymentGatewayConfig.Provider.STRIPE,
                    "key_id": "sk_test_DEMO",
                    "key_secret": "DEMO",
                    "webhook_secret": "whsec_DEMO",
                    "extra": {"note": "Demo Stripe config. Replace with real credentials."},
                },
            ]
            for spec in rows:
                seeded.append(f"ecommerce.payment_gateway.{spec['provider']}")
                if not apply:
                    continue
                PaymentGatewayConfig.objects.update_or_create(
                    branch_code=branch_code,
                    provider=spec["provider"],
                    defaults={
                        "is_active": True,
                        "sandbox": True,
                        "key_id": spec["key_id"],
                        "key_secret": spec["key_secret"],
                        "webhook_secret": spec["webhook_secret"],
                        "extra": spec["extra"],
                    },
                )
        except Exception:
            self.stdout.write(self.style.WARNING("Skipped PaymentGatewayConfig (ecommerce_engine not installed/migrated)."))

        # AI Call Assistant provider configs
        try:
            from addons.ai_call_assistant.models import IVRProviderConfig, WhatsAppProviderConfig

            seeded.append("ai_call_assistant.whatsapp.meta_cloud")
            seeded.append("ai_call_assistant.ivr.exotel")
            if apply:
                WhatsAppProviderConfig.objects.update_or_create(
                    branch_code=branch_code,
                    provider=WhatsAppProviderConfig.Provider.META_CLOUD,
                    defaults={
                        "is_active": True,
                        "sandbox": True,
                        "demo_sender": "DEMO_PHONE_NUMBER_ID",
                        "access_token": "DEMO_ACCESS_TOKEN",
                        "webhook_verify_token": "DEMO_VERIFY_TOKEN",
                        "extra": {"note": "Demo WhatsApp Cloud config. Replace with real token + phone number id."},
                    },
                )
                IVRProviderConfig.objects.update_or_create(
                    branch_code=branch_code,
                    provider=IVRProviderConfig.Provider.EXOTEL,
                    defaults={
                        "is_active": True,
                        "sandbox": True,
                        "demo_number": "+91-DEMO-IVR",
                        "api_key": "DEMO_API_KEY",
                        "api_secret": "DEMO_API_SECRET",
                        "extra": {"note": "Demo IVR config. Replace with real Exotel/Twilio credentials."},
                    },
                )
        except Exception:
            self.stdout.write(self.style.WARNING("Skipped WhatsApp/IVR configs (ai_call_assistant not installed/migrated)."))

        # Courier configs
        try:
            from addons.courier_integration.models import CourierProvider, CourierProviderConfig

            for provider, base_url in [
                (CourierProvider.SHIPROCKET, "https://apiv2.shiprocket.in/v1/external"),
                (CourierProvider.DELHIVERY, "https://track.delhivery.com"),
            ]:
                seeded.append(f"courier.provider.{provider}")
                if not apply:
                    continue
                CourierProviderConfig.objects.update_or_create(
                    branch_code=branch_code,
                    provider=provider,
                    defaults={
                        "is_active": True,
                        "sandbox": True,
                        "base_url": base_url,
                        "api_key": "DEMO_API_KEY",
                        "api_secret": "DEMO_API_SECRET",
                        "extra": {"note": f"Demo {provider} config. Replace with real credentials."},
                    },
                )
        except Exception:
            self.stdout.write(self.style.WARNING("Skipped courier configs (courier_integration not installed/migrated)."))

        self.stdout.write("Demo configs:")
        for item in seeded:
            self.stdout.write(f"- {item}")

        if apply:
            self.stdout.write(self.style.SUCCESS("Demo provider configs created/updated."))

