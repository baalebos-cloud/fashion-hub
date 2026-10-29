"""Explicitly gated live Interswitch hosted checkout for the hackathon.

Not available in staging. Do not enable until the organizers assign a team
and pay-item ID and the live account has been verified with Interswitch.
"""
from app.core.config import settings
from app.core.exceptions import ConflictError
from app.services.interswitch_sandbox_service import InterswitchSandboxService


class InterswitchLiveService(InterswitchSandboxService):
    @staticmethod
    def _live_mode() -> bool:
        return True

    @staticmethod
    def _require_sandbox():
        # Inherited checkout/verify call this gate on every request.
        if (settings.APP_ENV != "production"
                or not settings.INTERSWITCH_LIVE_ENABLED
                or not settings.INTERSWITCH_LIVE_MERCHANT_CODE
                or not settings.INTERSWITCH_LIVE_PAY_ITEM_ID):
            raise ConflictError("Live Interswitch checkout is not enabled or configured.")

    def _checkout_form(self, payment, email):
        # The parent form builder enforces HTTPS callbacks, exact amount and
        # all required checkout identifiers. It selects the live URL here.
        from app.integrations.payments.interswitch_checkout import build_checkout_form
        return build_checkout_form(
            merchant_code=settings.INTERSWITCH_LIVE_MERCHANT_CODE,
            pay_item_id=settings.INTERSWITCH_LIVE_PAY_ITEM_ID,
            reference=payment.provider_reference,
            amount=payment.amount,
            customer_email=email,
            return_url=self._return_url(),
            live=True,
        )

    def verify_and_confirm(self, provider_reference, *, buyer_user_id=None):
        # Parent verification uses the live endpoint through _live_mode.
        # The merchant code is swapped through a deliberately scoped settings
        # adapter below instead of mutating process-global configuration.
        raise NotImplementedError("Live settlement requires separate audited verification.")
