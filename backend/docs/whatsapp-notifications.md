# WhatsApp Notifications (Vendor <-> Tailor/Designer)

Per the product requirement that WhatsApp is "the easiest way to notify"
vendors and tailors/designers of each other's order activity,
`vendor_order` status changes additionally dispatch a WhatsApp template
message to both parties, if they've set a `whatsapp_number` on their
profile (`PATCH /users/me`).

See `NotificationService.notify_order_status_changed` ->
`WHATSAPP_TEMPLATES` map -> `workers/whatsapp_tasks.py::send_whatsapp_task`
-> `integrations/notifications/whatsapp.py`.

**Customer-order notifications never go to WhatsApp** -- only
`order_type == "vendor_order"` events trigger it, so a customer who never
opted into WhatsApp contact isn't messaged there.

## Provider

Two supported: Meta's own WhatsApp Cloud API, or Twilio's WhatsApp API --
either requires pre-approved message templates for business-initiated
conversations (WhatsApp doesn't allow free-form text outside a 24h
customer-initiated window). See `.env.example` for the exact setup for
each.
