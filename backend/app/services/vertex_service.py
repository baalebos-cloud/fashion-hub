"""Opt-in Gemini on Vertex AI; no SDK import or GCP request at application startup."""
from functools import lru_cache
from typing import AsyncGenerator, Literal

from pydantic import BaseModel, Field
from app.core.config import settings


class MeasurementEstimate(BaseModel):
    bust: float | None = Field(default=None, gt=0, le=300)
    waist: float | None = Field(default=None, gt=0, le=300)
    hips: float | None = Field(default=None, gt=0, le=300)
    inseam: float | None = Field(default=None, gt=0, le=250)
    unit: Literal["cm", "inches"] = "cm"
    confidence: float = Field(ge=0, le=1)


class MaterialEstimate(BaseModel):
    name: str = Field(min_length=1)
    estimated_yards: float = Field(ge=0, le=100)


class TailoringSpec(BaseModel):
    garment_type: str = Field(min_length=1)
    construction_notes: str
    estimated_fabric_yards: float = Field(ge=0, le=100)
    recommended_materials: list[MaterialEstimate]


class VertexAIService:
    """Inject client for deterministic mocks; use ADC, not a browser-exposed API key."""
    def __init__(self, client=None):
        self.model = settings.VERTEX_AI_MODEL_NAME
        if client is not None:
            self.client = client
            return
        if not settings.GCP_PROJECT_ID:
            raise RuntimeError("Vertex AI is not configured")
        from google import genai
        self.client = genai.Client(vertexai=True, project=settings.GCP_PROJECT_ID, location=settings.GCP_REGION)

    @staticmethod
    def _image(data: bytes):
        if not data or len(data) > 10 * 1024 * 1024:
            raise ValueError("Image must be nonempty and at most 10 MiB")
        from google.genai import types
        mime = "image/png" if data.startswith(b"\x89PNG\r\n\x1a\n") else "image/jpeg" if data.startswith(b"\xff\xd8\xff") else None
        if mime is None:
            raise ValueError("Only JPEG and PNG images are supported")
        return types.Part.from_bytes(data=data, mime_type=mime)

    def extract_measurements_from_image(self, image_bytes: bytes) -> MeasurementEstimate:
        from google.genai import types
        result = self.client.models.generate_content(
            model=self.model,
            contents=["Estimate only observable measurements; return null if uncertain. These guesses require manual confirmation.", self._image(image_bytes)],
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=MeasurementEstimate),
        )
        return MeasurementEstimate.model_validate_json(result.text)

    def generate_tailoring_spec(self, prompt: str, reference_images: list[bytes] | None = None) -> TailoringSpec:
        from google.genai import types
        if not prompt.strip() or len(prompt) > 8000:
            raise ValueError("Prompt must be between 1 and 8000 characters")
        images = reference_images or []
        if len(images) > 5:
            raise ValueError("At most five images")
        result = self.client.models.generate_content(
            model=self.model,
            contents=["Create a provisional tailoring BOM. Do not claim stock is reserved. " + prompt, *[self._image(b) for b in images]],
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=TailoringSpec),
        )
        return TailoringSpec.model_validate_json(result.text)

    async def stream_fashion_advisor(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        from google.genai import types
        if not 1 <= len(messages) <= 30:
            raise ValueError("Expected 1-30 messages")
        contents = []
        for message in messages:
            if message.get("role") not in {"user", "assistant"}:
                raise ValueError("Unsupported message role")
            contents.append(types.Content(
                role="model" if message["role"] == "assistant" else "user",
                parts=[types.Part.from_text(text=str(message.get("content", ""))[:4000])],
            ))
        stream = await self.client.aio.models.generate_content_stream(model=self.model, contents=contents)
        async for chunk in stream:
            if chunk.text:
                yield chunk.text


@lru_cache
def get_vertex_service() -> VertexAIService:
    return VertexAIService()
