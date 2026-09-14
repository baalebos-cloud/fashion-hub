# State Management

Zustand for all shared/global state (`src/store/*.ts`). Local component
state (`useState`) is still the right tool for anything that doesn't need
to be read from more than one place — most form fields, a dropdown's
open/closed state, etc.

## What lives in a store vs. a hook

- **Store**: the actual state and the functions that mutate it
  (`store/order.store.ts`).
- **Hook**: the ergonomic, component-facing interface
  (`hooks/use-orders.ts`), often adding a `useEffect` to fetch on mount.

Components should almost always import the hook, not the store directly —
this indirection is what let `hooks/use-timezone.ts` layer extra logic
(the fallback chain) on top of `useAuthStore` without every consumer
needing to know about it.

## Notable stores

- **`auth.store.ts`**: the only store with an explicit `initialize()`
  lifecycle method, called once from `App.tsx` on boot.
- **`cart.store.ts`**: deliberately NOT optimistic — every mutation
  re-syncs from the backend's response rather than guessing the new state,
  because the backend can reject a change (stock ran out) that looked fine
  a moment ago. See `backend/docs/cart.md`.
- **`ai.store.ts`**: the assistant's open/closed state and conversation are
  global specifically so opening it from a completely different page than
  where it was last used continues the same conversation. This is the
  mechanism behind "available throughout the application."
