"""Paystack Transfers: paying sellers from the Paystack balance to their bank accounts.

Docs: https://paystack.com/docs/transfers/single-transfers/
Every call raises ExternalProviderError with a short reason an admin can act on. Account numbers,
names and keys are never logged.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError

logger = logging.getLogger(__name__)
BASE = "https://api.paystack.co"


class TransferOutcomeUnknown(ExternalProviderError):
    """No clear answer (connection dropped, timeout, Paystack error 5xx): the transfer may or may not
    have gone through. Never treat this as failed; check the reference with Paystack first."""


class TransferNotFound(ExternalProviderError):
    """Paystack has no transfer with this reference: it was never created."""


@dataclass
class TransferResult:
    status: str  # pending | success | failed | reversed | otp (Paystack's words)
    transfer_code: str | None
    reason: str | None = None


def _headers() -> dict:
    if not settings.PAYMENT_SECRET_KEY:
        raise ExternalProviderError("Paystack isn't set up (PAYMENT_SECRET_KEY is missing).")
    return {"Authorization": f"Bearer {settings.PAYMENT_SECRET_KEY}", "Content-Type": "application/json"}


def _call(method: str, path: str, *, client=None, **kwargs) -> dict:
    http = client or httpx
    try:
        response = getattr(http, method)(f"{BASE}{path}", headers=_headers(), timeout=20.0, **kwargs)
    except httpx.HTTPError:
        logger.warning("paystack_transfer_request_failed path=%s", path.split("?")[0])
        raise TransferOutcomeUnknown("Paystack didn't answer in time.") from None
    try:
        body = response.json()
    except ValueError:
        body = {}
    if response.status_code >= 500:
        logger.warning("paystack_transfer_error path=%s status=%d", path.split("?")[0], response.status_code)
        raise TransferOutcomeUnknown(f"Paystack error (HTTP {response.status_code}).")
    if response.status_code == 404:
        raise TransferNotFound("Paystack has no record of it.")
    if response.status_code >= 400 or body.get("status") is False:
        message = str(body.get("message") or f"HTTP {response.status_code}")[:200]
        logger.warning("paystack_transfer_error path=%s status=%d", path.split("?")[0], response.status_code)
        raise ExternalProviderError(f"Paystack: {message}")
    return body.get("data") or {}


def list_banks(*, client=None) -> list[dict]:
    data = _call("get", "/bank?country=nigeria&currency=NGN&perPage=200", client=client)
    banks = data if isinstance(data, list) else []
    return sorted(({"code": str(b["code"]), "name": str(b["name"])} for b in banks
                   if b.get("code") and b.get("name") and b.get("active", True)), key=lambda b: b["name"])


def resolve_account(account_number: str, bank_code: str, *, client=None) -> str:
    """The account holder's name as the bank has it."""
    data = _call("get", f"/bank/resolve?account_number={account_number}&bank_code={bank_code}", client=client)
    name = str(data.get("account_name") or "").strip()
    if not name:
        raise ExternalProviderError("The bank didn't return a name for that account.")
    return name[:255]


def create_recipient(*, name: str, account_number: str, bank_code: str, client=None) -> str:
    data = _call("post", "/transferrecipient", client=client, json={
        "type": "nuban", "name": name, "account_number": account_number, "bank_code": bank_code, "currency": "NGN"})
    code = data.get("recipient_code")
    if not code:
        raise ExternalProviderError("Paystack didn't return a transfer recipient.")
    return str(code)


def initiate_transfer(*, amount_kobo: int, recipient_code: str, reference: str, reason: str,
                      client=None) -> TransferResult:
    """`reference` makes this safe to repeat: Paystack refuses a second transfer with the same one."""
    data = _call("post", "/transfer", client=client, json={
        "source": "balance", "amount": amount_kobo, "recipient": recipient_code, "reference": reference,
        "reason": reason[:100], "currency": "NGN"})
    return TransferResult(status=str(data.get("status") or "pending"), transfer_code=data.get("transfer_code"))


def verify_transfer(reference: str, *, client=None) -> TransferResult:
    data = _call("get", f"/transfer/verify/{reference}", client=client)
    return TransferResult(status=str(data.get("status") or "pending"), transfer_code=data.get("transfer_code"),
                          reason=(str(data.get("reason") or "")[:200] or None))
