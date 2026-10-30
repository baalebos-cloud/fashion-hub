"""Regression tests for fail-closed Interswitch sandbox requery."""
import unittest
from decimal import Decimal
from unittest.mock import Mock

import httpx

from app.core.exceptions import ExternalProviderError
from app.integrations.payments.interswitch_checkout import requery_transaction


class RequeryTests(unittest.TestCase):
    def query(self, response=None, error=None):
        client = Mock()
        if error:
            client.get.side_effect = error
        else:
            client.get.return_value = response
        return requery_transaction(
            merchant_code="TEST", reference="test-reference",
            expected_amount=Decimal("30.00"), client=client,
        )

    def test_approved_matching_result(self):
        result = self.query(httpx.Response(200, json={
            "MerchantReference": "test-reference", "Amount": 3000, "ResponseCode": "00",
        }, request=httpx.Request("GET", "https://example.test")))
        self.assertTrue(result.successful)

    def test_unapproved_does_not_set_success(self):
        result = self.query(httpx.Response(200, json={
            "MerchantReference": "test-reference", "Amount": 3000, "ResponseCode": "51",
        }, request=httpx.Request("GET", "https://example.test")))
        self.assertFalse(result.successful)

    def test_timeout_never_approves(self):
        with self.assertRaisesRegex(ExternalProviderError, "timed out"):
            self.query(error=httpx.ReadTimeout("timeout"))

    def test_http_error_never_approves(self):
        with self.assertRaisesRegex(ExternalProviderError, "rejected"):
            self.query(httpx.Response(502, request=httpx.Request("GET", "https://example.test")))

    def test_invalid_json_never_approves(self):
        with self.assertRaisesRegex(ExternalProviderError, "invalid response"):
            self.query(httpx.Response(200, content=b"not json", request=httpx.Request("GET", "https://example.test")))

    def test_reference_mismatch_never_approves(self):
        with self.assertRaisesRegex(ExternalProviderError, "do not match"):
            self.query(httpx.Response(200, json={
                "MerchantReference": "different", "Amount": 3000, "ResponseCode": "00",
            }, request=httpx.Request("GET", "https://example.test")))

    def test_amount_mismatch_never_approves(self):
        with self.assertRaisesRegex(ExternalProviderError, "do not match"):
            self.query(httpx.Response(200, json={
                "MerchantReference": "test-reference", "Amount": 100, "ResponseCode": "00",
            }, request=httpx.Request("GET", "https://example.test")))


if __name__ == "__main__":
    unittest.main()
