"""
`InternalDeliveryProvider` matches orders to the platform's own registered
delivery partners (see delivery_partner_service / delivery_request_service)
rather than calling an external courier API. This is the default so the
platform can operate on day one without a third-party delivery contract.
"""
import uuid

from app.integrations.delivery.base import CreateDeliveryResult, DeliveryProvider, DeliveryStatusResult


class InternalDeliveryProvider(DeliveryProvider):
    def create_delivery_request(
        self,
        *,
        order_id: str,
        pickup_address: str,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_address: str,
        dropoff_lat: float,
        dropoff_lng: float,
        package_description: str,
    ) -> CreateDeliveryResult:
        # No external API call: delivery_request_service persists a
        # DeliveryRequest row and broadcasts it to nearby available
        # delivery partners (via notification_service).
        reference = f"internal-{uuid.uuid4()}"
        return CreateDeliveryResult(provider_reference=reference, estimated_fee=0.0, raw_response={})

    def get_delivery_status(self, provider_reference: str) -> DeliveryStatusResult:
        # Status is read from delivery_tracking table directly by
        # tracking_service; this method exists to satisfy the interface for
        # future external providers.
        raise NotImplementedError("InternalDeliveryProvider status is read from the local database.")

    def cancel_delivery(self, provider_reference: str) -> bool:
        return True

    def verify_webhook_signature(self, *, payload: bytes, signature_header: str) -> bool:
        # No external webhooks for the internal provider.
        return True
