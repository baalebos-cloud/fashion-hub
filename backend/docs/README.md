# Fashion Hub Backend — Documentation Index

This folder documents the backend for the Fashion Hub marketplace: a
modular-monolith FastAPI application connecting customers, tailors/fashion
designers, material vendors, and delivery partners.

| Doc | Covers |
|---|---|
| [architecture.md](./architecture.md) | System architecture, module layout, request flow |
| [database.md](./database.md) | Schema, entity relationships, key constraints |
| [authentication.md](./authentication.md) | Signup/login, JWT, sessions, RBAC |
| [customers.md](./customers.md) | Customer profile, addresses, measurements |
| [professionals.md](./professionals.md) | Tailor/designer profiles, portfolios, verification |
| [vendors.md](./vendors.md) | Vendor profiles, products, inventory |
| [cart.md](./cart.md) | Multi-vendor cart |
| [checkout.md](./checkout.md) | Single-payment, multi-vendor checkout |
| [orders.md](./orders.md) | Order state machines, endpoint reference |
| [payments.md](./payments.md) | Payment provider abstraction, webhooks |
| [invoices.md](./invoices.md) | Invoice/receipt generation |
| [payment-consent.md](./payment-consent.md) | Digital consent records |
| [delivery.md](./delivery.md) | Delivery provider abstraction, lifecycle |
| [delivery-tracking.md](./delivery-tracking.md) | GPS tracking, staleness detection |
| [maps-and-gps.md](./maps-and-gps.md) | Geocoding, PostGIS, distance |
| [kyc-kyb.md](./kyc-kyb.md) | Identity/business verification |
| [measurements.md](./measurements.md) | Measurement profiles |
| [reviews.md](./reviews.md) | Review/rating rules |
| [notifications.md](./notifications.md) | Multi-channel notification dispatch |
| [messaging.md](./messaging.md) | Customer/professional conversations |
| [ai-assistant.md](./ai-assistant.md) | Navigation/support AI assistant |
| [security.md](./security.md) | Security controls, OWASP mitigations |
| [testing.md](./testing.md) | Test strategy, running the suite |
| [deployment.md](./deployment.md) | VPS deployment, see also `../deployment/README.md` |
| [troubleshooting.md](./troubleshooting.md) | Common issues |

Also see [environment-variables.md](./environment-variables.md) and
[api-reference.md](./api-reference.md).
