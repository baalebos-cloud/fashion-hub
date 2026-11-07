# Delivery intelligence (logistics phase 7)

**Principle:** baselines first, models only when the data justifies them, and AI only for wording.
Nothing in this phase changes a delivery, a payment or a rider assignment. Everything is advice,
and it all works with every AI service switched off.

## What's built (`app/services/delivery_intelligence_service.py`, Admin → Reports)

| Piece | How it works | Status |
|---|---|---|
| **Data readiness** | Counts finished deliveries and days of history against fixed thresholds (500 deliveries, 60 days) | Live |
| **ETA calibration** | Per vehicle, the median of *actual trip ÷ estimated trip* over the last 30 days (at least 20 trips) | Report live. Applying it to live ETAs needs `DELIVERY_ETA_CALIBRATION_ENABLED=true` |
| **Backtest** | Learns the factor on the older half of trips and measures the average error on the newer half, against the raw estimate | The factor is only "usable" when it's *measurably better* |
| **Rider performance** | Deliveries, median minutes to pickup, median trip time, on-time share (within 1.5× the estimate + 15 min), offer acceptance | Live |
| **Demand forecast** | 4-week average of jobs per hour of the week (seasonal naive), West Africa Time | Live |
| **Route efficiency** | Planned minutes saved by multi-stop routes; actual vs estimated trip time | Live |
| **Recommendations** | Fixed rules: keep baselines, rider supply for the coming peak, switch on calibration, rider check-ins | Live, advisory |
| **Summary** | Plain text from the numbers. With `DELIVERY_AI_SUMMARIES_ENABLED=true` and an AI provider set, the wording is rewritten by the existing Vertex/Groq client from the **same numbers only** (no names or personal data are sent). If the AI fails, the plain text is used | AI off by default |

Every recommendation carries **evidence**, a **recommendation**, a **confidence** level, its **reasoning**, the
**ruleset version** (`delivery-insights-v1`) and a **timestamp**, and is marked `advisory: true`. A person decides.

## What isn't built, and why

**Machine-learning models** for ETA prediction, delay or failure prediction, and demand forecasting aren't built.
Tailora doesn't have enough finished deliveries yet to train them and check them honestly. The readiness check
says when it does. At that point:
1. Train a model on the older history.
2. Compare it with these baselines on the newer history, using the same backtest approach.
3. Enable it behind a flag only if it's clearly better, with owner approval.

LLMs are never used to decide delivery state, ETAs or assignments.

## Guardrails

These are checked in code and tests:
- No automatic payments, reassignments or cancellations, and no edits to past delivery events.
- No invented ETAs: calibration applies only when it's switched on *and* validated for that vehicle.
- If the AI fails, insights still work.
- Admin-only endpoint: `GET /api/v1/admin/dispatch/insights`.

## Rollback

Both flags are off by default. There's no migration. Revert the PR to remove it.
