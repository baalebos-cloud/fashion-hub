# Authentication

Email/password only in the current scaffold (see backend/docs/authentication.md
for the full backend-side flow this frontend drives).

## Tokens

- Access + refresh tokens, stored via `lib/auth/token.ts` in
  **sessionStorage** (not localStorage) — deliberately: it clears when the
  tab closes, limiting how long a hypothetically-exfiltrated token via XSS
  would remain usable.
- `lib/api/interceptors.ts` attaches the access token to every request and
  transparently retries once on a 401 after refreshing — concurrent 401s
  are collapsed into a single refresh call, not one per failed request.

## Session bootstrap

`lib/auth/session.ts::restoreSession()` turns "a token exists" into "we
know who this user is" by calling `GET /users/me`. Called once from
`useAuthStore.initialize()` on app boot (see `App.tsx`).

## Role-based UI

`lib/auth/permissions.ts` — cosmetic checks only (see
`docs/routing.md#guards-are-ux-not-security`). Every function in that file
has a comment reiterating that the backend independently authorizes the
underlying action regardless of what the UI decided to render.
