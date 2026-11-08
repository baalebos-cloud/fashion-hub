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

`NIN_PROVIDER` picks the lookup service:

| Value | Service | Settings |
|---|---|---|
| `manual` (default) | none: every submission is held for an admin | — |
| `dojah` | Dojah NIN Lookup (Basic) — `GET /api/v1/kyc/nin` | `NIN_API_KEY` (secret key), `DOJAH_APP_ID`, `DOJAH_BASE_URL` (`https://sandbox.dojah.io` for testing, `https://api.dojah.io` live) |
| `prembly` | Prembly NIN Basic | `NIN_API_KEY` |

A provider outage never verifies anyone: the submission is held for an admin.
A NIN the provider says doesn't exist is refused with a message to check it.

## Automatic approval (`NIN_AUTO_APPROVE`, off by default)

When on, an identity check is approved without an admin only if **every** rule passes
(`app/services/nin_matching.py`):

1. **NIN record found** by the provider.
2. **Name matches**: each word of the account name (at least two) matches a *different* word
   on the NIN record, any order, allowing a one-letter typo; extra official names are fine.
3. **Date of birth matches**: the date the person enters equals the NIN record exactly.
   The entered date is only compared, never stored.
4. **Profile photo** on the account.
5. **NIN not used elsewhere**: no other account has this NIN verified or waiting. NINs are
   compared by a keyed fingerprint (`nin_fingerprint`, HMAC from `IDENTITY_ENCRYPTION_KEY`),
   never in readable form. Migration 0035 fingerprints existing records; any it missed are
   fingerprinted on the next submission, and one that can't be read sends that submission to
   manual review. Submissions of the same NIN are handled one at a time (a per-NIN database
   lock), so two accounts racing with one NIN can't both be approved.

An automatic approval has the same effects as an admin's (profile badge, notification) and
writes an audit entry `kyc.auto_approved` with the rule results and no personal data.
If any rule fails, the check goes to the admin queue with the failed rules listed. Nothing
is ever rejected automatically.

Turn it on only after the provider is configured and tested against its sandbox.

HTTP client loggers (`httpx`, `httpcore`) are held at WARNING so lookup URLs, which can carry
the NIN, never reach the logs.
