#!/usr/bin/env python
"""
Creates one sample user per role for local development/manual testing.
Never run against a production database.

Usage: python scripts/create_test_users.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.core.constants import UserRole
from app.core.database import session_scope
from app.core.security import hash_password
from app.models.user import User

TEST_PASSWORD = "Password123"

SAMPLE_USERS = [
    ("customer@example.com", UserRole.CUSTOMER, "Test Customer"),
    ("tailor@example.com", UserRole.TAILOR, "Test Tailor"),
    ("designer@example.com", UserRole.DESIGNER, "Test Designer"),
    ("vendor@example.com", UserRole.VENDOR, "Test Vendor"),
    ("courier@example.com", UserRole.DELIVERY_PARTNER, "Test Delivery Partner"),
]


def main():
    if settings.is_production:
        print("Refusing to run create_test_users.py against a production environment.")
        return

    with session_scope() as db:
        for email, role, full_name in SAMPLE_USERS:
            if db.query(User).filter(User.email == email).first():
                continue
            db.add(
                User(
                    email=email,
                    hashed_password=hash_password(TEST_PASSWORD),
                    full_name=full_name,
                    role=role.value,
                    is_active=True,
                    is_email_verified=True,
                )
            )
    print(f"Test users created (password for all: {TEST_PASSWORD}).")


if __name__ == "__main__":
    main()
