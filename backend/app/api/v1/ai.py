"""Authenticated opt-in Vertex AI drafts. No provider credentials reach browser."""
from collections.abc import AsyncIterator
import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.vertex_ai import CustomerMeasurementSchema, TailoringSpecSchema
from app.services.vertex_service import VertexUnavailable, get_vertex_service
from app.integrations.ai.llm_client import LLMClient, ChatMessage

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


class TailoringSpecRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=6000)


class AdvisorMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class AdvisorRequest(BaseModel):
    messages: list[AdvisorMessage] = Field(min_length=1, max_length=25)


def require_vertex_configured():
    if not settings.VERTEX_AI_ENABLED or not settings.GCP_PROJECT_ID:
        raise HTTPException(status_code=503, detail="AI features are not configured.")
    return get_vertex_service()


@router.get("/health-check")
def ai_health_check():
    return {"module": "AI Assistant", "status": "configured" if settings.VERTEX_AI_ENABLED and settings.GCP_PROJECT_ID else "disabled"}


@router.post("/measurements/extract", response_model=CustomerMeasurementSchema)
async def extract_measurements(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    vertex=Depends(require_vertex_configured),
):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Upload JPEG, PNG or WebP only.")
    data = await file.read(5_000_001)
    if not 0 < len(data) <= 5_000_000:
        raise HTTPException(413, "Image exceeds 5 MB or is empty.")
    # Model draft only: no automatic saving into customer measurements.
    try:
        return vertex.extract_measurements_from_image(data)
    except VertexUnavailable as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@router.post("/spec/estimate", response_model=TailoringSpecSchema)
def estimate_materials(
    payload: TailoringSpecRequest,
    user: User = Depends(get_current_user),
    vertex=Depends(require_vertex_configured),
):
    try:
        return vertex.generate_tailoring_spec(payload.prompt)
    except VertexUnavailable as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@router.post("/advisor/stream")
async def stream_advisor(
    payload: AdvisorRequest,
    user: User = Depends(get_current_user),
):
    async def events() -> AsyncIterator[str]:
        try:
            if settings.VERTEX_AI_ENABLED:
                try:
                    vertex = get_vertex_service()
                    async for chunk in vertex.stream_fashion_advisor([m.model_dump() for m in payload.messages]):
                        yield "data: " + json.dumps({"delta": chunk}) + "\n\n"
                    yield "event: done\ndata: {}\n\n"
                    return
                except Exception:
                    if not (settings.AI_FALLBACK_PROVIDER == "groq" and settings.GROQ_API_KEY):
                        raise
            if settings.AI_FALLBACK_PROVIDER == "groq" and settings.GROQ_API_KEY:
                import asyncio
                completion = await asyncio.to_thread(
                    LLMClient()._complete_groq,
                    [ChatMessage(role=m.role, content=m.content) for m in payload.messages],
                    512,
                )
                yield "data: " + json.dumps({"delta": completion.content}) + "\n\n"
            else:
                raise VertexUnavailable("No AI advisor provider is configured.")
        except Exception:
            # Do not leak cloud credentials or upstream provider exception details.
            yield "event: error\ndata: " + json.dumps({"message": "Advisor temporarily unavailable."}) + "\n\n"
        yield "event: done\ndata: {}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
