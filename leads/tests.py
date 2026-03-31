import json
import io
import zipfile

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from accounts.models import SaaSRole, User
from agents.models import Agent, AgentCoverageArea
from customers.models import Customer
from deals.models import Deal, Payment
from leads.models import Lead
from leads.services import auto_assign_lead
from saas_core.models import Company


@override_settings(VOICE_AI_ENABLED=False)
class LeadRoutingTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme Realty")

    def _make_agent(self, *, email: str, name: str, pin_code: str = "", district: str = "", state: str = "", city: str = ""):
        user = User.objects.create(
            email=email,
            username=name.lower().replace(" ", "_"),
            mobile=f"90000{User.objects.count() + 1000}",
            role=SaaSRole.AGENT,
            company=self.company,
        )
        agent = user.agent_profile
        agent.name = name
        agent.phone = user.mobile
        agent.city = city
        agent.district = district
        agent.state = state
        agent.pin_code = pin_code
        agent.approval_status = Agent.ApprovalStatus.APPROVED
        agent.save()
        AgentCoverageArea.objects.create(
            agent=agent,
            city=city,
            district=district,
            state=state,
            pin_code=pin_code,
            is_primary=True,
        )
        return agent

    def test_auto_assign_uses_pin_code_then_balances_load(self):
        agent_a = self._make_agent(
            email="agent-a@example.com",
            name="Agent A",
            pin_code="272001",
            district="Basti",
            state="Uttar Pradesh",
            city="Basti",
        )
        agent_b = self._make_agent(
            email="agent-b@example.com",
            name="Agent B",
            pin_code="272001",
            district="Basti",
            state="Uttar Pradesh",
            city="Basti",
        )

        lead_one = Lead.objects.create(
            company=self.company,
            name="Lead One",
            mobile="9999900001",
            pincode_text="272001",
            district="Basti",
            state="Uttar Pradesh",
            city="Basti",
        )
        auto_assign_lead(lead=lead_one)
        self.assertIn(lead_one.assigned_agent, {agent_a, agent_b})
        self.assertEqual(lead_one.assignment_logs.first().matched_on, "pin_code")

        lead_two = Lead.objects.create(
            company=self.company,
            name="Lead Two",
            mobile="9999900002",
            pincode_text="272001",
            district="Basti",
            state="Uttar Pradesh",
            city="Basti",
        )
        auto_assign_lead(lead=lead_two)

        self.assertIsNotNone(lead_two.assigned_agent)
        self.assertNotEqual(lead_two.assigned_agent_id, lead_one.assigned_agent_id)
        self.assertEqual(lead_two.assignment_logs.first().matched_on, "pin_code")

    def test_auto_assign_falls_back_to_district_then_state(self):
        district_agent = self._make_agent(
            email="district@example.com",
            name="District Agent",
            district="Lucknow",
            state="Uttar Pradesh",
            city="Lucknow",
        )
        state_agent = self._make_agent(
            email="state@example.com",
            name="State Agent",
            state="Maharashtra",
            city="Mumbai",
        )

        district_lead = Lead.objects.create(
            company=self.company,
            name="District Lead",
            mobile="9999900100",
            district="Lucknow",
            state="Uttar Pradesh",
            city="Lucknow",
        )
        auto_assign_lead(lead=district_lead)
        self.assertEqual(district_lead.assigned_agent, district_agent)
        self.assertEqual(district_lead.assignment_logs.first().matched_on, "district")

        state_lead = Lead.objects.create(
            company=self.company,
            name="State Lead",
            mobile="9999900101",
            state="Maharashtra",
            city="Pune",
        )
        auto_assign_lead(lead=state_lead)
        self.assertEqual(state_lead.assigned_agent, state_agent)
        self.assertEqual(state_lead.assignment_logs.first().matched_on, "state")


