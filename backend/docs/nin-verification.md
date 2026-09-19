# NIN Identity Verification

NIN (Nigeria's National Identity Number) is **compulsory** for every
professional, vendor business-owner, and delivery partner -- there is no
way to complete KYC without it (see `KYCService.submit`, which requires
`nin_number` as a required field, not optional).

## What gets captured, and where it comes from

| Field | Source |
|---|---|
| NIN number | Typed by the person |
| Full name | **From the NIN lookup**, not the signup form |
| Date of birth | **From the NIN lookup** |
| Gender | **From the NIN lookup** |
| Home address | Picked on a map, geocoded, stored as a `Location` linked via `User.home_location_id` |
| Business location | Separate map pick -- `PATCH /professionals/me/location` -- linked via `Professional.location_id` |
| Email, phone | Already collected at signup (`User.email`, `User.phone_number`) |
| WhatsApp number | `PATCH /users/me` with `whatsapp_number` -- **never** returned in any other user's view of this profile |

## The actual verification mechanism

`KYCService.submit` calls `NINVerificationProvider.verify(nin_number)`
(`app/integrations/kyc/nin_provider.py`), which returns the government
record's own name/DOB/gender. That record is compared against the
account's self-reported `full_name` via a string-similarity check
(`SequenceMatcher`, threshold 0.7) and stored as `KYCVerification.identity_match`.

This is what "verify their identity for client safety" means concretely:
a customer ordering from a tailor can trust that an admin reviewed a
government-backed confirmation of who that tailor actually is, not just a
self-reported name and an uploaded photo of *something*.

A name mismatch does **not** auto-reject the submission -- it flags it
for closer admin review (`KYCService.review` requires an explicit
`rejection_reason` note before an admin can approve a flagged mismatch,
so overrides are always on record, never silent).

## Provider

`NIN_PROVIDER=manual` (the default) blocks all submission with a clear
"not configured" error -- there is no unverified fallback path. Configure
a real provider (Prembly is implemented as a reference; Youverify/QoreID/
VerifyMe/Smile ID all fit the same interface) before accepting real KYC
submissions.
