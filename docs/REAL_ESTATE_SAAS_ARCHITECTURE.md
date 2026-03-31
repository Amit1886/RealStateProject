# Real Estate SaaS Architecture

## Module Map

- `accounts`: auth, OTP, tenant user roles
- `users`: current user/profile ledger APIs
- `customers`: buyer/seller profile + preferences
- `agents`: agent profile, coverage areas, verification, approvals
- `leads`: lead capture, routing, marketplace properties, followups
- `crm`: call logs, customer notes, CRM reminders
- `communication`: in-app, email, SMS, WhatsApp delivery logs
- `deals`: deal lifecycle + commission split inputs
- `wallet`: wallet balance, transactions, withdrawals
- `marketing`: campaigns, messages, campaign-lead mapping
- `reviews`: property reviews, agent ratings
- `notifications`: in-app notification center
- `saas_core`: tenant company isolation

## Production Schema Direction

- Tenant isolation lives at `saas_core.Company` and is attached to `accounts.User`.
- Agent routing uses indexed geography fields plus `AgentCoverageArea`.
- Property data remains backward compatible in `leads.Property` while normalized child tables now support:
  - `PropertyLocation`
  - `PropertyImage`
  - `PropertyVideo`
  - `PropertyFeature`
- Customer intent is captured separately in:
  - `customers.Customer`
  - `customers.CustomerPreference`
- Communication audit trail is stored in:
  - `crm.CallLog`
  - `communication.MessageLog`
  - `communication.EmailLog`
  - `communication.SMSLog`
- Campaign audience tracking is stored in `marketing.CampaignLead`.
- Deal records now store property linkage, stage, commission rate, share percentages, and closing date.

## Lead Assignment

1. Exact `pin_code`
2. Fallback `district`
3. Fallback `state`
4. Fallback `city`
5. Round robin inside matched agent pool
6. Assignment log + notification fanout

Implementation entry points:

- `leads.services.auto_assign_lead`
- `leads.services.assign_lead`
- `leads.tasks.auto_assign_lead_task`

## Automation

Celery tasks now cover:

- `leads.tasks.process_due_followups_task`
- `leads.tasks.refresh_open_lead_scores_task`
- `marketing.tasks.process_scheduled_campaigns`
- `communication.tasks.send_email_log_task`
- `communication.tasks.send_sms_log_task`
- `communication.tasks.send_whatsapp_message_task`
- `communication.tasks.dispatch_in_app_notification_task`

## API Surface

Core routes:

- `/api/auth/login/`
- `/api/auth/token/`
- `/api/v1/agents/register/`
- `/api/v1/leads/create/`
- `/api/v1/leads/properties/list/`
- `/api/v1/leads/properties/create/`
- `/api/v1/deals/create/`
- `/api/v1/wallet/balance/`
- `/api/v1/customers/customers/`
- `/api/v1/communication/events/`
- `/api/v1/reviews/property-reviews/`

## Scaling Notes

- PostgreSQL should be used in production via `DATABASE_URL`.
- Redis backs Celery and channel layers when configured.
- Media models are CDN-friendly because each file/URL is normalized and independently cacheable.
- Tenant-safe APIs should always scope by `request.user.company` unless admin access is intended.
