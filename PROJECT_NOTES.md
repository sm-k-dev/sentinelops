# SentinelOps – Working Notes

## Goal

AI-powered revenue & operations observability system.

## Key Decisions

- Stripe scope: include subscriptions
- Anomaly severity: low / medium / high
- Amount-spike baseline: 30-day average

---

## v0.1 — Stripe Webhook Ingestion (MVP)

### What

- Receive Stripe webhooks and store raw events in PostgreSQL
- Verify Stripe signature
- Ensure idempotency using provider_event_id (UNIQUE)

### Why

- Webhooks can be retried; we must safely dedupe
- Store raw payload to enable future pipelines (rules/AI/alerts)

### Outcome

- Verified Stripe events persist reliably
- Invalid webhook attempts can be detected later (observability-ready)

---

## v0.2 — Rule-based Anomaly Engine

### What

- Add anomalies table (JSONB evidence)
- Implement rule runner script (`run_rules`)
- Rules:
  - `webhook_integrity` (invalid webhook detection)
  - `payment_failure_spike` (30-min failure spike detection)

### Why

- Separate ingestion from analysis to keep webhook fast & stable
- Prevent alert spam via time-window bucketing (30-min buckets)

### Outcome

- Anomalies are created with evidence for investigation
- Duplicate anomalies are prevented within the same time window

Status: v0.2 complete – rule engine validated with real Stripe events and idempotent time-window execution.
