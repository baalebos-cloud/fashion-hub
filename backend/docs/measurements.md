# Measurements

`MeasurementProfile` — a named, reusable set of measurements per customer
(e.g. "My measurements", "Son's measurements"). `Measurement` rows hold
individual fields (`chest`, `waist`, `sleeve_length`, ...) with a unit
(default `cm`).

`MeasurementService.create_profile` creates both in one transaction.
`CreateCustomerOrderRequest.measurement_profile_id` lets a customer
reference an existing profile when placing an order, rather than
re-entering measurements every time.
