# Seam — the Fashion Hub AI assistant widget

A global, always-available assistant, not a page. Mount it once at the
application root and it follows the person across every screen —
customer, tailor, designer, vendor, or delivery partner.

```
┌───────────────────────────────────────────┐
│  Orders   Discover   Messages              │
│                                             │
│  ...the rest of the app renders here...    │
│                                             │
│                              ┌───────────┐ │
│                              │ ✦ Ask Seam│ │
│                              └───────────┘ │
└───────────────────────────────────────────┘
```

Clicking the launcher expands a chat panel anchored to the same corner.
The panel and launcher are rendered through a React portal straight into
`document.body`, so they always sit above the app regardless of any
`overflow: hidden` or `z-index` elsewhere in your layout.

## Files

```
ai-assistant/
  SeamAssistantContext.jsx   Global context: open/close state, role, quick prompts
  SeamAssistantWidget.jsx    The launcher + panel UI (portal-rendered)
  useSeamChat.js             Chat state + calls to the backend
  AskSeamLink.jsx            Contextual "Ask Seam" trigger for use elsewhere in the app
  seam-assistant.css         Self-contained styling (namespaced under .seam-root)
  index.js                   Barrel export
```

## 1. Mount it once, at the root

See `src/App.example.jsx`. In short:

```jsx
import { SeamAssistantProvider, SeamAssistantWidget } from "./components/ai-assistant";

<SeamAssistantProvider
  role={currentUser.role}                 // "customer" | "tailor" | "designer" | "vendor" | "delivery_partner"
  apiBaseUrl="/api/v1"
  getAuthToken={async () => getAccessToken()}
>
  <YourRouter />
  <SeamAssistantWidget />
</SeamAssistantProvider>
```

Do **not** mount `<SeamAssistantWidget />` on individual pages — mounting
it once at the root, outside the router, is what makes it "available
throughout the application" rather than isolated to one screen.

## 2. Open it contextually from anywhere

```jsx
import { AskSeamLink } from "../components/ai-assistant";

<AskSeamLink prompt="Why hasn't my order moved from Shipped?">
  Ask Seam about this order
</AskSeamLink>
```

Or programmatically:

```jsx
import { useSeamAssistant } from "../components/ai-assistant";

const { openWithPrompt } = useSeamAssistant();
openWithPrompt("How do I find a tailor near me?");
```

## 3. Backend contract

The widget talks to the endpoints in
`backend/app/api/v1/ai_navigation.py`:

```
POST /api/v1/ai/navigation/messages
  body: { conversation_id: string | null, content: string }
  ->    { conversation_id: string, answer: string }

GET  /api/v1/ai/navigation/conversations
GET  /api/v1/ai/navigation/conversations/{id}/messages
POST /api/v1/ai/navigation/feedback
  body: { ai_message_id: string, was_helpful: boolean }
```

`conversation_id` starts `null`; the backend creates a new conversation
and returns its id, which the widget then reuses for the rest of the
session — so a person can close the panel, reopen it, and keep talking in
the same thread without any extra wiring.

## 4. Keeping quick-prompts and routes in sync

`SeamAssistantContext.jsx::ROLE_QUICK_PROMPTS` is a client-side mirror of
the backend's `ROLE_APP_MAP`
(`backend/app/integrations/ai/navigation_agent.py`). When you add a new
page/route, update both so the assistant never suggests — or gets asked
about — a page a given role can't actually reach.

## 5. Design notes

- **Palette**: ink navy panels, a muslin (unbleached cotton) surface, a
  brass accent for the assistant's own identity, and a pin-cushion red for
  the person's own messages — a tailoring vocabulary instead of a generic
  chat-bubble blue.
- **Motion**: a single expand/collapse transition, anchored to the
  launcher's corner (`transform-origin: bottom right`), respecting
  `prefers-reduced-motion`.
- **Accessibility**: `Escape` closes the panel, focus moves to the
  composer on open, and all interactive elements have visible focus rings
  and `aria-label`s.
- **Mobile**: below 480px the panel becomes a near-full-screen sheet
  instead of a fixed-width card.

## 6. What Seam will and won't do

Per the backend's system prompt
(`backend/app/integrations/ai/prompts.py`), Seam only tells people where
to go and how something works — it never executes a payment, refund, or
order-status change, and it never reveals another user's data. The
composer's footnote line exists to set that expectation up front.
