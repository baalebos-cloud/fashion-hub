"""Google Cloud Vertex AI generation, injected and disabled unless configured.

Uses Google's supported Gen AI SDK with Vertex AI authentication (ADC).
No photographed body dimensions are inferred as tape-measured facts.
"""
from collections.abc import AsyncGenerator
from functools import lru_cache
import json

from app.core.config import settings
from app.schemas.vertex_ai import CustomerMeasurementSchema, TailoringSpecSchema


class VertexUnavailable(RuntimeError):
    pass


class VertexAIService:
    def __init__(self, client=None, model: str | None = None):
        self.model = model or settings.VERTEX_AI_MODEL_NAME
        self.client = client

    def _client(self):
        if self.client is not None:
            return self.client
        if not settings.GCP_PROJECT_ID or not settings.GCP_REGION or not settings.VERTEX_AI_ENABLED:
            raise VertexUnavailable("Vertex AI is not configured.")
        try:
            from google import genai
        except ImportError as exc:
            raise VertexUnavailable("Google Gen AI SDK not installed.") from exc
        self.client = genai.Client(vertexai=True, project=settings.GCP_PROJECT_ID,
                                   location=settings.GCP_REGION)
        return self.client

    def _structured(self, schema, contents):
        from google.genai import types
        response = self._client().models.generate_content(
            model=self.model, contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=schema,
                temperature=0.2,
            ),
        )
        if not response.text:
            raise VertexUnavailable("Vertex AI returned no structured result.")
        return schema.model_validate_json(response.text)

    @staticmethod
    def _image_mime(image_bytes: bytes) -> str:
        if image_bytes.startswith(bytes.fromhex("ffd8ff")):
            return "image/jpeg"
        if image_bytes.startswith(bytes.fromhex("89504e470d0a1a0a")):
            return "image/png"
        if len(image_bytes) > 12 and image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
            return "image/webp"
        raise ValueError("Invalid JPEG, PNG or WebP image data.")

    def extract_measurements_from_image(self, image_bytes: bytes) -> CustomerMeasurementSchema:
        if not 0 < len(image_bytes) <= 5_000_000:
            raise ValueError("Image must be between 1 byte and 5 MB.")
        from google.genai import types
        result = self._structured(
            CustomerMeasurementSchema,
            [types.Part.from_text(text=(
                "Describe the outfit and give only measurements explicitly legible on a ruler "
                "or tape measure. Do not infer body size from a person's appearance. "
                "Use null for dimensions without readable scale. Explicitly require "
                "manual confirmation; do not assign confidence above 0.5 to photo-only estimates."
            )), types.Part.from_bytes(data=image_bytes, mime_type=self._image_mime(image_bytes))],
        )
        return result.model_copy(update={"requires_manual_measurement": True})

    def generate_tailoring_spec(self, prompt: str, reference_images: list[bytes] | None = None) -> TailoringSpecSchema:
        if not prompt.strip() or len(prompt) > 6000:
            raise ValueError("Design description must contain 1-6000 characters.")
        imgs = reference_images or []
        if len(imgs) > 4 or any(len(x) > 5_000_000 for x in imgs):
            raise ValueError("Limit design references to four images of at most 5 MB.")
        from google.genai import types
        parts = [types.Part.from_text(text=(
            "Draft a tailoring bill of materials. Estimate yardage conservatively and "
            "state assumptions. Tailor must confirm before pricing, ordering or payment. " + prompt
        ))] + [types.Part.from_bytes(data=image, mime_type=self._image_mime(image)) for image in imgs]
        return self._structured(TailoringSpecSchema, parts)

    async def stream_fashion_advisor(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        if not messages or len(messages) > 25:
            raise ValueError("Provide between 1 and 25 messages.")
        safe = []
        for message in messages:
            if message.get("role") not in {"user", "assistant"} or not isinstance(message.get("content"), str):
                raise ValueError("Messages require a role and text.")
            if len(message["content"]) > 4000:
                raise ValueError("Message exceeds maximum size.")
            safe.append(message["content"])
        stream = await self._client().aio.models.generate_content_stream(
            model=self.model, contents="\n".join(safe),
            config={"system_instruction": "Advise on clothing and materials, not payments or verified body measurements."},
        )
        async for chunk in stream:
            if chunk.text:
                yield chunk.text


@lru_cache(maxsize=1)
def get_vertex_service():
    return VertexAIService()
