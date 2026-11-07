# Multi-stop routes (logistics phase 4)

## What it does

When `DISPATCH_MULTISTOP_ENABLED=true`, a dispatcher can give a rider a second (or third) job while
they're already delivering, **only if the rider's whole route still works**:

- **Capacity:** no more orders on board than the vehicle carries (`DISPATCH_VEHICLE_CAPACITY`: foot 1,
  bike 3, car 8, van 20). Each order counts as one unit.
- **Order of stops:** every pickup comes before its drop-off.
- **Time limit:** the whole route finishes within `DISPATCH_BATCH_MAX_MINUTES` (default 150).
- **Time windows:** respected when given. The planner supports them, but orders don't carry delivery windows yet.

If any of these fails, the assignment is refused with the reason, for example "more packages than the vehicle
can carry at once". Infeasible routes are never accepted.

The rider then sees **Your route** on their dashboard: the stops in order, each linking to that
order's own pickup or drop-off page. Dispatchers see the same list under **Rider's route** on each active
run. The plan is recomputed after every assignment, pickup, drop-off, release or reassignment. Once the
rider has fewer than two deliveries, the batch closes.

## Orders stay separate

A batch only **orders the stops**. Each order keeps its own:
- delivery record and status
- pickup code, handover code and package count
- event log, permissions and fee

Vendor → tailor and tailor → customer legs are still separate deliveries. Batching never merges them or
touches payments.

## The planner (`app/services/route_optimizer.py`)

| Batch size | Method | Guarantee |
|---|---|---|
| Up to 12 remaining stops (6 orders) | Exact dynamic programming over (stops visited, last stop) | **Optimal** for the travel-time table, deterministic; about 7 ms for 12 stops on a laptop |
| More than 12 stops | Cheapest feasible insertion, capped at 0.5 s | Valid, not guaranteed optimal |

Travel times come from `route_service.travel_matrix`:
- Google Route Matrix (with traffic when there are 10 points or fewer)
- the OSRM table
- or the labelled straight-line estimate

Routes planned on estimates say so ("Times are estimates").

### Evaluating OR-Tools

Google OR-Tools solves fleet-wide problems: many riders at once, capacitated VRP, pickup-and-delivery,
time windows. **It isn't used here yet:**
1. A rider's batch is small (a motorbike carries 2–3 orders, so 4–6 stops), where an exact answer takes milliseconds.
2. OR-Tools is a large compiled dependency (about 25 MB of wheels) for the Railway image.
3. The current flow assigns jobs one dispatcher decision at a time, not as a fleet-wide batch.

**When to add it:** automatic batching across all riders, for example every 5 minutes assigning all waiting jobs
to all riders together. `route_optimizer.plan_route` is the interface; an OR-Tools solver would sit beside
`exact_dp` and `insertion`.

### Measured results

- **Correctness:** on 12 random 3-order problems, the planner's time equals a brute-force search of every ordering,
  with the pickup-first rule and capacity checked on each.
- **Synthetic example:** for 6 orders with a random travel-time table, 138 min versus 270 min one order at a time.
  That's synthetic data only, **not** a real-world saving.
- **Real-world savings:** not measured; that needs live deliveries.
- **Ongoing comparison:** each batch stores `total_minutes` and `baseline_minutes` (one order at a time), so savings
  can be tracked once it runs.

## API

- `GET /api/v1/deliveries/mine/route`: the rider's route, or null.
- `GET /api/v1/admin/dispatch/riders/{partner_id}/route`: a dispatcher's read-only view of a rider's route.
- `POST /api/v1/admin/dispatch/requests/{id}/assign` (phase 3): with multi-stop on, it accepts a busy rider when the
  route fits.

## Not included yet

- **Rider self-batching:** riders can't claim a second job from the job board. Only dispatchers add stops, which
  is the controlled rollout.
- **Automatic fleet-wide batching:** see OR-Tools above.
- **Real package size and weight:** capacity is counted in orders.

## Rollback

- **Instant:** set `DISPATCH_MULTISTOP_ENABLED=false`. Replanning stops, and busy riders can't be given more jobs.
  Current deliveries continue as normal.
- **Full:** revert the PR and run `alembic downgrade 0028` (drops the `delivery_batches` table).
