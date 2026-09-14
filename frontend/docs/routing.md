# Routing

`react-router-dom` v6, configured in `src/router/index.tsx` via
`createBrowserRouter`. Route path *strings* live in
`src/config/routes.config.ts`, grouped by role — no component should
hard-code a path literal.

## Guard nesting

```
<AuthGuard>                 must be logged in
  <CustomerGuard>           must be role=customer
    /app/customer/*
  <ProfessionalGuard>       must be role=tailor|designer
    /app/professional/*
  <VendorGuard>             must be role=vendor
    /app/vendor/*
  <DeliveryGuard>           must be role=delivery_partner
    /app/delivery/*
  <AdminGuard>              must be role=admin
    /app/admin/*
```

`AuthGuard` shows a spinner while `useAuthStore.initialize()` is
resolving, then either renders `<Outlet />` or redirects to `/login` with
the originally-requested location preserved in `location.state.from` (so
`LoginForm` can send the person back where they meant to go).

## Public vs. authenticated routes

`public.routes.tsx` and `auth.routes.tsx` are NOT behind any guard —
marketing pages and the login/signup flow must be reachable while logged
out by definition.

## Guards are UX, not security

Every guard document in `src/guards/` repeats this, deliberately: a role
guard decides what renders. It has no bearing on what the backend will
accept. See `backend/docs/security.md`.
