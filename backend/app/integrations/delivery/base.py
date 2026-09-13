"""
DeliveryProvider interface. `internal` is the default/first-class provider
(the platform's own delivery-partner network, matched via delivery_service);
external couriers can be added later without touching order/delivery
business logic.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class CreateDeliveryResult:
    provider_reference: str
    estimated_fee: float
    raw_response: dict


@dataclass
class DeliveryStatusResult:
    status: str
    latitude: Optional[float]
    longitude: Optional[float]
    eta_minutes: Optional[int]
    raw_response: dict


class DeliveryProvider(ABC):
    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def get_delivery_status(self, provider_reference: str) -> DeliveryStatusResult:
        raise NotImplementedError

    @abstractmethod
    def cancel_delivery(self, provider_reference: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def verify_webhook_signature(self, *, payload: bytes, signature_header: str) -> bool:
        raise NotImplementedError
