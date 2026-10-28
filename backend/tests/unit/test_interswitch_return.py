"""The browser return cannot fabricate paid status or select conflicting references."""
import pytest

from app.services.interswitch_return import redirect_for_interswitch_return


@pytest.mark.parametrize("key", ["txnref", "txn_ref", "transactionreference", "reference"])
def test_provider_reference_variants(key):
    link = redirect_for_interswitch_return(**{key: "seam_123"})
    assert "provider=interswitch" in link
    assert "reference=seam_123" in link


def test_conflicting_references_not_forwarded():
    link = redirect_for_interswitch_return(txnref="seam_good", txn_ref="seam_wrong")
    assert "reference=" not in link


@pytest.mark.parametrize("value", ["../bad", "bad?status=paid", "hello world", "é"])
def test_invalid_reference_rejected(value):
    assert "reference=" not in redirect_for_interswitch_return(txnref=value)


def test_return_does_not_trust_success_claims():
    link = redirect_for_interswitch_return(txnref="seam_test")
    assert "successful" not in link
    assert "paid" not in link


def test_direct_route_invocation_with_fastapi_form_defaults():
    # Regression: calling a FastAPI handler directly retains Form objects in
    # unprovided parameters. These must not count as conflicting references.
    from app.api.v1.interswitch import browser_return
    redirect = browser_return(txnref="seam_test")
    assert redirect.status_code == 303
    assert "reference=seam_test" in redirect.headers["location"]
