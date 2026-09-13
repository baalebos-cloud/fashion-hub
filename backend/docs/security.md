# Security

## Authentication & session security

- Passwords hashed with bcrypt (`passlib`); never stored or logged in
  plaintext.
- JWT access tokens are short-lived (30 min default); refresh tokens are
  long-lived but their **hash** (SHA-256) is what's stored in `sessions`,
  so a database leak doesn't expose usable tokens.
- Password reset revokes all of a user's existing sessions.

## Authorization

Every state-changing action goes through two checks: route-level RBAC
(`require_roles`) and service-level ownership (`assert_is_owner_or_admin`,
or explicit checks in services like `OrderService.transition`). See
[authentication.md](./authentication.md#authorization-rbac).

## Input validation

All request bodies are Pydantic models (`app/schemas/`) with explicit
constraints (`Field(..., gt=0)`, `min_length`, etc.). File uploads are
validated for content-type and size before ever reaching storage
(`app/utils/file_upload.py`).

## Rate limiting

`slowapi`, configured in `app/main.py`. Default limit applies globally;
apply stricter limits to `/auth/login`, `/auth/forgot-password`, and
webhook endpoints (`settings.RATE_LIMIT_AUTH`, `RATE_LIMIT_WEBHOOK`).

## Webhook verification

Every payment/delivery webhook handler verifies a cryptographic signature
over the **raw request body** before processing anything
(`PaymentProvider.verify_webhook_signature`). No webhook is ever trusted
based on IP allow-listing alone.

## Secure file uploads

Uploads go through `StorageProvider`, never saved with client-controlled
paths. Private documents (KYC/KYB) are only ever resolved via
time-limited signed URLs (`get_signed_url`), gated by an ownership/admin
check in the calling service.

## Database access controls

- Application connects as a dedicated `fashionhub` role, not a superuser.
- Row-level locks (`with_for_update()`) are used wherever concurrent
  mutation could cause a race (inventory decrement, order status
  transitions) — see [database.md](./database.md).

## OWASP-relevant mitigations present in this scaffold

| Risk | Mitigation |
|---|---|
| Broken access control | Route RBAC + service-level ownership checks everywhere |
| Injection | SQLAlchemy parameterized queries throughout; no raw string-interpolated SQL |
| Sensitive data exposure | Location precision truncation; private KYC docs via signed URLs; secrets never in code |
| Broken auth | bcrypt hashing, short-lived JWTs, hashed refresh tokens, session revocation |
| Security misconfiguration | `.env`-based config, `DEBUG`/docs disabled in production (`app/main.py`) |
| SSRF | Provider integrations call fixed, known provider hostnames only |
| CSRF | N/A for a stateless bearer-token API; ensure any cookie-based session (if added) sets `SameSite` |

## Audit logging

`AuditService.record` — call from any service performing a
security-sensitive or business-critical action (logins, role changes,
payment/refund decisions, verification approvals). Written to the
append-only `audit_logs` table.

## Environment variables

Never commit `.env`. See [environment-variables.md](./environment-variables.md)
for the full variable reference and `.env.example` for the template.
