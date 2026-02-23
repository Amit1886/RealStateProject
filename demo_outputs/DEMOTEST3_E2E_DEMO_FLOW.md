# Demotest3 End-to-End Demo Flow

## 1. Demo Credentials
- Demo User: `Demotest3` (`demotest3@gmail.com`)
- Demo Password: `Demo@123`
- Admin User: `admin@jaistech.demo`
- Active Plan: `Premium Plan`

## 2. Demo Dataset
### Business Profile
- Business Name: Demotest3 Retail Private Limited
- Address: Shop 14, Civil Lines, Lucknow, Uttar Pradesh
- GST: 09ABCDE1234F1Z5
- UPI: demotest3@upi
- Theme Primary: #2b5cff
- POS Print Mode: Thermal-80mm
- Custom Domain (White-label): demotest3.jaistech.demo

### Parties (3 Customers + 2 Suppliers)
| # | Name | Type | Mobile | UPI | Credit Grade |
|---|---|---|---|---|---|
| 1 | Anita Retail | customer | 9123456710 | anita.retail@upi | A+ |
| 2 | Bharat Traders | customer | 9123456711 | bharat.traders@upi | A+ |
| 3 | City Mart | customer | 9123456712 | citymart@upi | A+ |
| 4 | Fresh Farm Supply | supplier | 9123456713 | freshfarm@upi | A+ |
| 5 | Metro Wholesale | supplier | 9123456714 | metro.wholesale@upi | A+ |

### Transactions (10 Mixed Credit/Debit)
| # | Date | Party | Type | Mode | Amount | Notes |
|---|---|---|---|---|---|---|
| 1 | 2026-01-19 | Anita Retail | credit | upi | INR 7200.00 | Invoice INV-A-0001 settled |
| 2 | 2026-01-21 | Anita Retail | debit | cash | INR 9800.00 | Sales bill SB-3111 |
| 3 | 2026-01-28 | Bharat Traders | debit | cash | INR 12800.00 | Bulk sale with 5% discount |
| 4 | 2026-02-01 | Bharat Traders | credit | bank | INR 5000.00 | Partial payment by NEFT |
| 5 | 2026-02-04 | City Mart | debit | upi | INR 8450.00 | POS order settlement |
| 6 | 2026-02-06 | City Mart | credit | cash | INR 2400.00 | Return adjustment |
| 7 | 2026-02-09 | Fresh Farm Supply | debit | bank | INR 21000.00 | Purchase invoice PI-8801 |
| 8 | 2026-02-12 | Fresh Farm Supply | credit | upi | INR 11000.00 | Supplier payment UPI |
| 9 | 2026-02-14 | Metro Wholesale | debit | cheque | INR 15600.00 | Stock replenishment |
| 10 | 2026-02-17 | Metro Wholesale | credit | online | INR 7600.00 | Advance settlement |

### Payment Links
- UPI Link: `upi://pay?pa=anita.retail@upi&pn=Anita%20Retail&am=10044.16&cu=INR&tn=Invoice%20INV-20260219-706491`
- QR Link: `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=upi%3A%2F%2Fpay%3Fpa%3Danita.retail%40upi%26pn%3DAnita%2520Retail%26am%3D10044.16%26cu%3DINR%26tn%3DInvoice%2520INV-20260219-706491`
- Bank Link: `https://payments.jaistech.demo/bank-transfer?bank=State+Bank+of+India&acc=123456789012&ifsc=SBIN0001234`

### Templates Assigned
- POS Invoice Template (invoice / pos / pos_80)
- A4 Invoice Template (invoice / desktop / a4)
- Mobile Receipt Template (receipt / mobile / mobile)
- Transport Bill Template (transport_receipt / tablet / tablet)

