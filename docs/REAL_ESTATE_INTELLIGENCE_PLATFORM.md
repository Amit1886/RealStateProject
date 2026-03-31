# Real Estate Intelligence Platform

## Added Modules

- Property data aggregation with batch imports, normalization, enrichment, and duplicate detection.
- Demand heatmap analytics using leads, searches, property views, and deal closures.
- Price trend snapshots by city, district, and property type.
- AI voice lead qualification storage with transcripts, structured responses, and qualification status.
- Investor ecosystem with investor profiles, investor matches, and alert fanout.
- Builder marketplace enrichment with registration, city, launch metadata, pricing bands, and project progress.
- Property alert subscriptions for new listings, price drops, similar properties, and builder launches.
- Premium lead marketplace with wallet deduction and assignment automation.
- Secure real-estate document storage with scoped access.
- Fraud detection hooks for duplicate listings, fake-agent suspicion, and spam leads.

## Key API Areas

- `/api/v1/intelligence/import-batches/`
- `/api/v1/intelligence/aggregate/import/`
- `/api/v1/intelligence/heatmaps/`
- `/api/v1/intelligence/price-trends/`
- `/api/v1/intelligence/investors/`
- `/api/v1/intelligence/investor-matches/`
- `/api/v1/intelligence/alerts/`
- `/api/v1/intelligence/premium-leads/`
- `/api/v1/intelligence/documents/`
- `/api/v1/intelligence/dashboard/`
- `/api/v1/voice/calls/`
- `/api/v1/voice/qualify-lead/`

## Automation Jobs

- `intelligence.tasks.run_property_import_batch_task`
- `intelligence.tasks.refresh_demand_heatmap_task`
- `intelligence.tasks.refresh_price_trends_task`
- `intelligence.tasks.refresh_investor_matches_task`
- `intelligence.tasks.notify_pending_investor_matches_task`
- `intelligence.tasks.expire_premium_leads_task`
- `voice.tasks.schedule_inactive_lead_calls_task`
- `voice.tasks.qualify_voice_call`

## Model Extensions

- `leads.Property`: aggregated import metadata
- `leads.Builder`: registration + city + contact metadata
- `leads.PropertyProject`: price bands, city, launch state, ROI, completion tracking
- `voice.VoiceCall`: transcript, structured qualification, qualification status
- `voice.VoiceCallTurn`: turn-by-turn transcript log

## Notes

- Current voice automation is provider-ready and workflow-ready, but still relies on external telephony credentials/webhooks for live outbound calling.
- Aggregation imports currently support structured partner/public payload ingestion and task scheduling; live crawler/fetch adapters can be added next without changing the schema.
- Heatmap and trend analytics are snapshot-based, which keeps admin dashboards fast and scales well for multi-tenant usage.
