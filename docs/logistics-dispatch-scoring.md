# Rider scoring and dispatcher assignment (logistics phase 3)

## Rules every rider must pass first (unchanged)

Verified, online, has a vehicle, active account, no active delivery, not already offered this
job, not holding another reserved job, and within `DISPATCH_AUTO_OFFER_RADIUS_KM` of the pickup when
their location is known. A rider who fails any of these is never offered or suggested.

## The score (`app/services/dispatch_scoring.py`, version `dispatch-score-v1`)

| Factor | Weight | 0 → 1 |
|---|---|---|
| Pickup | 40% | ETA to the pickup: 0 min → 1, 45+ min → 0. A **road** ETA for the 5 nearest riders (`DISPATCH_SCORING_ROUTE_TOP_N`) when a routing provider is on, otherwise the labelled straight-line estimate. Unknown location → 0.2 |
| Reliability | 20% | Share of automatic offers accepted in the last 30 days, smoothed as (accepted + 2) / (answered + 3), so a new rider starts at about 0.67 |
| Rating | 15% | Average rating / 5; unrated riders get 0.7 |
| Experience | 10% | Completed deliveries, capped at 50 |
| Fairness | 15% | 1 / (1 + jobs assigned today), spreading work across riders |

The score is 0–100. Ties break on rider id, so the same inputs always give the same order. No AI or
randomness is involved, and dispatch works the same whether or not any AI service is up.

Each automatic offer stores the score and the record behind it (`dispatch_job_offers.score`,
`score_details`, migration 0028): inputs, per-factor scores, weights, a one-line explanation and
the version. You can always answer "why did Sola get this job?"

## Rollout

- `DISPATCH_SMART_SCORING_ENABLED=false` (default): automatic offers keep the original order (nearest by
  straight line, then rating, then experience).
- `true`: automatic offers use the score. Automatic offers themselves are still behind
  `DISPATCH_AUTO_OFFER_ENABLED` (off by default).

## Dispatcher tools (Admin → Deliveries → a job waiting for a rider)

- **Suggested riders** (`GET /admin/dispatch/requests/{id}/candidates`): the top riders with score and
  reasons, for example "pickup in about 6 min (road route); accepts 90% of offers; rated 4.6; 120
  deliveries done, 2 today". This is always available, whatever the flag says. It's advice only.
- **Assign** (`POST /admin/dispatch/requests/{id}/assign`): give the job to a chosen rider. It needs
  a reason, which goes in the audit log as `dispatch.assigned_by_dispatcher`. It locks order → request →
  rider (the same order as rider claims and accepted fare offers), refuses a job that already has a
  rider and refuses a busy rider. It also withdraws any automatic offer for that job.

The open job board, inDrive-style fare offers, reassignment and release all work exactly as before.

## Not included (documented for later)

- Package size and weight, rider capacity, and delivery deadlines aren't recorded on orders yet, so they
  can't be scored. Adding them is a schema and product change.
- Live traffic in the pickup ETA comes from the routing provider (phase 1, Google), only when it's switched on.

## Rollback

Set `DISPATCH_SMART_SCORING_ENABLED=false`. The code can be reverted; migration 0028 only adds two
nullable columns (`alembic downgrade 0027`).
