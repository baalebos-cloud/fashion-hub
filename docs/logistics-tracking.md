# Live rider tracking (logistics phase 2)

## How it works

1. **Starting:** after pickup, the assigned rider taps **Start sharing my location**. The server issues a random
   consent token, held only in the page's memory.
2. **Sending:** the phone sends its GPS fix with **the time the fix was taken**. One Redis script atomically:
   - checks the consent token
   - rejects a fix that isn't newer than the last accepted one (stops replays and out-of-order points)
   - ignores fixes less than 3 seconds apart
   - stores the point, and keeps consent alive while the rider keeps sending

   Fixes older than 2 minutes, or more than 30 seconds in the future, are refused.
3. **Freshness** comes from the age of the fix:

   | State | Fix age | Shown as |
   |---|---|---|
   | `live` | ≤ 30 s | "Live · updated 8s ago"; used for the live ETA |
   | `delayed` | ≤ 90 s | "Delayed · updated 1 min ago"; still used for the ETA |
   | `last_known` | ≤ 10 min | "Last seen 5 min ago. This isn't the rider's current position" (map dimmed, **no ETA**) |
   | gone | > 10 min | Nothing |

4. **The phone reports why there's no location:** `permission_denied`, `unavailable` (no GPS fix) or `paused` (page in the
   background). Customers and the dispatcher see that instead of a silent gap. A new fix clears it.
5. **Tracking ends** when the rider taps stop, and automatically at **handover**, release, reassignment or cancellation.

## Who sees what

| Viewer | Sees |
|---|---|
| Buyer, seller, assigned rider, admin | Coordinates with freshness (`GET /deliveries/{id}/position`) |
| Everyone else | 404 |
| Order journey / admin dispatch board | Freshness **state only**, no coordinates |
| Public tracking link | ETA and its basis only. **Never coordinates** |

Positions live only in Redis with a TTL of 10 minutes at most. They're never written to the database
and never logged. A test checks that coordinates don't appear in log output.

## Delivery to viewers: adaptive polling

The customer page polls **every 10 s while the rider is live**, otherwise every 20 s. The live ETA
behind it is recomputed at most once a minute per delivery (phase 1). We chose polling over
WebSockets or SSE because:
- the app runs as several gunicorn workers on Railway, and push connections would need sticky sessions or a
  Redis pub/sub fan-out
- at current volumes, polling Redis reads is cheap and degrades gracefully
- a phone that changes networks needs no reconnection protocol: the next poll just works

**When to revisit:** if concurrent tracked deliveries reach the hundreds, add an SSE endpoint fed by Redis
pub/sub. The freshness model and authorization stay the same.

## The rider's phone

- **Adaptive timing:** sends every **10 s** while moving (speed ≥ 2 m/s) and every **30 s** when stopped.
- **Connection drops:** keeps only the newest point and retries after 5, 10, 20 … seconds, up to 60 s. It sends straight away
  when the browser comes back online or the page becomes visible again.
- **Expired session:** if sharing lapsed, it starts a new session once and resends.
- **Screen awake:** asks the browser to keep the screen on while sharing (Wake Lock API, where supported).

### Browser limits

**A web page cannot track reliably in the background.** iOS Safari and Android Chrome pause or slow
location for pages that are hidden or have the screen off. That's why the page asks the rider to keep it
open, and why a `paused` state exists. **Dependable background tracking needs a native app**:
- Android: a foreground service with `ACCESS_BACKGROUND_LOCATION` and an ongoing notification.
- iOS: "Always" location permission with background location updates.

Both can post to the **same** `POST /deliveries/{id}/position` contract with `recorded_at`, so the server
needs no changes. A React Native or Expo rider app is the recommended upgrade path.

## Rollback

There's no migration. Revert the PR; older app versions that send no `recorded_at` are still accepted,
with the server's clock standing in. Redis keys expire on their own.

## Tests

- **Backend** (`tests/api/test_realtime_tracking.py`):
  - replayed, out-of-order, too-frequent, too-old and future fixes
  - freshness boundaries
  - consent extended while sending
  - permission-denied state visible to the customer and admin without coordinates
  - non-parties get 404, and no coordinates appear in logs
  - tracking cleared at handover
  - the existing GPS, journey and proximity tests updated to send real fix times
- **Frontend** (`tests/components/RealtimeTracking.test.tsx`):
  - sends the fix time and speed
  - survives a dropped connection and retries
  - restarts an expired session
  - reports permission denied
  - freshness wording never calls an old point current
