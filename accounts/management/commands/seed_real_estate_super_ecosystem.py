from __future__ import annotations

from decimal import Decimal
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.files import File
from django.utils import timezone

from accounts.models import SaaSRole, User, UserProfile
from agents.models import Agent, AgentCoverageArea
from content.models import Article, ArticleRead, Category
from leads.models import Lead, Property, PropertyImage, PropertyVideo
from loans.models import Bank, LoanApplication, LoanProduct
from loans.services import build_application_snapshot
from saas_core.models import Company
from schemes.models import Scheme
from schemes.services import create_scheme_matches
from verification.models import PropertyVerification
from visits.models import SiteVisit
from wallet.models import Wallet, WalletTransaction


class Command(BaseCommand):
    help = "Seed the Django real-estate super ecosystem demo with users, properties, banks, schemes, and content."

    def handle(self, *args, **options):
        with transaction.atomic():
            company, _ = Company.objects.get_or_create(
                name="Demo Realty",
                defaults={"currency": "INR", "timezone": "Asia/Kolkata", "active": True},
            )

            admin = self._upsert_user(
                email="admin@example.com",
                password="123456",
                full_name="Platform Admin",
                role=SaaSRole.SUPER_ADMIN,
                company=company,
                mobile="9000000001",
                is_staff=True,
                is_superuser=True,
            )
            agent_user = self._upsert_user(
                email="agent@example.com",
                password="123456",
                full_name="Demo Realty",
                role=SaaSRole.AGENT,
                company=company,
                mobile="9000000002",
            )

            customers = []
            for idx in range(1, 6):
                customers.append(
                    self._upsert_user(
                        email=f"user{idx}@example.com",
                        password="123456",
                        full_name=f"Demo User {idx}",
                        role=SaaSRole.CUSTOMER,
                        company=company,
                        mobile=f"900000001{idx}",
                    )
                )

            agent_profile, _ = Agent.objects.get_or_create(
                user=agent_user,
                defaults={
                    "name": "Demo Realty",
                    "phone": agent_user.mobile or "",
                },
            )
            agent_profile.name = "Demo Realty"
            agent_profile.phone = agent_user.mobile or ""
            agent_profile.approval_status = Agent.ApprovalStatus.APPROVED
            agent_profile.kyc_verified = True
            agent_profile.city = "Basti"
            agent_profile.district = "Basti"
            agent_profile.state = "Uttar Pradesh"
            agent_profile.pin_code = "272001"
            agent_profile.experience_years = 6
            agent_profile.total_sales = Decimal("18500000.00")
            agent_profile.rating = Decimal("4.80")
            agent_profile.save()
            AgentCoverageArea.objects.update_or_create(
                agent=agent_profile,
                pin_code="272001",
                defaults={
                    "country": "India",
                    "state": "Uttar Pradesh",
                    "district": "Basti",
                    "city": "Basti",
                    "is_primary": True,
                    "is_active": True,
                },
            )

            self._ensure_wallet(admin, Decimal("150000.00"))
            self._ensure_wallet(agent_user, Decimal("85000.00"))
            for idx, customer in enumerate(customers, start=1):
                self._ensure_wallet(customer, Decimal(str(idx * 2500)))

            banks = self._seed_banks(company)
            schemes = self._seed_schemes(company)
            articles = self._seed_articles(company, admin)
            properties = self._seed_properties(company, agent_user, agent_profile, customers)
            self._seed_leads_and_visits(company, agent_user, agent_profile, customers, properties)
            self._seed_loans(company, customers, properties, banks)
            self._seed_verification(company, customers[0], properties[0])
            create_scheme_matches(
                user=customers[0],
                income=Decimal("450000.00"),
                location="Basti Uttar Pradesh",
                ownership_status=Scheme.OwnershipStatus.FIRST_TIME,
                property_obj=properties[0],
                company=company,
            )
            ArticleRead.objects.get_or_create(article=articles[0], user=customers[0])

            self.stdout.write(self.style.SUCCESS("Real estate super ecosystem demo data seeded successfully."))

    def _upsert_user(self, *, email, password, full_name, role, company, mobile, is_staff=False, is_superuser=False):
        username = email.split("@")[0]
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={
                "username": username,
                "mobile": mobile,
            },
        )
        user.username = username
        user.mobile = mobile
        user.role = role
        user.company = company
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.is_active = True
        user.email_verified = True
        user.mobile_verified = True
        user.is_otp_verified = True
        user.set_password(password)
        user.save()
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "full_name": full_name,
                "mobile": mobile,
                "business_name": "Demo Realty" if role == SaaSRole.AGENT else full_name,
                "business_type": "Real Estate",
                "address": "Civil Lines, Basti",
            },
        )
        return user

    def _ensure_wallet(self, user, balance: Decimal):
        wallet, _ = Wallet.objects.get_or_create(user=user)
        wallet.balance = balance
        wallet.save(update_fields=["balance", "updated_at"])
        WalletTransaction.objects.get_or_create(
            wallet=wallet,
            entry_type=WalletTransaction.EntryType.CREDIT,
            amount=balance,
            source="demo_seed",
            reference=f"seed-{user.id}",
        )

    def _seed_banks(self, company):
        bank_specs = [
            ("SBI", "State-backed home loans", Decimal("8.45"), Decimal("4500000.00"), 20),
            ("HDFC Bank", "Premium urban housing finance", Decimal("8.65"), Decimal("6500000.00"), 25),
            ("ICICI Bank", "Fast-processing property finance", Decimal("8.85"), Decimal("5500000.00"), 22),
        ]
        banks = []
        for name, summary, rate, amount, tenure in bank_specs:
            bank, _ = Bank.objects.update_or_create(
                name=name,
                defaults={
                    "company": company,
                    "website": "https://example.com",
                    "support_email": f"{name.split()[0].lower()}@example.com",
                    "support_phone": "1800-000-000",
                    "active": True,
                },
            )
            LoanProduct.objects.update_or_create(
                bank=bank,
                name="Home Loan",
                defaults={
                    "company": company,
                    "property_type": LoanProduct.PropertyType.APARTMENT,
                    "interest_rate": rate,
                    "loan_amount": amount,
                    "tenure_years": tenure,
                    "emi_estimate": Decimal("0.00"),
                    "min_income_required": Decimal("50000.00"),
                    "metadata": {"summary": summary},
                    "active": True,
                },
            )
            banks.append(bank)
        return banks

    def _seed_schemes(self, company):
        scheme_specs = [
            ("PMAY Urban", "Credit-linked subsidy for first home buyers", Decimal("1800000.00"), Scheme.OwnershipStatus.FIRST_TIME),
            ("UP Affordable Housing Support", "Location support for budget buyers", Decimal("1200000.00"), Scheme.OwnershipStatus.ANY),
            ("Women Property Ownership Benefit", "Stamp duty and subsidy guidance", Decimal("2200000.00"), Scheme.OwnershipStatus.ANY),
        ]
        schemes = []
        for title, summary, income_limit, ownership in scheme_specs:
            scheme, _ = Scheme.objects.update_or_create(
                title=title,
                defaults={
                    "company": company,
                    "summary": summary,
                    "description": summary,
                    "state": "Uttar Pradesh",
                    "district": "Basti",
                    "city": "Basti",
                    "income_limit": income_limit,
                    "ownership_status": ownership,
                    "apply_url": "https://example.com/scheme",
                    "active": True,
                },
            )
            schemes.append(scheme)
        return schemes

    def _seed_articles(self, company, author):
        categories = {
            "Buying Guide": "buying-guide",
            "Legal Checklist": "legal-checklist",
            "Investment Tips": "investment-tips",
        }
        category_rows = {}
        for name in categories:
            category_rows[name], _ = Category.objects.get_or_create(name=name)

        article_specs = [
            ("How to choose your first apartment in Basti", "Buying Guide", "Basti", "apartment"),
            ("Legal documents you should verify before purchase", "Legal Checklist", "Basti", "house"),
            ("Best localities for long-term real estate ROI", "Investment Tips", "Basti", "villa"),
            ("Budget buyer checklist for site visits", "Buying Guide", "Basti", "flat"),
            ("How to compare loans and government schemes together", "Investment Tips", "Basti", "apartment"),
        ]
        articles = []
        for title, category_name, city, property_type in article_specs:
            article, _ = Article.objects.update_or_create(
                title=title,
                defaults={
                    "company": company,
                    "category": category_rows[category_name],
                    "author": author,
                    "excerpt": title,
                    "body": f"{title}. This demo article powers lead generation, property recommendations, and education-center flows.",
                    "tags": [category_name.lower().replace(" ", "-"), city.lower()],
                    "related_city": city,
                    "related_property_type": property_type,
                    "is_published": True,
                },
            )
            articles.append(article)
        return articles

    def _seed_properties(self, company, agent_user, agent_profile, customers):
        property_specs = [
            ("Skyline Residency 2 BHK", Decimal("3200000.00"), "apartment"),
            ("Green Court Family Flat", Decimal("2800000.00"), "flat"),
            ("Royal Villa Estate", Decimal("6800000.00"), "villa"),
            ("City Center Shop", Decimal("2200000.00"), "shop"),
            ("Prime Office Space", Decimal("4500000.00"), "office"),
            ("Warehouse Link Yard", Decimal("5200000.00"), "warehouse"),
            ("Sunrise Plot Phase 1", Decimal("1800000.00"), "land"),
            ("Lakeview House", Decimal("3900000.00"), "house"),
            ("Metro Commercial Hub", Decimal("7500000.00"), "commercial"),
            ("Budget Apartment Block", Decimal("2500000.00"), "apartment"),
        ]
        properties = []
        for idx, (title, price, property_type) in enumerate(property_specs, start=1):
            owner = agent_user if idx <= 6 else customers[(idx - 1) % len(customers)]
            property_obj, _ = Property.objects.update_or_create(
                title=title,
                city="Basti",
                defaults={
                    "company": company,
                    "owner": owner,
                    "assigned_agent": agent_profile,
                    "price": price,
                    "location": f"Sector {idx}, Civil Lines",
                    "district": "Basti",
                    "state": "Uttar Pradesh",
                    "country": "India",
                    "pin_code": "272001",
                    "property_type": property_type,
                    "listing_type": Property.ListingType.SALE,
                    "area_sqft": Decimal("1200.00") + Decimal(idx * 75),
                    "bedrooms": 2 if property_type in {"apartment", "flat", "house", "villa"} else 0,
                    "bathrooms": 2 if property_type in {"apartment", "flat", "house", "villa"} else 1,
                    "parking": 1,
                    "description": "Seeded super ecosystem demo property.",
                    "status": Property.Status.APPROVED,
                    "metadata": {"badges": ["high_roi"] if idx in {1, 3, 8} else []},
                },
            )
            if title == "Lakeview House":
                self._seed_lakeview_media(property_obj)
            properties.append(property_obj)
        return properties

    def _seed_lakeview_media(self, property_obj):
        demo_dir = Path(settings.BASE_DIR) / "media" / "demo"
        image_path = demo_dir / "lakeview-house.png"
        video_path = demo_dir / "lakeview-house.mp4"
        property_obj.images.all().delete()
        property_obj.videos.all().delete()
        PropertyImage.objects.filter(property=property_obj, caption__icontains="Lakeview House").delete()
        PropertyVideo.objects.filter(property=property_obj, caption__icontains="Lakeview House").delete()
        if image_path.exists():
            with image_path.open("rb") as fh:
                PropertyImage.objects.update_or_create(
                    property=property_obj,
                    caption="Lakeview House - Front Elevation",
                    defaults={
                        "image": File(fh, name=image_path.name),
                        "image_url": "/static/demo/lakeview-house.png",
                        "sort_order": 0,
                        "is_primary": True,
                    },
                )
        if video_path.exists():
            with video_path.open("rb") as fh:
                PropertyVideo.objects.update_or_create(
                    property=property_obj,
                    caption="Lakeview House - Walkthrough Tour",
                    defaults={
                        "video": File(fh, name=video_path.name),
                        "video_url": "/static/demo/lakeview-house.mp4",
                    },
                )

    def _seed_leads_and_visits(self, company, agent_user, agent_profile, customers, properties):
        for idx, customer in enumerate(customers[:3], start=1):
            lead, _ = Lead.objects.update_or_create(
                company=company,
                email=customer.email,
                defaults={
                    "created_by": customer,
                    "assigned_to": agent_user,
                    "assigned_agent": agent_profile,
                    "interested_property": properties[idx - 1],
                    "name": customer.get_full_name() or customer.username,
                    "mobile": customer.mobile or "",
                    "budget": Decimal("3500000.00"),
                    "preferred_location": "Basti",
                    "property_type": properties[idx - 1].property_type,
                    "source": Lead.Source.WEBSITE,
                    "status": Lead.Status.CONTACTED if idx == 1 else Lead.Status.NEW,
                    "stage": Lead.Stage.VISIT_SCHEDULED if idx == 1 else Lead.Stage.NEW,
                    "city": "Basti",
                    "district": "Basti",
                    "state": "Uttar Pradesh",
                    "pincode_text": "272001",
                    "notes": "Seeded demo lead",
                },
            )
            SiteVisit.objects.update_or_create(
                lead=lead,
                agent=agent_profile,
                defaults={
                    "visit_date": timezone.now() + timedelta(days=idx),
                    "location": properties[idx - 1].location,
                    "status": SiteVisit.Status.SCHEDULED,
                    "notes": "Seeded demo visit",
                },
            )

    def _seed_loans(self, company, customers, properties, banks):
        first_product = LoanProduct.objects.filter(bank=banks[0]).first()
        if not first_product:
            return
        snapshot = build_application_snapshot(
            requested_amount=Decimal("2500000.00"),
            interest_rate=first_product.interest_rate,
            tenure_years=20,
            monthly_income=Decimal("85000.00"),
            existing_emi=Decimal("12000.00"),
        )
        LoanApplication.objects.update_or_create(
            applicant=customers[0],
            property=properties[0],
            loan_product=first_product,
            defaults={
                "company": company,
                "requested_amount": Decimal("2500000.00"),
                "tenure_years": 20,
                "monthly_income": Decimal("85000.00"),
                "existing_emi": Decimal("12000.00"),
                "emi_estimate": snapshot["emi_estimate"],
                "eligibility_ratio": snapshot["eligibility_ratio"],
                "status": snapshot["status"],
                "notes": "Seeded demo loan application",
            },
        )

    def _seed_verification(self, company, customer, property_obj):
        PropertyVerification.objects.update_or_create(
            property=property_obj,
            requested_by=customer,
            defaults={
                "company": company,
                "status": PropertyVerification.Status.APPROVED,
                "notes": "Seeded verified property request",
                "reviewed_by": User.objects.filter(email="admin@example.com").first(),
                "reviewed_at": timezone.now(),
            },
        )
