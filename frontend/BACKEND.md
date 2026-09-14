# Backend reference

The backend for this project lives at:

**https://github.com/baalebos-cloud/fashion-hub**

This frontend was built against the API contract documented in
`backend/docs/api-reference.md` and the endpoint list in
`src/lib/api/endpoints.ts`, which mirror the scaffold originally generated
in this workspace (see `backend/app/api/v1/*.py`).

## Note on staying in sync

This sandbox has no outbound network access, so changes pushed to the
GitHub repo after this point can't be pulled in or diffed automatically
here. If the backend's routes, request/response shapes, or status enums
have changed since:

1. Update `src/lib/api/endpoints.ts` to match any renamed/added/removed routes.
2. Update `src/types/*.ts` to match any changed request/response schemas.
3. Update `src/constants/order-status.ts` (and the other `*-status.ts`
   files) if `backend/app/core/constants.py`'s enums changed.
4. Update `src/components/ai/AIQuickActions.tsx` and
   `AINavigationGuide.tsx` if the backend's `ROLE_APP_MAP`
   (`backend/app/integrations/ai/navigation_agent.py`) changed.

Everything in this frontend was written to isolate backend-shape
assumptions into those specific files precisely so a backend change only
requires updating a handful of well-known spots rather than hunting
through components.
