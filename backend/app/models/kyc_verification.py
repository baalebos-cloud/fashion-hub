from datetime import datetime
from sqlalchemy.orm import Mapped
from typing import Any
"""
Individual (KYC) verification for customers/professionals/delivery
partners acting as natural persons.

NIN (Nigeria's National Identity Number) is COMPULSORY for every
professional, vendor business-owner, and delivery partner -- see
docs/nin-verification.md and kyc_service.py::submit. `id_type` is fixed to
"nin" for this flow (kept as a free field for a future non-Nigerian market
where a passport/driver's license might be the primary document instead).
"""
import uuid
from sqlalchemy import Boolean, Date, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class KYCVerification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "kyc_verifications"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    id_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # nin, passport, drivers_license

    # The NIN itself is sensitive PII: never returned in any API response
    # (see schemas/kyc.py::KYCStatusResponse, which deliberately omits it)
    # and should be encrypted at the database/column level in a production
    # deployment (e.g. pgcrypto or application-level envelope encryption --
    # not implemented in this scaffold; id_number_encrypted is a plain
    # column here as a placeholder for that encryption layer).
    id_number_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Populated FROM the NIN lookup response (see integrations/kyc/nin_provider.py),
    # not from what the person typed into a form -- this is what makes the
    # verification meaningful: the government record's name/DOB/gender are
    # compared against the profile the person is registering, not trusted
    # blindly from either source alone.
    nin_verified_full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nin_verified_date_of_birth: Mapped[Date | None] = mapped_column(Date, nullable=True)
    nin_verified_gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # True only when the NIN provider's name matches the account's
    # full_name closely enough (see NINVerificationService) -- surfaced to
    # admins reviewing the submission, not auto-approved on a match alone.
    identity_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
