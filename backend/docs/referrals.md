# Referrals & Commission

## The rule, exactly as specified

Signing up with someone's referral code earns the referrer **nothing** by
itself. A `Referral` only becomes commission-worthy once the **referred**
person completes their **first successful paid order** --
`ReferralService.qualify_if_applicable`, called from
`payment_service.py` the moment a payment is confirmed. This is checked
against `Referral.status == "pending"`, so only the first order ever
qualifies a given referral; every order after that is a no-op here.

## Commission math

`REFERRAL_COMMISSION_SHARE` (default 20%) of the **platform's own 15%
commission** on that first order -- not 20% of the order total. A
₦10,000 order nets the platform ₦1,500; the referrer earns ₦300. This
keeps the program self-funded from the platform's take rate rather than
eating into what the referred seller nets.

## Flow

1. `GET /referrals/code` -- get-or-create a shareable code
   (`ReferralService.get_or_create_code`).
2. Someone signs up with `?ref=CODE` -> frontend passes `referral_code` on
   `POST /auth/signup` -> `ReferralService.record_signup` creates a
   `PENDING` `Referral` row. An invalid code fails silently (doesn't block
   signup) -- see `auth_service.py::sign_up`.
3. Referred person pays for their first order -> `qualify_if_applicable`
   flips the row to `QUALIFIED`, computes `commission_amount`, and
   notifies the referrer in-app.
4. An admin marks it `PAID` out-of-band (`POST /referrals/{id}/mark-paid`)
   once the payout is actually sent -- this scaffold doesn't automate the
   money movement itself, only the accounting.

`GET /referrals/me` returns a summary (`total_referred`,
`qualified_count`, `total_earned`, `total_paid`) plus the raw list.
