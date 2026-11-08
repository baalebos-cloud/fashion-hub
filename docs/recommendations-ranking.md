# Recommendations, part 3: personal ranking and the rules-vs-learned test

Builds on part 1 (activity, `docs/recommendations-activity.md`) and part 2 (related items,
`docs/recommendations-related-items.md`).

## Where ranking applies

| Surface | Fixed rules (today) | Learned |
|---|---|---|
| Budget guide (materials marketplace) | Cheapest in budget first | In-budget matches ranked for the shopper |
| "Picked for you" row (materials marketplace, new) | Newest buyable items ("New in") | Pool of 200 newest buyable items ranked ("Picked for you" / "Popular now") |
| Tailor/designer search (customer and public search pages) | Rating, then review count | Top 500 matches ranked for the shopper; the rest follow in rules order |

Other lists of tailors (onboarding, "Near you") keep the fixed order and are not logged; only
search pages ask for ranking (`ranked=true`).

## Learned score (`services/personal_ranking_service.py`)

`0.60 × affinity + 0.25 × trending + 0.15 × rating`, each 0–1:
- **affinity**: relatedness (part 2's similarities; bought-together ×1.5) to what this shopper
  engaged with in the last 90 days, weighted by action and halving every 30 days; items they
  engaged with directly get a smaller boost.
- **trending**: everyone's engagement over the last 14 days, halving weekly.
- **rating**: vendor or tailor rating out of 5.

With no history, trending and rating decide. Ties keep the rules order.

## The test

`RECOMMENDATIONS_MODE` = `rules` | `learned` | `experiment` (default). In `experiment`, each
shopper is fixed to one side by a hash of their account (or browser ID) and
`RECOMMENDATIONS_EXPERIMENT` (`ranking_v1`; rename it to start a fresh test). Shoppers who turned
personalisation off, or whose browser sends no ID (opted out / GPC / Do Not Track), always get the
rules order and nothing is logged.

Each ranked list shown is stored in `recommendation_impressions` (surface, variant, who, item IDs
in order). Same 180-day retention and opt-out deletion as shopping activity; no IP or location.

## Admin: Reports → Recommendations health (`GET /api/v1/admin/recommendations/health`)

Per surface and side, over 30 days: lists shown, click rate (opened an item from that list within
24 h, via the `?from=<surface>` view source) and conversion rate (added a shown item to cart or
bought it within 7 days). A winner is named only when each side has 100 lists and a two-proportion
z-test on click rate is significant at 95%. If the rules win, set `RECOMMENDATIONS_MODE=rules`.

Migration `0033`.
