import pytest

pytestmark = pytest.mark.skip(reason="Requires a configured test database.")


def test_review_only_after_received():
    pass
