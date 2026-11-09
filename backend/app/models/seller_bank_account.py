"""Where a seller's payouts go: one Nigerian bank account per seller, checked with Paystack.

The account number is encrypted at rest (IDENTITY_ENCRYPTION_KEY); only the last four digits are
shown. `name_matches` says whether the bank's account name matches the seller's verified NIN name or
business name; automatic payouts only go to matching accounts.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class SellerBankAccount(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "seller_bank_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                                               unique=True, nullable=False, index=True)
    bank_code: Mapped[str] = mapped_column(String(16), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(128), nullable=False)
    account_number_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    account_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_matches: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recipient_code: Mapped[str] = mapped_column(String(64), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(nullable=False)
