# Measurements

`MeasurementProfile` — a named, reusable set of measurements per customer
(e.g. "My measurements", "Son's measurements"). `Measurement` rows hold
individual fields (`chest`, `waist`, `sleeve_length`, ...) with a unit
(default `cm`).

`GET /api/v1/measurements` lists the authenticated customer's profiles and
fields. `POST /api/v1/measurements` creates a profile and its fields in one
transaction, lazily provisioning the account's customer profile under a row lock.
Field names must be unique, values positive (at most two decimal places), and
units explicitly `cm` or `in`. Empty profiles and unsupported units are rejected.
Profiles belonging to other users cannot be selected for checkout.
`CreateCustomerOrderRequest.measurement_profile_id` lets a customer
reference an existing profile when placing an order, rather than
re-entering measurements every time.

## Per-design measurement requirements

`Design.required_measurement_fields` (e.g. `["chest", "waist",
"sleeve_length"]`) lets a tailor/designer specify exactly which fields
they need for a given design -- set via `POST /designs` (see
`schemas/design.py`). Left null/empty, the customer's explicitly selected
measurement profile is used as-is: **"or client filled it themselves"**
is the default behavior, not an edge case -- a design only narrows the
requirement when the professional explicitly sets one.
