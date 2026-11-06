# Logistics modernisation: completion report

## 1. Baseline and final references

- **Baseline:** `main` at `4e6d378` (after #140) when work began on 2026-11-06.
- **Work:** seven stacked draft PRs, each built on the one before. Merge them in order.
- **Final working commit:** the head of `feat/logistics-ai-intelligence`.

## 2–3. Phases and pull requests

| # | Phase | PR | Off-by-default switch |
|---|---|---|---|
| 1 | Road routing and ETA engine | #141 | `ROUTING_PROVIDER=none` |
| 2 | Production-grade rider tracking | #142 | (always on: safer behaviour, no new risk) |
| 3 | Explainable rider scoring and dispatcher assignment | #143 | `DISPATCH_SMART_SCORING_ENABLED=false` |
| 4 | Multi-stop route planning | #144 | `DISPATCH_MULTISTOP_ENABLED=false` |
| 5 | Dispatcher control tower | #145 | (read-only) |
| 6 | Courier company adapters (sandbox) | #146 | `EXTERNAL_COURIERS` empty |
| 7 | Delivery intelligence (baselines) | #147 | `DELIVERY_ETA_CALIBRATION_ENABLED`, `DELIVERY_AI_SUMMARIES_ENABLED` false |

## 4–5. Features implemented and preserved

**Implemented:** see each phase's doc in `docs/logistics-*.md`.

**Preserved and still tested:**
- order flows, seller dispatch requests, the open job board and inDrive-style fare offers
- sequential auto-offers, the pickup code and handover codes, the delivery event log
- share links, proximity alerts, Nigerian address fields
- release, reassign and issue triage
- masked calls, payments, admin lockdown and the activity log

## 6. New API contracts (all additive)

| Area | Endpoints |
|---|---|
| Routing | `route` on job cards, the seller panel and the trip; journey `live.basis = road_route`; `GET /admin/routing/health` |
| Tracking | `POST /deliveries/{id}/position` takes `recorded_at` and `speed_mps`; `POST /deliveries/{id}/position/state`; freshness and `tracking` fields |
| Dispatch | `GET /admin/dispatch/requests/{id}/candidates`; `POST …/assign` |
| Multi-stop | `GET /deliveries/mine/route`; `GET /admin/dispatch/riders/{id}/route` |
| Control tower | `GET /admin/dispatch/control-tower`; `GET /admin/dispatch/riders/overview` |
| Couriers | `GET …/courier-quotes`; `POST …/courier-booking`, `…/courier-cancel`, `…/courier-simulate` (sandbox only); `POST /webhooks/couriers/{courier}` |
| Insights | `GET /admin/dispatch/insights` |

## 7. Database migrations (all additive, each reversible one step)

- **0027:** route columns on `delivery_requests`
- **0028:** `score` and `score_details` on `dispatch_job_offers`
- **0029:** `delivery_batches`
- **0030:** `courier_events`

## 8–13. Architecture summaries

- **Routing:** a provider interface (Google Routes and Matrix, OSRM route and table) with caching, a timeout, one retry and a
  Redis circuit breaker. If the provider fails, the app falls back to a straight-line estimate labelled as such. The route
  is stored once per request; live ETAs are recalculated at most once a minute per delivery.
- **Tracking:**
  - One atomic Redis script handles consent, replay and out-of-order rejection, a 3-second throttle and consent extension.
  - Locations are labelled live, delayed or last known. The rider's phone reports why there's no location.
  - Viewers get adaptive polling; tracking is cleared at handover.
  - Background tracking needs a native app (documented).
- **Dispatch:** eligibility rules first, then a deterministic 0–100 score from 5 weighted factors. A record of each
  decision is stored, and dispatchers get suggestions and can assign manually (audited, lock-ordered).
- **Multi-stop:** exact DP (optimal) for up to 12 stops, insertion beyond that. Pickup always comes first, capacity, time
  limits and windows are hard constraints, and infeasible routes are refused. OR-Tools is evaluated and deferred to
  fleet-wide planning.
- **Courier readiness:** a provider-neutral contract and a sandbox courier. Real couriers (Shipbubble, Sendbox, GIG) need API access.
- **AI readiness:** baselines and a backtested calibration are live. ML is deferred until the readiness thresholds are met;
  AI is used only for summary wording, and is off by default.

## 14. Security review (across phases)

- **Access:** every new admin endpoint is role-gated and covered by tests. Rider and customer data is limited to the parties on the order.
- **Location privacy:**
  - Route lines are shown only to the assigned rider.
  - Coordinates never appear in public views, the control tower, logs or AI prompts. A test checks they don't appear in logs.
- **Courier webhooks:** HMAC-verified before parsing, size-capped and rate-limited. Duplicates are stored once.
- **Integrity:** writes in dispatch and courier booking use the existing lock order (order → request → partner). Idempotency is used where retries happen.
- **Money:** no code path touches payments, refunds, settlements or payouts. Courier prices are recorded only.

## 15–16. Tests and CI

- **Local (latest branch):** backend 576 passed / 8 skipped, frontend 201 passed. Typecheck, eslint and ruff (CI rules) clean. Secret scan: only the pre-approved finding.
- **CI:** runs on each draft PR. One flaky admin-TOTP test (from #137) was fixed in #143.
- **Real browser:** the control tower was checked at desktop and phone widths through the real admin two-step login.

## 17. Implemented vs tested vs production-validated

| Capability | Implemented | Automated tests | Validated in production |
|---|---|---|---|
| Road routing (Google, OSRM) | Yes | Yes, with faked providers | **No**: needs Google billing or an OSRM server |
| Rider tracking hardening | Yes | Yes | **No**: needs real phones on real deliveries |
| Smart scoring and assignment | Yes | Yes | **No**: needs real riders and auto-offers switched on |
| Multi-stop planning | Yes | Yes (brute-force verified) | **No**: no real batches yet |
| Control tower | Yes | Yes, plus a local browser check | **No** |
| Courier adapters | Framework and sandbox | Yes (contract tests) | **No real courier connected** |
| Delivery intelligence | Baselines | Yes, on synthetic history | **No**: not enough real history |

## 18. Remaining blockers

1. **Google Cloud billing and the Routes API:** road routing, traffic ETAs and a fleet map.
2. **Courier API access:** Shipbubble recommended first.
3. **Africa's Talking Voice approval:** masked calls.
4. **Real delivery volume:** before turning on ML models or ETA calibration.

## 19. Production configuration (when each is approved)

- `ROUTING_PROVIDER=google` and `ROUTING_GOOGLE_API_KEY` (a server key)
- `DISPATCH_SMART_SCORING_ENABLED` and `DISPATCH_AUTO_OFFER_ENABLED`
- `DISPATCH_MULTISTOP_ENABLED`
- `EXTERNAL_COURIERS` plus that courier's credentials
- `DELIVERY_ETA_CALIBRATION_ENABLED`, once the Reports page shows it as usable
- Optionally `DELIVERY_AI_SUMMARIES_ENABLED`

A Celery beat service must run for auto-offers, courier reconciliation and log purging.

## 20. Rollback

- **Every feature:** switch its flag off. No deploy is needed.
- **Code:** revert the PRs in reverse order (#147 → #141). Each migration downgrades one step (0030 → 0026).

## Owner approval checklist

- [ ] Review and merge #141 → #147 in order, each with CI green
- [ ] Enable Google billing and the Routes API; set `ROUTING_PROVIDER=google`
- [ ] Decide on fares from road distance (`DISPATCH_PRICE_FROM_ROAD_ROUTES`)
- [ ] Decide on smart scoring and auto-offers; run Celery beat on Railway
- [ ] Decide on multi-stop routes
- [ ] Contact Shipbubble, Sendbox or GIG for API access
- [ ] Revisit ETA calibration and ML once Reports shows "ready"
