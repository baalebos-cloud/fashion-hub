# KYC / KYB Verification

## Statuses

`pending -> under_review -> verified | rejected` (+ `expired` where
applicable) — `app/core/constants.py::VerificationStatus`.

## Provider abstraction

```
KYCProvider (ABC)              app/integrations/kyc/base.py
└── ManualReviewKYCProvider     app/integrations/kyc/provider.py (default)
```

The default provider stores submitted documents and routes them to an
admin for manual review (`POST /api/v1/admin/...`) rather than calling a
third-party identity-verification API — this lets the platform launch
without an identity-verification vendor contract. Swap in a real provider
(Smile ID, Youverify, Persona, etc.) later by implementing `KYCProvider`.

## Individual vs. business

- `KYCVerification` — customers, professionals, delivery partners acting
  as natural persons (national ID, passport, driver's license).
- `KYBVerification` — vendors and professional businesses (registration
  number + supporting documents).

Both reference `VerificationDocument` rows, whose `storage_key` points to
a **privately** stored file — access is resolved via
`StorageProvider.get_signed_url`, gated by `KYCService.get_document_url`
to the document owner or an admin only. Documents are never served via a
public URL.

## Review flow

`KYCService.review` / `KYBService.review` — admin-only
(`reviewer.role == "admin"`), sets status to `verified`/`rejected` with an
optional rejection reason, and stamps `reviewed_by_user_id`/`reviewed_at`.

## Verified badge

`Professional.is_verified` / `Vendor.is_verified` should be recomputed
whenever the underlying KYC/KYB verification changes status — wire this
into `KYCService.review`/`KYBService.review` as the codebase matures.
