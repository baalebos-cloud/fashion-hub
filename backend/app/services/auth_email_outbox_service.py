"""DB-backed authentication mail outbox. Never publish raw reset tokens to Redis.

Jobs are rows in `notifications` (channel=email). They are sent right after the request that
created them (no background worker needed) and retried by the Celery beat drain if the
provider was down. A failing address backs off and is eventually parked, so it can never block
everyone else's mail.

Verification links are minted when the email is *sent*, not when it was queued, so a link
never arrives already expired; the job only stores who to send to. Password-reset links are
bound to the password at request time, so their token is stored, Fernet-encrypted.
"""
import base64
import hashlib
from datetime import timedelta
from html import escape
from urllib.parse import quote

from cryptography.fernet import Fernet
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.timezone import utcnow
from app.models.notification import Notification
from app.models.user import User

logger = get_logger(__name__)

KINDS = {
    "verification": ("auth.email_verification", "Confirm your email for Tailora", "verify-email"),
    "password_reset": ("auth.password_reset", "Reset your Tailora password", "reset-password"),
}
EVENTS = [info[0] for info in KINDS.values()]
MAX_ATTEMPTS = 8
MAX_BATCH = 20000  # safety stop for "send everything" runs


def _cipher():
    # A domain-separated encryption key derived from the protected application
    # secret. Rotation invalidates outstanding links, just like JWT rotation.
    digest = hashlib.sha256((settings.SECRET_KEY + ":auth-email-outbox:v1").encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _now_iso() -> str:
    return utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def render(kind: str, *, name: str, url: str) -> str:
    """A plain, mobile-friendly email that works in Gmail and Outlook (inline styles only)."""
    first = escape((name or "").strip().split(" ")[0] or "there")
    safe_url = escape(url, quote=True)
    if kind == "verification":
        heading, lead, button = ("Confirm your email", f"Hi {first}, welcome to Tailora. Confirm this is your email "
                                 "address so we can send you order updates and keep your account secure.", "Confirm email")
        note = f"This link works for {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES // 60} hours. If you didn't create a Tailora account, ignore this email."
    else:
        heading, lead, button = ("Reset your password", f"Hi {first}, we received a request to reset your Tailora "
                                 "password.", "Choose a new password")
        note = "This link works once and expires soon. If you didn't ask for this, ignore this email; your password stays the same."
    return f"""<!doctype html><html><body style="margin:0;background:#faf9f5;font-family:Arial,Helvetica,sans-serif;color:#1c2230">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#faf9f5;padding:24px 12px"><tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:#ffffff;border:1px solid #ddd6c6;border-radius:12px">
<tr><td style="padding:24px 24px 0;font-family:Georgia,serif;font-size:22px;color:#8d7040">Tailora</td></tr>
<tr><td style="padding:16px 24px 0;font-size:20px;font-weight:bold">{heading}</td></tr>
<tr><td style="padding:8px 24px 0;font-size:15px;line-height:1.5;color:#3a3f4b">{lead}</td></tr>
<tr><td style="padding:20px 24px"><a href="{safe_url}" style="display:inline-block;background:#1c2230;color:#ffffff;text-decoration:none;padding:12px 20px;border-radius:8px;font-size:15px;font-weight:bold">{button}</a></td></tr>
<tr><td style="padding:0 24px;font-size:13px;line-height:1.5;color:#565a66">If the button doesn't work, copy this link into your browser:<br><a href="{safe_url}" style="color:#8d7040;word-break:break-all">{safe_url}</a></td></tr>
<tr><td style="padding:16px 24px 24px;font-size:12px;line-height:1.5;color:#565a66">{escape(note)}</td></tr>
</table></td></tr></table></body></html>"""


class AuthEmailOutboxService:
    def __init__(self, db: Session):
        self.db = db

    def enqueue(self, *, user: User, kind: str, token: str | None = None) -> Notification | None:
        """Queue one email. A verification email already waiting for this person is reused."""
        event, subject, _ = KINDS[kind]
        if kind == "verification":
            pending = (self.db.query(Notification)
                       .filter(Notification.recipient_user_id == user.id, Notification.event_type == event,
                               Notification.channel == "email", Notification.sent_at.is_(None))
                       .first())
            if pending is not None:
                # Give a parked or backed-off job a fresh start (the person asked again).
                pending.metadata_json = {}
                return pending
            metadata = {}
        else:
            metadata = {"ciphertext": _cipher().encrypt(token.encode()).decode()}
        job = Notification(recipient_user_id=user.id, channel="email", event_type=event,
                           title=subject, body="Authentication email is awaiting dispatch.", metadata_json=metadata)
        self.db.add(job)
        return job

    def _due(self, user_id=None):
        query = (self.db.query(Notification)
                 .filter(Notification.channel == "email", Notification.event_type.in_(EVENTS),
                         Notification.sent_at.is_(None),
                         or_(Notification.metadata_json.is_(None),
                             Notification.metadata_json["parked"].astext.is_(None)),
                         or_(Notification.metadata_json.is_(None),
                             Notification.metadata_json["retry_after"].astext.is_(None),
                             Notification.metadata_json["retry_after"].astext <= _now_iso())))
        if user_id is not None:
            query = query.filter(Notification.recipient_user_id == user_id)
        return query

    def pending_count(self) -> int:
        return self._due().count()

    def last_error(self) -> str | None:
        """The provider's most recent refusal, for the admin's email card."""
        job = (self.db.query(Notification)
               .filter(Notification.channel == "email", Notification.event_type.in_(EVENTS),
                       Notification.sent_at.is_(None), Notification.metadata_json["last_error"].astext.is_not(None))
               .order_by(Notification.updated_at.desc()).first())
        return (job.metadata_json or {}).get("last_error") if job else None

    def process_one(self, *, user_id=None) -> bool:
        """Send the oldest due email. Returns False when nothing is due. A provider failure
        backs that job off and returns True, so the next job still gets its turn."""
        job = (self._due(user_id).order_by(Notification.created_at, Notification.id)
               .with_for_update(skip_locked=True).populate_existing().first())
        if job is None:
            return False
        user = self.db.get(User, job.recipient_user_id)
        kind = next(key for key, data in KINDS.items() if data[0] == job.event_type)
        if not user or not user.is_active or (kind == "verification" and user.is_email_verified):
            job.sent_at, job.metadata_json = utcnow(), None  # nothing to send any more
            self.db.commit()
            return True

        _, subject, path = KINDS[kind]
        if kind == "verification":
            from app.core.security import create_email_verification_token
            token = create_email_verification_token(str(user.id))
        else:
            token = _cipher().decrypt(job.metadata_json["ciphertext"].encode()).decode()
        url = f"{settings.FRONTEND_URL.rstrip('/')}/{path}?token={quote(token, safe='')}"
        from app.core.exceptions import ExternalProviderError
        from app.integrations.notifications.email import send_email
        try:
            send_email(to_address=user.email, subject=subject, html_body=render(kind, name=user.full_name, url=url),
                       idempotency_key=f"auth-email-{job.id}-{(job.metadata_json or {}).get('attempts', 0)}")
        except ExternalProviderError as exc:
            metadata = dict(job.metadata_json or {})
            attempts = int(metadata.get("attempts", 0)) + 1
            metadata.update(attempts=attempts, last_error=str(exc)[:200],
                            retry_after=(utcnow() + timedelta(minutes=min(2 ** attempts, 360))).strftime("%Y-%m-%dT%H:%M:%S"))
            if attempts >= MAX_ATTEMPTS:
                metadata["parked"] = True  # stops retrying; a resend request revives it
            job.metadata_json = metadata
            self.db.commit()
            logger.warning("auth_email_deferred", extra={"job_id": str(job.id), "attempts": attempts,
                                                         "reason": metadata["last_error"]})
            raise
        job.sent_at, job.metadata_json = utcnow(), None
        self.db.commit()
        return True

    def send_pending(self, *, user_id=None, limit: int | None = 20) -> dict:
        """Send due emails now; `limit=None` keeps going until nothing is due. Stops early if
        the provider is failing for everyone."""
        from app.core.exceptions import ExternalProviderError
        sent = failed = 0
        for _ in range(MAX_BATCH if limit is None else max(1, limit)):
            try:
                if not self.process_one(user_id=user_id):
                    break
                sent += 1
            except ExternalProviderError:
                self.db.rollback()
                failed += 1
                if failed >= 3 and sent == 0:
                    break  # provider not configured or down; the drain retries later
        return {"sent": sent, "failed": failed}

    def queue_for_unverified(self, *, limit: int = 5000) -> int:
        """Queue a fresh verification email for every active account that hasn't confirmed yet."""
        users = (self.db.query(User).filter(User.is_active.is_(True), User.is_email_verified.is_(False),
                                            User.role != "admin")
                 .order_by(User.created_at).limit(limit).all())
        for user in users:
            self.enqueue(user=user, kind="verification")
        self.db.commit()
        return len(users)


def send_in_background(user_id=None, limit: int | None = 20) -> None:
    """Run after the response is sent (FastAPI BackgroundTasks), in its own session."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        AuthEmailOutboxService(db).send_pending(user_id=user_id, limit=limit)
    except Exception:
        db.rollback()
        logger.exception("auth_email_background_send_failed")
    finally:
        db.close()
