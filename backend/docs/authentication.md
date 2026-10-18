# Authentication

## Flow

- `POST /api/v1/auth/signup` — creates a `User` row (role one of
  `customer|tailor|designer|vendor|delivery_partner`), hashes the password
  with Argon2id, and enqueues a verification email.
- `POST /api/v1/auth/login` — verifies credentials, issues a short-lived
  JWT access token (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 30 min) and a
  longer-lived refresh token (`REFRESH_TOKEN_EXPIRE_DAYS`, default 14
  days). The refresh token's **hash** (not the raw token) is stored in
  `sessions`, so a stolen database dump can't be used to forge sessions.
- `POST /api/v1/auth/refresh` — exchanges a valid, non-revoked refresh
  token for a new access token.
- `POST /api/v1/auth/logout` — revokes the given refresh token's session.
- `POST /api/v1/auth/verify-email`, `/forgot-password`, `/reset-password`
  — standard token-based flows; a password reset revokes all of the user's
  existing sessions.

## Authorization (RBAC)

Two layers, always used together:

1. **Route-level role check** — `require_roles(Role.TAILOR, Role.DESIGNER)`
   as a FastAPI dependency. Fails fast with 403 before any business logic
   runs.
2. **Service-level ownership check** — e.g. `OrderService.transition`
   additionally verifies that a tailor calling `/accept` actually owns
   *this* order (`order.seller_user_id == actor.id`), and that
   `/received` can only be called by `order.buyer_user_id`. A role check
   alone is never sufficient for owned resources.

## Rate limiting

`slowapi` is wired in `app/main.py`. Apply
`settings.RATE_LIMIT_AUTH` (default `10/minute`) specifically to
`/login`, `/forgot-password`, and `/reset-password` — these are classic
brute-force/enumeration targets.

## Credential compatibility

New hashes use Argon2id. Existing bcrypt and bcrypt_sha256 hashes remain valid
and are replaced with Argon2id after a successful active-account login, in the
same commit as the new refresh session. Failed/inactive logins do not replace
hashes. JWTs use PyJWT with the configured signing algorithm; the issuer controls
identity, role, expiry and token type, and decoders require the issuer's identity
and expiry claims. Keep `SECRET_KEY` and `JWT_ALGORITHM` stable to preserve
existing standard JWTs. See the [security rollout](../../docs/dependency-security.md)
before rolling back an application image.

## Password requirements

Enforced in `app/schemas/auth.py::SignUpRequest` — minimum 8 characters,
at least one letter and one digit. Adjust to your compliance requirements.
