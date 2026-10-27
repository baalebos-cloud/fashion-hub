"""DB-backed authentication mail outbox. Never publish raw reset tokens to Redis."""
import base64
import hashlib
from html import escape
from urllib.parse import quote

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timezone import utcnow
from app.models.notification import Notification
from app.models.user import User

KINDS = {
    "verification": ("auth.email_verification", "Verify your Fashion Hub account", "verify-email"),
    "password_reset": ("auth.password_reset", "Reset your Fashion Hub password", "reset-password"),
}


def _cipher():
    # A domain-separated encryption key derived from the protected application
    # secret. Rotation invalidates outstanding links, just like JWT rotation.
    digest = hashlib.sha256((settings.SECRET_KEY + ":auth-email-outbox:v1").encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


class AuthEmailOutboxService:
    def __init__(self, db: Session):
        self.db = db

    def enqueue(self, *, user: User, kind: str, token: str) -> None:
        event, subject, _ = KINDS[kind]
        self.db.add(Notification(
            recipient_user_id=user.id, channel="email", event_type=event,
            title=subject, body="Authentication email is awaiting dispatch.",
            metadata_json={"ciphertext": _cipher().encrypt(token.encode()).decode()},
        ))

    def process_one(self) -> bool:
        events = [info[0] for info in KINDS.values()]
        job = (self.db.query(Notification)
               .filter(Notification.channel == "email", Notification.event_type.in_(events),
                       Notification.sent_at.is_(None))
               .order_by(Notification.created_at, Notification.id)
               .with_for_update(skip_locked=True).populate_existing().first())
        if job is None:
            return False
        user = self.db.get(User, job.recipient_user_id)
        if not user or not user.is_active:
            job.sent_at, job.metadata_json = utcnow(), None
            self.db.commit()
            return True

        kind = next(key for key, data in KINDS.items() if data[0] == job.event_type)
        _, subject, path = KINDS[kind]
        token = _cipher().decrypt(job.metadata_json["ciphertext"].encode()).decode()
        url = f"{settings.FRONTEND_URL.rstrip('/')}/{path}?token={quote(token, safe='')}"
        from app.integrations.notifications.email import send_email
        send_email(
            to_address=user.email, subject=subject,
            html_body=f'<p>Use this secure link to continue: <a href="{escape(url, quote=True)}">Open link</a></p>',
            idempotency_key=f"auth-email-{job.id}",
        )
        job.sent_at, job.metadata_json = utcnow(), None
        self.db.commit()
        return True
