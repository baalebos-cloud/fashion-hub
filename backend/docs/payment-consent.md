# Payment / Order Consent

`PaymentConsent` records a digital consent entry at checkout: user, order,
amount, consent text version, timestamp, and (where legally appropriate)
IP/user-agent metadata.

**Important**: this is an operational audit record, not a verified legal
e-signature. `app/models/payment_consent.py` and this document intentionally
avoid claiming legal-signature status — verify applicable legal
requirements (e.g. e-signature law in your operating jurisdiction) before
representing this record as legally binding in your terms of service.

## Usage

Record consent immediately before initializing payment
(`POST /api/v1/payment-consent`, scaffolded in `app/api/v1/payment_consent.py`)
so the recorded amount matches exactly what the user is about to be charged.
