# UI Guidelines

## Palette — "workroom," not generic SaaS

- `ink` (#1c2230) — primary text, dark surfaces (headers, the AI
  assistant's launcher)
- `muslin` (#ece7db) — the AI panel surface and dashboard backgrounds; a
  nod to the unbleached cotton used in garment drafting
- `paper` (#faf9f5) — cards, inputs, message bubbles
- `brass` (#ab8a52) — the one accent color, used sparingly for the primary
  brand mark and focus/active states — pins and tape-measure hardware
- `thread` (#8a3a2b) — a muted pin-cushion red, used for destructive
  actions and the person's own chat bubbles

## Typography

`Fraunces` (serif) for headings/display text — editorial, not corporate.
`Inter` for everything else. Both loaded via Google Fonts in
`styles/globals.css`.

## Timestamps — always through DateTimeDisplay

Every rendered date/time in this app must go through
`components/common/DateTimeDisplay.tsx` (or, for a raw string,
`lib/formatters/date.ts` + `hooks/use-timezone.ts` directly) — never
`new Date(x).toLocaleString()` inline in a component. This is what makes
"the backend always sends UTC, the person always sees their own timezone"
a property of the whole app rather than something each page has to
remember.

## Accessibility baseline

- Every interactive element has a visible focus ring
  (`:focus-visible` in `styles/globals.css`) — never suppressed without a
  replacement.
- Modals/drawers/the AI panel all close on `Escape` and trap focus at the
  container level.
- `prefers-reduced-motion` is respected globally.
