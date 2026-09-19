# AI Assistant (Seam)

## Mounted once, globally

`App.tsx`'s `GlobalAssistant` (not exported — an internal piece of the app
shell) decides which of three things renders, based on auth state and the
current path:

| State | Renders |
|---|---|
| Session still resolving (`isInitializing`) | Nothing — avoids a flash of "sign in" right before the real assistant appears for an already-logged-in person |
| Authenticated | `components/ai/AIAssistant.tsx` — the real, backend-backed chat |
| Not authenticated, on an auth page (`/login`, `/signup`, etc.) | Nothing — prompting sign-in there is redundant |
| Not authenticated, anywhere else | `components/ai/AIPublicTeaser.tsx` — a look-alike button that links straight to `/login` |

The teaser exists, not the real chat, on public pages for a structural
reason, not a design preference: the backend's
`POST /ai/navigation/messages` requires `get_current_user` (see
`backend/app/api/v1/ai_navigation.py`) — there's no anonymous-conversation
endpoint. Opening a real chat panel pre-login would let someone type a
message and then fail on send, which is worse than not offering it. The
teaser is honest about that instead.

`AIAssistant.tsx` itself renders `AIHelpButton` + `AIChatWindow` through a
React portal into `document.body`, alongside the router rather than inside
it. This is what makes the (real) assistant available on every
authenticated screen rather than confined to one page — closing the panel
on an order page and reopening it from Settings continues the exact same
conversation, because the state lives in the global `ai.store.ts`, not
component state.

**Implementation note**: `GlobalAssistant` is mounted as a sibling of
`<RouterProvider>`, not inside it, so it can't use React Router's
`useLocation()` hook (that only works for descendants of the router). It
instead subscribes directly to the `router` instance's own `.subscribe()`
API to know the current path — see the comment in `App.tsx` if you're
adding similar router-aware-but-outside-the-tree components.

## Component breakdown

| File | Role |
|---|---|
| `AIAssistant.tsx` | Mount point; renders the two pieces below via portal |
| `AIPublicTeaser.tsx` | Pre-login stand-in that links to `/login` instead of opening chat |
| `AIHelpButton.tsx` | The floating "Ask Seam" launcher |
| `AIChatWindow.tsx` | The expandable panel: header, thread, composer |
| `AIMessage.tsx` | A single chat bubble |
| `AIInput.tsx` | The composer textarea + send button |
| `AIQuickActions.tsx` | Role-scoped suggested prompts shown before the first message |
| `AINavigationGuide.tsx` | Turns an allow-listed destination into a real, guard-respecting link |

## The boundary this feature must never cross

> The AI can guide the user, but it should not bypass frontend route
> guards or backend authorization.

Concretely, enforced in `AINavigationGuide.tsx`:

- It only ever links to a **static, role-scoped page** from a hard-coded
  allow-list (`NAMED_DESTINATIONS`), keyed by the CURRENT user's own role —
  never an arbitrary path parsed out of the model's free-text response.
- The link it renders is a plain `<Link>`, which passes through
  `AuthGuard`/`RoleGuard` exactly like any other in-app navigation. There
  is no special "the AI said so" bypass path.
- It never links to another user's specific resource (an order ID, a
  conversation ID) — only to a page, never a record.

The actual conversational safety (never revealing another user's data,
never claiming to execute a payment/refund/status change) is enforced
server-side by the system prompt in
`backend/app/integrations/ai/prompts.py` — this frontend's job is narrower
and purely structural: make sure that even if the model said something it
shouldn't, the UI has no mechanism to act on it beyond a normal,
guard-respecting link.

## Keeping quick-prompts in sync

`AIQuickActions.tsx`'s prompt list is a client-side mirror of the
backend's `ROLE_APP_MAP`
(`backend/app/integrations/ai/navigation_agent.py`). Update both when a
route is added/renamed/removed so the assistant never suggests, or is
asked about, a page a given role can't reach.
