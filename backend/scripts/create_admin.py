#!/usr/bin/env python
"""
Creates the platform admin, or resets their authenticator-app sign-in.

The email must be listed in ADMIN_EMAILS (staging/production). The password is asked for
interactively so it never lands in shell history or deploy logs. The authenticator app is
set up on the first sign-in at /admin/login.

Usage:
  python scripts/create_admin.py --email you@example.com
  python scripts/create_admin.py --email you@example.com --reset-2fa   # lost phone
  python scripts/create_admin.py --email you@example.com --promote     # turn an existing account into the admin
"""
import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.admin_access import admin_email_allowed
from app.core.constants import UserRole
from app.core.database import session_scope
from app.core.security import hash_password
from app.models.activity_log import AdminCredential
from app.models.user import RefreshSession, User


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", default="Platform Admin")
    parser.add_argument("--reset-2fa", action="store_true",
                        help="Clear the authenticator app so the next sign-in sets it up again.")
    parser.add_argument("--promote", action="store_true",
                        help="Make an existing account with this email the admin (keeps its password).")
    parser.add_argument("--password", help=argparse.SUPPRESS)  # local/dev automation only
    args = parser.parse_args()
    email = args.email.lower().strip()

    if not admin_email_allowed(email):
        print(f"{email} is not in ADMIN_EMAILS. Add it to the environment first.")
        sys.exit(1)

    with session_scope() as db:
        user = db.query(User).filter(User.email == email).first()
        if args.reset_2fa:
            if user is None or user.role != UserRole.ADMIN.value:
                print("No admin account with that email.")
                sys.exit(1)
            db.query(AdminCredential).filter_by(user_id=user.id).delete()
            db.query(RefreshSession).filter(RefreshSession.user_id == user.id).update({"revoked": True})
            print("Two-step sign-in reset and all admin sessions signed out. Set it up again at /admin/login.")
            return
        if user is not None and args.promote:
            user.role = UserRole.ADMIN.value
            user.is_active = True
            db.query(AdminCredential).filter_by(user_id=user.id).delete()
            db.query(RefreshSession).filter(RefreshSession.user_id == user.id).update({"revoked": True})
            print(f"{email} is now the admin. Sign in at /admin/login to set up your authenticator app.")
            return
        if user is not None:
            print("An account with that email already exists. Re-run with --promote to make it the admin.")
            sys.exit(1)
        password = args.password or os.environ.get("ADMIN_PASSWORD") or getpass.getpass("New admin password: ")
        if len(password) < 12:
            print("Use at least 12 characters for the admin password.")
            sys.exit(1)
        if not args.password and not os.environ.get("ADMIN_PASSWORD") and getpass.getpass("Repeat password: ") != password:
            print("Passwords didn't match.")
            sys.exit(1)
        db.add(User(email=email, hashed_password=hash_password(password), full_name=args.full_name,
                    role=UserRole.ADMIN.value, is_active=True, is_email_verified=True))
    print(f"Admin created: {email}. Sign in at /admin/login to set up your authenticator app.")


if __name__ == "__main__":
    main()