@override_settings(VOICE_AI_ENABLED=False)
class LeadAutomationApiTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Automation Realty")
        self.admin = User.objects.create_user(
            email="admin-automation@example.com",
            username="admin-automation",
            mobile="9111111111",
            password="Admin@123",
            role=SaaSRole.SUPER_ADMIN,
            company=self.company,
            is_staff=True,
        )
        self.agent_user = User.objects.create_user(
            email="agent-automation@example.com",
            username="agent-automation",
            mobile="9222222222",
            password="Agent@123",
            role=SaaSRole.AGENT,
            company=self.company,
        )
        self.agent = self.agent_user.agent_profile
        self.agent.name = "Automation Agent"
        self.agent.phone = self.agent_user.mobile
        self.agent.city = "Lucknow"
        self.agent.district = "Lucknow"
        self.agent.state = "Uttar Pradesh"
        self.agent.pin_code = "226010"
        self.agent.approval_status = Agent.ApprovalStatus.APPROVED
        self.agent.save()
        AgentCoverageArea.objects.create(
            agent=self.agent,
            city="Lucknow",
            district="Lucknow",
            state="Uttar Pradesh",
            pin_code="226010",
            is_primary=True,
        )
        self.client.force_authenticate(self.admin)

    def test_csv_import_creates_batch_and_assigns_leads(self):
        upload = SimpleUploadedFile(
            "leads.csv",
            b"name,phone,email,city,district,state,pincode,budget\nAman,9333333333,aman@example.com,Lucknow,Lucknow,Uttar Pradesh,226010,2500000\n",
            content_type="text/csv",
        )
        response = self.client.post(
            "/api/v1/leads/leads/import_csv/",
            {"file": upload, "source": "Demo CSV", "auto_assign": True},
        )

        self.assertEqual(response.status_code, 201)
        lead = Lead.objects.get(mobile="9333333333")
        self.assertEqual(lead.assigned_agent_id, self.agent.id)
        self.assertEqual(response.data["created_leads"], 1)

    def test_convert_endpoint_creates_customer_deal_and_payment(self):
        lead = Lead.objects.create(
            company=self.company,
            name="Buyer One",
            mobile="9444444444",
            email="buyer-one@example.com",
            city="Lucknow",
            district="Lucknow",
            state="Uttar Pradesh",
            pincode_text="226010",
            assigned_agent=self.agent,
            assigned_to=self.agent_user,
            budget=3500000,
        )
        response = self.client.post(
            f"/api/v1/leads/leads/{lead.id}/convert/",
            {"deal_amount": "3200000.00", "customer_name": "Buyer One"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.Status.CONVERTED)
        self.assertTrue(Customer.objects.filter(id=response.data["customer_id"]).exists())
        self.assertTrue(Deal.objects.filter(lead=lead).exists())
        self.assertTrue(Payment.objects.filter(deal__lead=lead, payment_type=Payment.PaymentType.CUSTOMER_PAYMENT).exists())

    def _build_minimal_xlsx(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "[Content_Types].xml",
                """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
            )
            zf.writestr(
                "_rels/.rels",
                """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
            )
            zf.writestr(
                "xl/workbook.xml",
                """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Sheet1" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>""",
            )
            zf.writestr(
                "xl/_rels/workbook.xml.rels",
                """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
            )
            zf.writestr(
                "xl/worksheets/sheet1.xml",
                """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>fullname</t></is></c>
      <c r="B1" t="inlineStr"><is><t>mobile</t></is></c>
      <c r="C1" t="inlineStr"><is><t>email_address</t></is></c>
      <c r="D1" t="inlineStr"><is><t>city</t></is></c>
    </row>
    <row r="2">
      <c r="A2" t="inlineStr"><is><t>Sheet Lead</t></is></c>
      <c r="B2" t="inlineStr"><is><t>9555512345</t></is></c>
      <c r="C2" t="inlineStr"><is><t>sheet@example.com</t></is></c>
      <c r="D2" t="inlineStr"><is><t>Lucknow</t></is></c>
    </row>
  </sheetData>
</worksheet>""",
            )
        buffer.seek(0)
        return SimpleUploadedFile("leads.xlsx", buffer.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def test_import_preview_supports_mapping_and_xlsx(self):
        upload = self._build_minimal_xlsx()
        response = self.client.post(
            "/api/v1/leads/leads/import_preview/",
            {
                "file": upload,
                "mapping": json.dumps({"name": "fullname", "phone": "mobile", "email": "email_address", "city": "city"}),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["file_type"], "xlsx")
        self.assertEqual(response.data["total_rows"], 1)
        self.assertEqual(response.data["preview_rows"][0]["name"], "Sheet Lead")
        self.assertEqual(response.data["preview_rows"][0]["phone"], "9555512345")

    def test_scrape_endpoint_ingests_raw_html(self):
        html = """
        <html>
          <head><title>Directory Leads</title></head>
          <body>
            <h1>Directory Leads</h1>
            <div>Contact: 9666612345</div>
            <a href="mailto:directory@example.com">Email</a>
          </body>
        </html>
        """
        response = self.client.post(
            "/api/v1/leads/leads/scrape/",
            {"raw_html": html, "url": "https://example.com/directory", "max_items": 5, "auto_assign": True},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Lead.objects.filter(email="directory@example.com").exists())
        scraped = Lead.objects.get(email="directory@example.com")
        self.assertEqual(scraped.source, Lead.Source.WEBSITE)
        self.assertEqual(scraped.metadata.get("ingest_channel"), "web_scrape")

    def test_merge_endpoint_combines_duplicate_leads(self):
        primary = Lead.objects.create(
            company=self.company,
            name="Primary Lead",
            mobile="9777711111",
            city="Lucknow",
        )
        duplicate = Lead.objects.create(
            company=self.company,
            name="Duplicate Lead",
            mobile="9777711111",
            email="duplicate@example.com",
            city="Lucknow",
            is_duplicate=True,
            duplicate_reason="Matched by phone/email",
        )
        response = self.client.post(
            f"/api/v1/leads/leads/{primary.id}/merge/",
            {"duplicate_id": duplicate.id, "note": "Dashboard merge"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        primary.refresh_from_db()
        duplicate.refresh_from_db()
        self.assertEqual(duplicate.duplicate_of_id, primary.id)
        self.assertTrue(duplicate.is_duplicate)
        self.assertEqual(response.data["id"], primary.id)