## 3. Demo Storyline (Step-by-Step)
1. Admin opens `/superadmin/`, creates/updates Free, Basic, Premium plans and feature matrix.
2. User logs in as `Demotest3` and opens dashboard `/accounts/dashboard/`.
3. User configures branding in settings center `/settings/center/`.
4. User enables WhatsApp/SMS/Email configs in settings center.
5. User creates/opens party list at `/app/party/list/` with 5 demo parties.
6. User enters transactions at `/app/transaction/add/` and views list at `/app/transactions/`.
7. Auto message logs are visible in `OfflineMessage` + `ReminderLog`.
8. User creates sales order at `/commerce/add-order/`.
9. User generates invoice/payment at `/commerce/add-invoice/` and `/commerce/add-payment/`.
10. User views print templates via `/api/printers/user-templates/`.
11. User tests POS print flow and A4 flow using render endpoint `/api/printers/engine/render/`.
12. User checks AI scores via `/api/ai/credit-risk/`, `/api/ai/forecast/`, `/api/ai/salesman-score/`.
13. User downloads credit report PDF from generated files.
14. User verifies due reminders and notifications.
15. User upgrades plan flow is visible from billing history + subscription events.
16. Admin verifies activity from admin list and logs.
17. User exports/uses JSON demo dataset `demotest3_demo_dataset.json`.
18. User validates settings pages and module toggles.
19. User verifies totals and formulas below.
20. Final PASS/FAIL checklist confirms full system demo readiness.

## 4. Mocked Screenshot Script
1. Login page showing Demotest3 credentials entered.
2. Dashboard cards: total parties, total debit, total credit, net position.
3. Party list showing 5 parties and credit grades.
4. Add transaction form with receipt upload.
5. Order entry screen with item rows and shortcuts.
6. Invoice preview with QR + barcode.
7. Payment link popup showing UPI/QR/Bank options.
8. POS print preview (80mm thermal).
9. A4 print preview (desktop invoice).
10. AI panel showing risk score + forecast rows.
11. Billing history page with upgrade timeline (Free -> Basic -> Premium).
12. Admin module checklist with PASS status.

## 5. Calculation Formulas Used
- Party Balance = `Total Credit - Total Debit`
- Net Ledger Position = `Sum(Debit) - Sum(Credit)`
- Order Total = `Subtotal - Discount + Tax`
- Margin = `Total Amount - Cost Amount`
- Credit Grade:
  - `ratio = (debit / credit) * 100`
  - `A+ >= 90`, `A >= 70`, `B >= 50`, `C >= 30`, else `D`
- Risk Score = weighted penalties from unpaid coverage + overdue + failed payments + collection delay
- Salesman Score = `sales component + quality component + collection component`

## 6. Expected Module Output
- Billing: invoice number, payment reference, active subscription.
- Party/Transaction: updated balances, receipt tag, reminder logs.
- Commerce: order items, invoice, sales voucher, supplier due tracking.
- POS/Print: render logs for POS, A4, mobile, tablet.
- AI: forecast rows + customer risk + salesman performance.
- Notifications: WhatsApp/SMS/Email reminder logs.
- Settings: operating mode, print mode, branding and communication config.

## 7. What Client Will See
- Single unified platform with accounting + commerce + POS + AI.
- One user (`Demotest3`) running realistic daily workflow.
- Admin control over plans, features, mode, and monitoring.
- Ready-to-show demo assets: data JSON + markdown playbook + credit report PDFs.

## 8. Totals Verification
- Total Parties: **5**
- Total Transactions: **10**
- Total Credit: **INR 33200.00**
- Total Debit: **INR 67650.00**
- Net Balance: **INR 34450.00**

## 9. PASS/FAIL Checklist
| Module | Status |
|---|---|
| User Signup/Login (Demotest3) | PASS |
| Role-based access users | PASS |
| Branding setup | PASS |
| Admin panel demo data | PASS |
| Plan management (Free/Basic/Premium) | PASS |
| Feature toggles | PASS |
| Party creation (5) | PASS |
| Transactions (>=10) | PASS |
| Payment links (UPI/QR/Bank) | PASS |
| Invoice/Receipt/Bill generation | PASS |
| Template selection (POS/A4/Mobile/Tablet) | PASS |
| Credit score calculation | PASS |
| Monthly reporting data | PASS |
| Due reminder automation logs | PASS |
| User dashboard data | PASS |
| Multi-device print preview logs | PASS |
| White-label domain | PASS |
| Backup file presence | PASS |
| API demo data ready | PASS |
| Notification system logs | PASS |
| Stock/items available | PASS |
| Settings center values | PASS |
| CRUD validation | PASS |

## 10. Generated Files
- `demo_outputs\demotest3_demo_dataset.json`
- `demo_outputs\DEMOTEST3_E2E_DEMO_FLOW.md`
- `demo_outputs\credit_report_all_demotest3.pdf`
- `demo_outputs\credit_report_anita_retail.pdf`
