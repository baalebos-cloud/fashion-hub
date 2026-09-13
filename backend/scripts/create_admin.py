#!/usr/bin/env python
"""
Creates the first admin user. Run once during initial deployment; refuse to
run again if an admin already exists to avoid silently creating extras.

Usage: python scripts/create_admin.py --email admin@example.com --password 'ChangeMe123!'
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.constants import UserRole
from app.core.database import session_scope
from app.core.security import hash_password
from app.models.user import User


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", default="Platform Admin")
    args = parser.parse_args()

    with session_scope() as db:
        existing_admin = db.query(User).filter(User.role == UserRole.ADMIN.value).first()
        if existing_admin:
            print(f"An admin already exists ({existing_admin.email}). Refusing to create another via this script.")
            return

        admin = User(
            email=args.email.lower().strip(),
            hashed_password=hash_password(args.password),
            full_name=args.full_name,
            role=UserRole.ADMIN.value,
            is_active=True,
            is_email_verified=True,
        )
        db.add(admin)
    print(f"Admin user created: {args.email}")


if __name__ == "__main__":
    main()
