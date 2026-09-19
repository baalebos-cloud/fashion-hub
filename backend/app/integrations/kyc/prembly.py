"""
Prembly Identity Pass implementation of NINVerificationProvider.
Docs: https://docs.prembly.com/identitypass/ (NIN verification endpoint) --
verify the exact request/response shape against current Prembly docs
before enabling in production; this reflects their documented pattern as
of this scaffold's writing but identity-verification APIs iterate their
contracts more often than most.

Alternatives with the same shape of API, if you'd rather not use Prembly:
Youverify, QoreID, VerifyMe, Smile ID -- all offer NIN lookup for the
Nigerian market. Swapping providers means writing one new class here and
registering it in this folder's __init__.py; nothing else in the codebase
changes.
"""
from datetime import datetime

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError, NotFoundError
from app.integrations.kyc.nin_provider import NINVerificationProvider, NINVerificationResult

PREMBLY_BASE_URL = "https://api.prembly.com/identitypass/verification/vnin"


class PremblyNINProvider(NINVerificationProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.NIN_API_KEY

    def verify(self, nin_number: str) -> NINVerificationResult:
        try:
            response = httpx.post(
                PREMBLY_BASE_URL,
                headers={"x-api-key": self.api_key or "", "app-id": self.api_key or ""},
                json={"number": nin_number},
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise ExternalProviderError(f"NIN verification request failed: {exc}") from exc

        if not data.get("status") or not data.get("nin_data"):
            raise NotFoundError("No record found for this NIN. Please double-check the number and try again.")

        record = data["nin_data"]
        full_name = " ".join(filter(None, [record.get("firstname"), record.get("middlename"), record.get("surname")]))

        try:
            dob = datetime.strptime(record["birthdate"], "%d-%b-%Y").date()
        except (KeyError, ValueError) as exc:
            raise ExternalProviderError(f"Unexpected date format from NIN provider: {exc}") from exc

        return NINVerificationResult(
            nin=nin_number,
            full_name=full_name,
            date_of_birth=dob,
            gender=record.get("gender", "").upper(),
            photo_base64=record.get("photo"),
        )
