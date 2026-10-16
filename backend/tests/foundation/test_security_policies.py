"""Dependency-light tests; run with python -m unittest discover -s tests/foundation."""
import unittest
from decimal import Decimal

from pydantic import ValidationError

from app.core.config import Settings
from app.core.policies import PUBLIC_SIGNUP_ROLES, validate_payment_identity, money_to_minor_units


class SettlementPolicyTests(unittest.TestCase):
    def validate(self, **overrides):
        values = dict(expected_reference="ref-123", reference="ref-123",
                      expected_amount=Decimal("125.10"), amount="125.10",
                      expected_currency="NGN", currency="NGN")
        values.update(overrides)
        validate_payment_identity(**values)

    def test_exact_settlement_accepts_decimal_values(self):
        self.validate(amount=Decimal("125.100"))

    def test_rejects_underpayment_overpayment_and_invalid_numbers(self):
        for amount in ["125.09", "125.11", "0", "-1", "NaN", "Infinity", None, "bad"]:
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                self.validate(amount=amount)

    def test_rejects_wrong_currency_and_reference(self):
        for overrides in [dict(currency="USD"), dict(currency=""), dict(reference="another"), dict(reference=None)]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.validate(**overrides)

    def test_minor_units_do_not_truncate_binary_float_amounts(self):
        for amount, expected in [(0.29, 29), (1.15, 115), (100.01, 10001), (Decimal("999999.99"), 99999999)]:
            self.assertEqual(money_to_minor_units(amount), expected)

    def test_minor_units_reject_invalid_or_fractional_subunits(self):
        for amount in ["NaN", "Infinity", "-1", "0", "1.001", None]:
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                money_to_minor_units(amount)

    def test_public_roles_exclude_privileged_and_unknown_roles(self):
        self.assertNotIn("admin", PUBLIC_SIGNUP_ROLES)
        self.assertNotIn("superadmin", PUBLIC_SIGNUP_ROLES)
        self.assertIn("customer", PUBLIC_SIGNUP_ROLES)


class DeploymentSettingsTests(unittest.TestCase):
    def production(self, **overrides):
        values = dict(_env_file=None, APP_ENV="production", DEBUG=False,
                      SECRET_KEY="x" * 48, DATABASE_ECHO=False,
                      CORS_ALLOWED_ORIGINS=["https://fashion.example"],
                      RATE_LIMIT_STORAGE_URI="redis://localhost:6379/3")
        values.update(overrides)
        return Settings(**values)

    def test_accepts_explicit_production_settings(self):
        self.assertTrue(self.production().is_production)

    def test_refuses_unsafe_production_configuration(self):
        for overrides in [dict(SECRET_KEY="change-me-in-env"), dict(DEBUG=True),
                          dict(DATABASE_ECHO=True), dict(CORS_ALLOWED_ORIGINS=["*"]),
                          dict(CORS_ALLOWED_ORIGINS=["http://fashion.example"]),
                          dict(CORS_ALLOWED_ORIGINS=[]), dict(RATE_LIMIT_STORAGE_URI="memory://")]:
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                self.production(**overrides)

    def test_rejects_misspelled_environment(self):
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, APP_ENV="prodution")


if __name__ == "__main__":
    unittest.main()
