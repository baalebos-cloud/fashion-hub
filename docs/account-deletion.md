# Deleting your account

Anyone can delete their own account from **Settings → Delete account**, on the website and in the
iPhone and Android apps. Both stores require this (App Store Review Guideline 5.1.1(v); Google Play's
account deletion policy).

## When it's refused

Nothing that involves money or another person may be left half-done. Deleting is refused, with a
plain-language reason, while the account has any of these:

| Blocker | Message |
|---|---|
| An order as buyer or seller that isn't finished (anything except completed, cancelled, rejected, refunded; a material cart that hasn't reached checkout doesn't count, but a checkout awaiting payment does, since its payment page can still be paid) | "You have 1 open order. Finish or cancel it first." |
| A delivery in progress (riders) | "You have a delivery in progress. Complete it first." |
| A payout not yet released (sellers) | "You have money waiting to be paid out to you. Wait until it has been paid." |
| A refund still being decided | "A refund on one of your orders is still being decided. Wait for the outcome." |
| Admin account | Admins can't delete themselves from the app; another admin removes the account. |

## What happens

The person confirms with their password. Then, in one transaction (`services/account_deletion_service.py`):

- **Signed out everywhere:** every session is revoked and push registrations are removed.
- **Details replaced:** name becomes "Deleted user", the email becomes `deleted-<id>@deleted.invalid`
  (so the address is free to sign up again), phone, WhatsApp, photo and referral code are cleared,
  and the password is replaced with a random one nobody knows. The account is switched off.
- **Erased:** saved addresses (and their map points unless a past delivery uses them), measurements,
  favourites, cart contents, assistant chats, notifications and recorded browsing activity.
- **Copies on past orders:** the delivery address saved on each of their orders is cut down to
  city, state and country (recipient name, phone, street and map point removed), and the
  measurements saved on the order are removed.
- **Profile photo:** an uploaded photo is deleted from storage, so its old link stops working.
- **Taken down:** a professional stops taking orders, their bio is cleared and designs are
  unpublished; a vendor's products are deactivated; a rider is marked unavailable; the storefront
  link is released.
- **Kept, without contact details:** orders, payments, invoices, receipts, payouts, refunds and
  identity checks (legal and tax records). Messages and reviews stay readable for the other person,
  under "Deleted user". Call records keep only times and durations; nothing was ever recorded.
- An `account.deleted` entry is written to the audit log.

## API

| Method | Path | |
|---|---|---|
| GET | `/api/v1/users/me/deletion` | `{ can_delete, blockers[] }` |
| DELETE | `/api/v1/users/me` | body `{ "password": "…" }` → 204; 403 wrong password (not 401, which would make the app refresh and retry); 409 with the blockers; rate-limited like sign-in |

No database changes.
