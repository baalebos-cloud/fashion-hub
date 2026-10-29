"""Strictly offline contract checks: no credentials or model calls."""
import pytest
from pydantic import ValidationError
from app.services.vertex_service import MeasurementEstimate, TailoringSpec, VertexAIService


def test_measurement_rejects_invalid_values():
    with pytest.raises(ValidationError):
        MeasurementEstimate(bust=-1, unit="inches", confidence=0.9)


def test_measurement_requires_confidence():
    with pytest.raises(ValidationError):
        MeasurementEstimate(bust=40, unit="inches")


def test_materials_reject_negative_quantity():
    with pytest.raises(ValidationError):
        TailoringSpec(garment_type="dress", construction_notes="test", estimated_fabric_yards=-1, recommended_materials=[])


def test_client_injection_avoids_credentials():
    fake = object()
    service = VertexAIService(client=fake)
    assert service.client is fake


@pytest.mark.asyncio
async def test_stream_rejects_empty_messages():
    service = VertexAIService(client=object())
    with pytest.raises(ValueError):
        async for _ in service.stream_fashion_advisor([]):
            pass
