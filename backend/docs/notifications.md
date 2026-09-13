# Notifications

## Channels

`in_app` (always written), plus `email`/`sms`/`push` dispatched via
background tasks (`app/workers/email_tasks.py`,
`sms_tasks.py`, `push_tasks.py`) so a slow provider never blocks a request.

## Event catalog

`NotificationService.EVENT_TITLES` maps event types (e.g.
`order.accepted`, `payment.successful`, `delivery.exception`) to
human-readable titles. Extend this map as new event types are added rather
than hard-coding titles at each call site.

## Order status notifications

Every call to `OrderService.transition` enqueues
`notify_order_status_changed_task`, which notifies both parties on the
order (buyer and seller) with a status-specific message.

## Scheduled reminders

`send_scheduled_reminders_task` runs hourly (Celery beat) — intended for
things like "order accepted but not started in 48h" or "delivered but
unconfirmed for 24h" reminders. Define the specific rules in
`NotificationService.send_scheduled_reminders` as product requirements are
finalized.
