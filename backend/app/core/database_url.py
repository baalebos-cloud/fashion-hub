"""Validate PostgreSQL configuration without connecting or exposing credentials."""
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def normalize_database_url(value: str) -> str:
    try:
        url = make_url(value.strip())
    except (ArgumentError, ValueError):
        # Parser errors may contain the original URL. Suppress that context
        # and let Settings report only this actionable, credential-free error.
        raise ValueError(
            "DATABASE_URL must be a valid PostgreSQL URL. Use a numeric port "
            "(for example :5432) or omit the colon and port entirely; an empty "
            "HOST:/DATABASE port is invalid. Copy the complete provider URI "
            "and URL-encode username/password characters when constructing it."
        ) from None

    if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
        raise ValueError("DATABASE_URL must use PostgreSQL with the installed psycopg driver.")
    if url.port is not None and not 1 <= url.port <= 65535:
        raise ValueError("DATABASE_URL port must be between 1 and 65535.")
    if not url.database:
        raise ValueError("DATABASE_URL must include a PostgreSQL database name.")
    if url.host and "@" in url.host:
        raise ValueError("DATABASE_URL credentials must be URL-encoded; copy the complete provider URI.")

    # Railway and other providers commonly supply postgres[ql]://. Only
    # select the installed driver; preserve the actual destination and SSL
    # options. Never guess a port or silently fall back to another database.
    return url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
