# Measurements

`MeasurementProfile` — a named, reusable set of measurements per customer
(e.g. "My measurements", "Son's measurements"). `Measurement` rows hold
individual fields (`chest`, `waist`, `sleeve_length`, ...) with a unit
(default `cm`).

`MeasurementService.create_profile` creates both in one transaction.
`CreateCustomerOrderRequest.measurement_profile_id` lets a customer
reference an existing profile when placing an order, rather than
re-entering measurements every time.

## Per-design measurement requirements

`Design.required_measurement_fields` (e.g. `["chest", "waist",
"sleeve_length"]`) lets a tailor/designer specify exactly which fields
they need for a given design -- set via `POST /designs` (see
`schemas/design.py`). Left null/empty, the customer's own default
measurement profile is used as-is: **"or client filled it themselves"**
is the default behavior, not an edge case -- a design only narrows the
requirement when the professional explicitly sets one.
