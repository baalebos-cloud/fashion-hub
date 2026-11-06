# Admin access and security monitoring

## Who can be admin

Only emails listed in `ADMIN_EMAILS` can hold an admin session. In staging and production an
empty list means nobody can use the admin area, so a missing setting fails closed.

Admins sign in at **`/admin/login`** in two steps:

1. Email and password.
2. A six-digit code from an authenticator app (Google Authenticator, Microsoft Authenticator,
   Authy, 1Password). The first sign-in shows a QR code to set the app up.

The normal `/login` page refuses admin accounts. Admin tokens carry an `mfa` claim and are
rejected without it. Removing an email from `ADMIN_EMAILS` locks that account out at once,
including sessions that are already open.

The authenticator secret is encrypted with `IDENTITY_ENCRYPTION_KEY` and stored in
`admin_credentials`. Each code works once.

## Setting up on Railway

1. Set these variables on the API service:
   - `ADMIN_EMAILS=jayeolaoluwadamilare@gmail.com`
   - `TRUST_PROXY_HEADERS=true`
   - `IDENTITY_ENCRYPTION_KEY` (already required for KYC)
2. Deploy. Migration `0026` creates `activity_logs` and `admin_credentials`.
3. Create the admin account from a Railway shell. The script asks for the password, so it
   never lands in logs:
   ```bash
   python scripts/create_admin.py --email jayeolaoluwadamilare@gmail.com
   ```
   If that email already has an account (for example as a customer), make it the admin instead:
   ```bash
   python scripts/create_admin.py --email jayeolaoluwadamilare@gmail.com --promote
   ```
4. Open `/admin/login`, sign in, and scan the QR code with your authenticator app.

**Lost phone:** run `python scripts/create_admin.py --email ... --reset-2fa` from a Railway
shell. This signs out every admin session; the next sign-in shows a new QR code.

## What is recorded

`activity_logs` records:

- every sign-in, failed sign-in (with the email that was tried), sign-up, sign-out and password reset
- every change made through the API (POST, PUT, PATCH, DELETE) and its outcome

Each entry stores the time, account, role, endpoint, IP address, browser/device description,
and a per-browser device ID (`X-Device-Id`). Request bodies, passwords, codes and tokens are
never stored. High-frequency rider GPS updates and provider webhooks are skipped.

Browsers never reveal a device's MAC address to websites, so it can't be collected. The
device ID is the practical substitute: it stays the same for one browser on one device
until its site data is cleared.

Entries are deleted after `ACTIVITY_LOG_RETENTION_DAYS` (default 180) by a daily Celery beat
job. The privacy policy discloses this logging (Nigeria Data Protection Act 2023, legitimate
interest in security and fraud prevention).

## Where the admin sees it

- **Security** (`/app/admin/security`):
  - counts for the last 24 hours
  - the IPs with the most failed sign-ins
  - a filterable activity table (email, IP, event)
  - each person's full list of IPs and devices with first and last seen
- **Audit Logs** (`/app/admin/audit-logs`): admin actions such as KYC/KYB approvals and dispatch changes.
- **KYC / KYB**: approve or reject tailors, designers, riders (KYC) and vendors/businesses (KYB).
