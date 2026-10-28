"""Interswitch checkout return normalizer.

Provider callbacks are *navigation only*: no callback field establishes
payment success. The signed-in buyer must still independently requery.
"""
import re
from urllib.parse import urlencode

from app.core.config import settings

REFERENCE_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")


def redirect_for_interswitch_return(*, txnref: str = "",
                                   txn_ref: str = "",
                                   transactionreference: str = "",
                                   reference: str = "") -> str:
    candidates = [v for v in (txnref, txn_ref, transactionreference, reference)\n                  if isinstance(v, str) and v]
    params = {"provider": "interswitch"}
    # Never trust conflicting references from an untrusted provider/browser callback.
    if len(set(candidates)) == 1 and REFERENCE_PATTERN.fullmatch(candidates[0]):
        params["reference"] = candidates[0]
    return f"{settings.FRONTEND_URL.rstrip('/')}/app/customer/payment/success?{urlencode(params)}"
