# Verification (KYC / KYB)

## What "verified" means

| Role | Needs | Optional |
| --- | --- | --- |
| Tailor / designer | Identity (NIN) verified | Business (CAC), shown as an extra trust signal |
| Delivery partner | Identity (NIN) verified | n/a |
| Vendor | Identity (NIN) **and** business (CAC) verified | n/a |

When an admin approves the last required check, the profile's `is_verified`
flag is set automatically. That flag drives the public verified badge, the
shop link going live, and riders being able to take jobs. Approval only ever
*grants* verification. Profiles verified earlier by an admin are never
silently un-verified, and admins still unverify explicitly if needed.

## Flow

1. The user opens **Verification** and sees a checklist with progress and the next step.
2. **Identity:** NIN plus an ID photo. Prembly checks the NIN (`NIN_PROVIDER=prembly`).
   If Prembly is unreachable, the submission is held as `under_review` for manual review.
3. **Business:** business type (RC, BN or IT), CAC number and certificate.
   With `KYB_PROVIDER=prembly` the CAC register is checked first:
   - Number not found: the user is told immediately to check the number and type.
   - Found: the registered company name is stored and compared with the shop name.
   - Registry unavailable: held as `under_review` for manual review.
4. Admins review under **Admin → KYC** and **Admin → KYB**, oldest first. Each card
   shows what the registry confirmed, whether the name matches, and the documents
   (opened privately with the admin's session). Rejecting needs a reason. Approving
   a name mismatch needs an override note. Every decision is audit-logged.
5. The applicant gets an in-app notification. On rejection, the reviewer's note
   appears on their checklist and they can resubmit. Duplicate submissions are
   blocked while one is in review or already verified.

The raw NIN is encrypted at rest (`IDENTITY_ENCRYPTION_KEY`) and never
returned by any API, including the admin queue.

## Settings

```
NIN_PROVIDER=prembly
NIN_API_KEY=<Prembly key>
KYB_PROVIDER=prembly            # or manual
PREMBLY_API_KEY=                # optional; defaults to NIN_API_KEY
PREMBLY_CAC_URL=https://api.prembly.com/api/v1/verification/api/cac_advance/
IDENTITY_ENCRYPTION_KEY=<Fernet key>
```

The default `PREMBLY_CAC_URL` is the CAC Advanced endpoint from Prembly's
current KYB guide; the CAC Advanced product must be enabled on your Prembly
account. Response codes: `00` found, `01` not found (the applicant is asked to
check the number), `02` or anything unexpected (held for manual review).
