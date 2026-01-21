# SentinelOps – Working Notes

## Goal

AI-powered revenue & operations observability system.
This document captures architectural decisions and iteration milestones during development.

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
- Rules were validated using real Stripe test events via Stripe CLI

Status: v0.2 complete – rule engine validated with real Stripe events and idempotent time-window execution.

---

## v0.3 – Rule Engine Scheduling

SentinelOps rule engine is designed to run as a batch job, separate from webhook ingestion.

### Local Scheduling (Development)

In local development, the rule runner can be scheduled using OS-level schedulers.

Example (Windows Task Scheduler):

- Command:
  python -m sentinelops.scripts.run_rules
- Frequency:
  Every 5 minutes
- Working directory:
  Project root (SentinelOps)

This ensures anomaly detection runs automatically without blocking webhook requests.
The 5-minute execution interval balances timely detection of critical issues with operational noise and cost.

### Production Consideration

In production environments, the same rule runner can be scheduled using:

- AWS EventBridge Scheduler
- Cron-based ECS task
- Kubernetes CronJob

The rule engine is idempotent per time window, so duplicate executions do not create duplicate anomalies.

# status

SentinelOps v0.3 – Operational Alerts
Rule engine scheduled execution
Multi-window anomaly detection (30m / 5m)
Slack operational alerts via webhook
Idempotent anomaly + notification delivery

---

---

## v0.4 — Daily Ops Summary & AI Insight (Daily Batch)

### What

- Generate a once-a-day operational summary for the last 24 hours.
- Inputs are strictly aggregated metrics + rule engine signals (no raw Stripe events).
- Optional AI layer converts signals into human-friendly language.
- Deliver summary to Slack as a single compact message (Overall / Highlights / Watch).

### Why

- Real-time alerts (v0.3) are useful but create fragmentation; operators still need a daily “big picture.”
- Separate reporting from ingestion to preserve webhook performance and system stability.
- Control AI risk by limiting scope to interpretation/language only, not calculation or decision-making.
- Predictable cost by calling AI at most once per day with bounded input size.

### Design Notes (Boundaries)

- AI can:
  - Summarize aggregated signals and trends in natural language.
  - Provide context and prioritization wording.
- AI must not:
  - Perform calculations, determine thresholds, or trigger actions.
  - Produce authoritative operational directives.

### Stability & Cost

- AI is optional: if AI fails, numeric/rule-based report still ships (fail-safe).
- Daily schedule: one run per day (batch job).
- Payload size is bounded and deterministic (signals + metrics only).

### Outcome

- Daily operational visibility is improved with minimal overhead.
- Architecture remains consistent: ingestion → rules → (alerts + summary/reporting).
- v0.4 establishes “controlled AI usage” as a portfolio differentiator.

### AI Stability & Failure Handling

- AI insight generation is fully optional and non-blocking.
- AI failures (rate limit, billing/quota, misconfiguration) are classified and logged without breaking delivery.
- Daily summary is always delivered with deterministic, rule-based content even when AI is unavailable.
- AI usage is strictly bounded (once per day) with controlled input size and scope.
- `used_ai` and `ai_error` are persisted for operational visibility and auditability.

This completes v0.4 with a fail-safe, cost-aware AI integration suitable for production environments.

---

## Local Quickstart (Non-Docker)

### Prerequisites

- Python 3.x
- PostgreSQL (local)
- PowerShell on Windows

### Setup

1) Create venv & install deps
2) Create `.env` from `.env.example` and set DB + Slack values

### Initialize DB tables

python -m sentinelops.scripts.init_db

- Run API server
uvicorn sentinelops.main:app --reload --app-dir src

- Verify Health
iwr "http://127.0.0.1:8000/api/v1/health" -UseBasicParsing

- Demo: Anomaly lifecycle (open → acknowledged → resolved)
iwr "http://127.0.0.1:8000/api/v1/anomalies?only_open=true&sort=severity_desc&limit=5" -UseBasicParsing | ConvertFrom-Json

- pick an id from the output, e.g. 9

$body = '{"status":"acknowledged"}'
iwr -Method Patch "http://127.0.0.1:8000/api/v1/anomalies/9" -ContentType "application/json" -Body $body -UseBasicParsing | ConvertFrom-Json

$body = '{"status":"resolved"}'
iwr -Method Patch "http://127.0.0.1:8000/api/v1/anomalies/9" -ContentType "application/json" -Body $body -UseBasicParsing | ConvertFrom-Json

- Run daily summary (AI optional)
python -m sentinelops.scripts.run_daily_summary

### Demo Seed Data

For demos and local testing, SentinelOps provides a seed script that creates
deterministic open anomalies without relying on live Stripe data.

python -m sentinelops.scripts.seed_demo_anomalies

This ensures the anomaly lifecycle API (open → acknowledged → resolved)
can always be demonstrated reliably.

### Demo-only filtering

For clean demos, anomaly queries support a `demo_only=true` parameter
which filters seeded demo anomalies (identified by `[demo]` title prefix).

/api/v1/anomalies?only_open=true&demo_only=true

---

## v0.5 — Operations Dashboard & Anomaly Lifecycle

### What

Expose a minimal operations dashboard API for anomalies.
Support anomaly lifecycle transitions:
open → acknowledged → resolved
Provide filtered views for:
open-only anomalies
severity-based sorting
demo-only data (for clean demos)

### Why

Operators need a clear, queryable view of current issues.
Status transitions must be explicit, validated, and auditable.
A demo-friendly view is required to showcase the system without production noise.

### Design Notes

Lifecycle rules are centralized in anomaly_lifecycle service.
Invalid or no-op transitions are rejected with clear errors (409).
Demo data is tagged at the data level (evidence._demo = true), not inferred from presentation.
API remains thin; all domain logic lives in services.

### Outcome

Anomaly lifecycle is fully enforceable and observable via API.
Demo scenarios can be executed end-to-end:
  anomaly creation → ack → resolve
v0.5 completes the operational control loop:
  ingestion → rules → alerts → dashboard → human action.

Status: v0.5 complete – operational dashboard and lifecycle management in place.

---

## TODO / Optional Backlog (Post v1.0)

The following items are intentional backlog items.
They are not required for v1.0 delivery but represent future refinement
towards a more extensible rule engine.

- [ ] Rule runner commonization (shared execution flow for anomaly rules)
- [ ] Extract rule thresholds and windows into rule definitions (data-driven rules)
- [ ] Introduce generic rule execution interface (input → decision → anomaly)
- [ ] Reduce duplication across rule scripts (windowing, idempotency checks)
- [ ] Optional: persist rule metadata for dynamic tuning
- [ ] Optional: rule-level enable/disable flags for production control

---
