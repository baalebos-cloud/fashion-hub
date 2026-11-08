# Recommendations, part 4: describe-what-you-want design search

A "Describe what you want" box on the customer "Find a professional" page and the public "Find a
tailor" page. Type "blue agbada under 50k"; it shows what it understood (word chips and a budget)
and matching designs from verified tailors, each linking to the tailor's profile.

## How text becomes filters (`services/smart_search_service.py`)

1. Emails and phone numbers are removed from the text first.
2. **AI on** (`AI_SEARCH_ENABLED=true`): the configured AI provider (`AI_PROVIDER`) returns JSON
   filters (garment, style words, budget). Only the cleaned search text is sent. The reply is
   checked strictly: only plain words (max 6), budgets 0–₦10m, min/max swapped if reversed; any
   other value is dropped. If the reply is malformed, empty, fails, or takes longer than
   `AI_SEARCH_TIMEOUT_SECONDS` (6), the keyword parser is used instead. Successful replies are
   cached in memory for repeat searches. If the AI leaves out a budget the text states plainly,
   the parser's budget is kept.
3. **AI off** (the default) or fallback: the keyword parser reads budgets ("under 50k",
   "between 20k and 40k", "below ₦30,000", "over 100000") and keeps meaningful words.
4. The filters search published designs from active, verified tailors who accept orders. Designs
   matching more words rank first (title counts double), then cheaper first.

The AI never names products, tailors or prices; it only produces filters, and results always come
from the database. The response says `understood_by: "ai" | "keywords"` and the page shows it.

## API

`GET /api/v1/search/smart?q=…&limit=20` (public, 30/minute per IP) returns
`{understood_by, filters: {keywords, min_price, max_price}, designs: [... + professional_name]}`.

Searches are recorded as shopping activity (`source=smart_search`) under part 1's rules, and result
links carry `?from=smart_search`.

## Turning AI on

Set `AI_SEARCH_ENABLED=true` on the backend, with a working `AI_PROVIDER` and its key (for example
`AI_API_KEY` for Anthropic). No other change is needed.
