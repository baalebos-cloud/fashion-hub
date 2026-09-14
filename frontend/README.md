# Fashion Hub — Frontend

React 18 + TypeScript + Vite frontend for the Fashion Hub marketplace,
implementing dashboards for five roles (Customer, Tailor/Designer, Vendor,
Delivery Partner, Admin) plus a public marketing site, all sharing one
globally-available AI assistant, **Seam**.

Backend: **https://github.com/baalebos-cloud/fashion-hub** — see
[`BACKEND.md`](./BACKEND.md) for how this frontend stays in sync with it.

## Quick start

```bash
cp .env.example .env.local     # fill in secrets, or leave defaults for local dev
npm install
npm run dev                    # http://localhost:5173, proxies /api to localhost:8000
```

```bash
npm run build      # type-check + production build to dist/
npm run test       # vitest
npm run lint        # eslint
```

## Project layout

```
public/            Static assets: favicon, logos, manifest, placeholder images
src/
  config/          Environment, routes, map/payment config — no secrets
  types/           TypeScript interfaces mirroring backend schemas
  lib/             Framework-agnostic logic (api client, auth, formatters, validation, maps, storage, notifications, utils, payments)
  api/             One file per backend domain — the only files that call lib/api/client.ts
  store/           Zustand global state
  hooks/           The interface components actually use (wraps store/api)
  components/      UI, grouped by domain — see components/ai/ for the assistant
  pages/           Route-level composition, grouped by role
  router/          Route trees + guard wiring
  guards/          Auth/role gating (UX only — see docs/routing.md)
  features/        Reserved for a future feature-first reorg (currently empty)
  constants/       Enums/labels mirroring backend/app/core/constants.py
  styles/          Global CSS + design tokens
tests/             unit / components / pages / integration / e2e
docs/              Full documentation set — see docs/frontend-architecture.md
```

## What's fully implemented vs. scaffolded

**Fully implemented:**
- Auth flow (login/signup/forgot/reset/verify), token refresh, session bootstrap
- The complete customer order lifecycle UI (list, detail, timeline, actions,
  the customer-only "Mark as Received" flow, tracking)
- **Seam**, the global AI assistant (`components/ai/`) — mounted once,
  available on every authenticated screen, with a guard-respecting
  navigation boundary (see `docs/ai-assistant.md`)
- The full API client layer (28 domain modules), all Zustand stores, all
  hooks, the full router with role guards, and the complete UI primitive kit
- Global timestamp handling (`DateTimeDisplay` + `use-timezone` +
  `lib/formatters/date.ts`)

**Documented scaffolds** (each has a docstring naming its hook/hooks and
the pattern to follow): most domain-specific components (marketplace,
checkout details, invoices, verification forms, messaging) and most
individual pages beyond the customer order flow.

## The one hard rule

Nothing in this frontend is the security boundary. Route guards, role
checks (`lib/auth/permissions.ts`), and hidden buttons are all UX —
every one of them is re-validated independently by the backend on every
request. See `docs/routing.md#guards-are-ux-not-security` and
`backend/docs/security.md`.
