"""Integration-level payment flow test placeholder -- requires a running
Postgres + Redis (see docker-compose.yml) and a sandboxed provider account."""
import pytest

pytestmark = pytest.mark.skip(reason="Requires live Postgres/Redis + sandbox payment provider credentials.")


def test_full_payment_flow_end_to_end():
    pass
