"""Rules for shareable storefront handles (shared by the API and migration 0018)."""
import re
import unicodedata

HANDLE_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9]|-(?!-)){1,28}[a-z0-9]$")

# Words that would read as Tailora pages or official accounts.
RESERVED_HANDLES = frozenset({
    "admin", "api", "app", "about", "account", "auth", "billing", "blog", "checkout",
    "contact", "customer", "delivery", "designer", "designers", "dispatch", "help",
    "home", "login", "logout", "marketplace", "official", "orders", "payments",
    "pricing", "privacy", "professional", "professionals", "rider", "s", "seam",
    "settings", "shop", "signup", "staff", "support", "tailor", "tailora", "tailors",
    "team", "terms", "vendor", "vendors", "www",
})


def is_valid_handle(handle: str) -> bool:
    return bool(HANDLE_PATTERN.fullmatch(handle)) and handle not in RESERVED_HANDLES


def slugify_handle(name: str | None) -> str:
    """Best-effort handle from a business name; may be empty or reserved."""
    ascii_name = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug[:30].rstrip("-")


def candidate_handles(name: str | None, fallback_seed: str):
    """Yield acceptable handles in preference order: name, name-2, ..., then a seeded fallback."""
    base = slugify_handle(name)
    if is_valid_handle(base):
        yield base
    if len(base) >= 2:
        stem = base[:26].rstrip("-")
        for n in range(2, 100):
            candidate = f"{stem}-{n}"
            if is_valid_handle(candidate):
                yield candidate
    yield f"shop-{fallback_seed.replace('-', '')[:10]}"
