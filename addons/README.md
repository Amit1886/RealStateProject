# Addons (Optional Extension Platform)

This project includes an **optional** `/addons/*` platform that can be enabled without touching any existing templates.

## Safe enablement (recommended)

1) Enable URL routing for addons by adding the middleware (no root `urls.py` changes needed):

- Add `addons.middleware.AddonsURLRoutingMiddleware` to `MIDDLEWARE` (prefer near the end).

2) Enable the platform at runtime (recommended in production):

- Set `ADDONS_PLATFORM_ENABLED=true`

With only the middleware enabled, `/addons/health/` works and all other addon routes return a 404 unless their app is in `INSTALLED_APPS`.

## Enabling a specific addon

To expose an addon's endpoints, add its Django app to `INSTALLED_APPS`, for example:

- `addons.autopilot_engine`
- `addons.ai_call_assistant`
- `addons.marketing_autopilot`

Then run migrations for that addon app as part of your normal deployment workflow.

If you prefer not to edit `INSTALLED_APPS` manually, you can enable all addon apps via:

- `ADDONS_PLATFORM_ENABLED=true`

## E-commerce storefront (shadow mode)

The e-commerce engine ships with **API-only** storefront endpoints (separate frontend can consume these):

- Public list: `/addons/ecommerce/storefront/products/`
- Checkout: `/addons/ecommerce/storefront/checkout/`
- Order status: `/addons/ecommerce/storefront/orders/<order_number>/status/`
- Payment captured webhook: `/addons/ecommerce/webhooks/payment-captured/`

Public storefront endpoints require a shared key:

- Set `STOREFRONT_PUBLIC_API_KEY=<long-random-key>`
- Send header `X-Storefront-Key: <key>`

### Payment webhook verification (recommended)

The payment captured webhook can optionally verify gateway signatures:

- Enable: `STOREFRONT_PAYMENT_WEBHOOK_VERIFY=true`

Razorpay:
- Set `RAZORPAY_WEBHOOK_SECRET=<secret>`
- Send header `X-Razorpay-Signature: <hex-hmac>` (provider does this)

Stripe:
- Set `STRIPE_WEBHOOK_SECRET=<secret>`
- Stripe sends `Stripe-Signature` header (provider does this)
- Optional: `STRIPE_WEBHOOK_TOLERANCE_SECONDS=300`

## Courier Integration (optional)

Admin APIs:
- `/addons/courier/shipments/`
- `/addons/courier/shipments/create/`
- `/addons/courier/shipments/<id>/`

Courier webhook (optional):
- `/addons/courier/webhooks/status/`
- Protect with `COURIER_WEBHOOK_KEY=<key>` and send `X-Courier-Key: <key>`

Mock mode (default on):
- `COURIER_INTEGRATION_MOCK=true` generates AWB/tracking locally (no external API calls)

## Demo setup (seed one entry per provider)

To create demo provider entries (so you can see how the flow works in Admin / APIs):

- Dry-run: `python manage.py addons_seed_demo`
- Apply: `python manage.py addons_seed_demo --apply`

This creates demo configs for:
- Razorpay + Stripe (payment gateways)
- WhatsApp + IVR provider
- Shiprocket + Delhivery (courier)

## Autopilot Engine event processing toggle

Autopilot event persistence/dispatch is guarded to avoid breaking core workflows if tables are missing:

- Global: `ADDONS_PLATFORM_ENABLED=true`
- Autopilot-specific: `ADDON_AUTOPILOT_ENGINE_ENABLED=true` (optional)

If `ADDON_AUTOPILOT_ENGINE_ENABLED` is not set, Autopilot Engine also supports enabling via the DB toggle `FeatureToggle(key="autopilot_engine", enabled=True)` once migrations are applied.

### Recommended e-commerce → Autopilot wiring

Events emitted by e-commerce:
- `storefront_order_created`
- `storefront_order_paid`

Suggested workflow example:
- on `storefront_order_paid` → `ecommerce_sync_to_billing` (safe adapter; does not write legacy billing by default)
