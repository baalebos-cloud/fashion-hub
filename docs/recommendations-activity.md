# Recommendations, part 1: shopping activity

Tailora's recommendations were fixed rules (cheapest in budget, highest-rated tailor). Learning
from behaviour needs a record of behaviour first; this is that record.

## What is recorded (`interaction_events`)

| Event | Who reports it | Notes |
|---|---|---|
| `view` (product, design, tailor profile) | Website | Same item, same person: once per 30 minutes |
| `search` | Website | Lower-cased, max 100 chars; sent once typing settles |
| `booking_started` | Website | Opening the booking form for a tailor |
| `add_to_cart`, `favorite`, `purchase` | Server only (daily history sync) | The browser cannot report these, so they can't be faked |

Each row: account **or** a random browser ID, event, item, page (`source`), time. Never an IP
address, location, device fingerprint or message content. The `/api/v1/interactions/events`
endpoint is excluded from the admin activity log so no IP is stored next to shopping activity.

## Privacy controls

- **Account switch** in Settings → Recommendations (`GET/PUT /api/v1/interactions/preference`).
  Turning it off deletes the account's recorded activity immediately and stops recording.
- **Browser choice** on the Privacy page; Global Privacy Control and Do Not Track are honoured.
- **Retention:** `INTERACTION_RETENTION_DAYS` (180), purged daily.
- **Shared devices:** sign-out drops queued events and starts a new browser ID.
- The shopping browser ID is separate from the security device ID, so the two can't be joined.

## Jobs (Celery beat)

- `sync-shopping-history` (daily): copies favourites, cart adds and purchases from the last 180
  days, for accounts that allow personalisation. Idempotent via `dedupe_key`; its first run is the
  backfill, so PR 2 (similar items) has data immediately.
- `purge-old-shopping-activity` (daily).

## Settings

`INTERACTION_RETENTION_DAYS=180`, `RATE_LIMIT_INTERACTIONS=60/minute`. Migration `0031`.
