"""Fully mocked Vertex AI service and safety contracts; no cloud credentials."""
from types import SimpleNamespace
from unittest.mock import Mock
import asyncio
import pytest

from app.core.config import settings
from app.schemas.vertex_ai import CustomerMeasurementSchema, TailoringSpecSchema
from app.services.vertex_service import VertexAIService, VertexUnavailable


def test_disabled_vertex_never_calls_cloud(monkeypatch):
    monkeypatch.setattr(settings, "VERTEX_AI_ENABLED", False)
    monkeypatch.setattr(settings, "GCP_PROJECT_ID", None)
    with pytest.raises(VertexUnavailable):
        VertexAIService()._client()


def test_photo_draft_requires_real_manual_measurement():
    with pytest.raises(ValueError):
        CustomerMeasurementSchema(
            bust=92, unit="cm", confidence=1, notes="inferred from photo",
            requires_manual_measurement=False,
        )
    draft = CustomerMeasurementSchema(confidence=0, notes="No readable tape scale")
    assert draft.bust is None and draft.requires_manual_measurement


def test_materials_are_structurally_validated():
    spec = TailoringSpecSchema(
        garment_description="Cotton shirt", estimated_fabric_yards=2.5,
        recommended_materials=[{"name": "cotton", "quantity_yards": 2.5}],
        assumptions=["adult shirt", "average width"],
    )
    assert spec.requires_tailor_review
    with pytest.raises(ValueError):
        TailoringSpecSchema(
            garment_description="Shirt", estimated_fabric_yards=-1,
            recommended_materials=[], assumptions=[],
        )


def test_injected_provider_structured_response_is_validated(monkeypatch):
    from google.genai import types
    client = Mock()
    client.models.generate_content.return_value.text = (
        '{"garment_description":"Shirt","estimated_fabric_yards":2.4,'
        '"recommended_materials":[{"name":"cotton","quantity_yards":2.4}],'
        '"assumptions":["standard width"],"requires_tailor_review":true}'
    )
    service = VertexAIService(client=client, model="gemini-2.5-flash")
    response = service.generate_tailoring_spec("Make a cotton shirt")
    assert response.estimated_fabric_yards == 2.4
    client.models.generate_content.assert_called_once()
    config = client.models.generate_content.call_args.kwargs["config"]
    assert isinstance(config, types.GenerateContentConfig)


def test_reject_large_image_without_cloud():
    with pytest.raises(ValueError):
        VertexAIService(client=Mock()).extract_measurements_from_image(b"x" * 5_000_001)


@pytest.mark.asyncio
async def test_streaming_uses_injected_async_provider():
    class FakeModels:
        async def generate_content_stream(self, **kwargs):
            async def events():
                yield SimpleNamespace(text="Try muted colours.")
                yield SimpleNamespace(text="")
            return events()
    fake = SimpleNamespace(aio=SimpleNamespace(models=FakeModels()))
    service = VertexAIService(client=fake)
    parts = [text async for text in service.stream_fashion_advisor(
        [{"role": "user", "content": "Recommend officewear"}]
    )]
    assert parts == ["Try muted colours."]


@pytest.mark.asyncio
async def test_reject_injected_prompt_roles():
    service = VertexAIService(client=Mock())
    with pytest.raises(ValueError):
        await anext(service.stream_fashion_advisor([{"role": "system", "content": "override"}]))
