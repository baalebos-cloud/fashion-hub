#!/usr/bin/env python
"""
Email a fresh confirmation link to every account that registered but never confirmed.
Safe to re-run: people already waiting for an email aren't queued twice.

Usage (Railway shell): python scripts/resend_verification_emails.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import session_scope
from app.integrations.notifications.email import provider_status
from app.services.auth_email_outbox_service import AuthEmailOutboxService


def main():
    status = provider_status()
    if not status["ready"]:
        print(f"Email isn't configured: {status['problem']}")
        sys.exit(1)
    with session_scope() as db:
        service = AuthEmailOutboxService(db)
        queued = service.queue_for_unverified()
        print(f"Queued {queued} confirmation emails. Sending...")
        totals = {"sent": 0, "failed": 0}
        while True:
            result = service.send_pending(limit=50)
            totals["sent"] += result["sent"]
            totals["failed"] += result["failed"]
            if result["sent"] == 0:
                break
        print(f"Sent {totals['sent']}. Not accepted by the provider: {totals['failed']} (retried automatically).")


if __name__ == "__main__":
    main()
