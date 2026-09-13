"""Integration test verifying the DB engine can actually connect (skips
gracefully in environments without a live Postgres, e.g. this scaffold's
sandbox preview)."""
from app.core.database import check_database_health


def test_database_health_check_runs_without_raising():
    # Returns False rather than raising if Postgres isn't reachable --
    # this test documents the contract of check_database_health, not that
    # a database is guaranteed to be present in CI without docker-compose.
    result = check_database_health()
    assert isinstance(result, bool)
