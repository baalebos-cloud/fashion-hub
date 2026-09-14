# Frontend Architecture

React 18 + TypeScript + Vite. Layer-first structure (not feature-first —
see `../src/features/*/README.md` for why that's reserved for later):

```
config/    Environment, routes, map/payment config — no secrets, ever
types/     TypeScript interfaces mirroring backend schemas
lib/       Framework-agnostic logic: api client, auth, formatters, validation
api/       One file per backend domain, thin wrappers over lib/api/client.ts
store/     Zustand stores — global state (auth, cart, orders, AI assistant)
hooks/     The public interface most components use to reach store/api
components/ Presentational + composed UI, grouped by domain
pages/     Route-level composition of components + hooks
router/    Route trees + guard wiring
guards/    Auth/role gating (UX convenience, not the security boundary)
```

## Data flow

```
Page component
  -> hook (src/hooks/*)
    -> store (src/store/*) or directly an api module for one-off reads
      -> api module (src/api/*)
        -> lib/api/client.ts (Axios + interceptors)
          -> backend REST API
```

Components never import `src/api/*` directly except through a hook or
store — this keeps data-fetching logic testable and swappable independent
of any specific component tree.

## Why Zustand over Context/Redux

Chosen for minimal boilerplate and because most of this app's shared state
(auth session, cart, the AI assistant's open/closed panel) is genuinely
global rather than scoped to a subtree — Context would work but requires
more ceremony per store; Redux's boilerplate isn't justified at this
scale. See `docs/state-management.md`.

## The frontend/backend boundary

The frontend owns UI, forms, navigation, client state, loading/error
states, and map/tracking visualization. It does **not** own business
rules, authorization decisions, payment verification, or timestamp
generation — those are exclusively the backend's job (see
`backend/docs/architecture.md`). Every place in this codebase that might
look like a business rule (e.g. `lib/auth/permissions.ts`,
`components/orders/OrderActions.tsx`) is explicitly documented as a UX
convenience that the backend re-validates independently.
