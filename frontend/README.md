# Fashion Hub — Frontend

This folder currently holds one piece: **Seam**, the global AI assistant
widget, framework-agnostic beyond React itself (no UI kit or CSS framework
required — see `src/components/ai-assistant/`).

Start here: [`src/components/ai-assistant/README.md`](./src/components/ai-assistant/README.md)

```
frontend/
  src/
    components/
      ai-assistant/     Seam — global assistant widget (see its README)
    App.example.jsx      Example root-level mount
  package.json
```

## Why this exists as its own package for now

The full customer/professional/vendor/delivery-partner web app isn't
scaffolded yet. This folder starts with the one piece requested — a
frontend component available throughout the application rather than
confined to a single page — built so it can be dropped into whatever
React app shell you build next (Next.js, Vite, Remix, etc.) with no
assumptions beyond React 18 and a fetch-capable browser.
