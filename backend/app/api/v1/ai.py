"""Authenticated, opt-in AI advisory routes. AI never confirms or saves measurements."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.vertex_service import get_vertex_service

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


class SpecRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)


class AdvisorMessage(BaseModel):
    role: str
    content: str = Field(max_length=4000)


class AdvisorRequest(BaseModel):
    messages: list[AdvisorMessage] = Field(min_length=1, max_length=30)


def enabled():
    if not settings.VERTEX_AI_ENABLED or not settings.GCP_PROJECT_ID:
        raise HTTPException(status_code=503, detail="Vertex AI is not configured")
    return get_vertex_service()


@router.get("/health-check")
def health_check():
    return {"module": "AI Assistant", "enabled": bool(settings.VERTEX_AI_ENABLED and settings.GCP_PROJECT_ID)}


@router.post("/measurements/extract")
async def extract_measurements(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(415, "Only JPEG/PNG photos are supported")
    data = await file.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "Maximum photo size is 10 MiB")
    try:
        estimate = enabled().extract_measurements_from_image(data)
        return {"estimate": estimate.model_dump(), "requires_manual_confirmation": True}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/spec/estimate")
def estimate_spec(payload: SpecRequest, user: User = Depends(get_current_user)):
    return enabled().generate_tailoring_spec(payload.prompt)


@router.post("/advisor/stream")
async def stream_advisor(payload: AdvisorRequest, user: User = Depends(get_current_user)):
    service = enabled()
    async def events():
        import json
        async for chunk in service.stream_fashion_advisor([msg.model_dump() for msg in payload.messages]):
            yield "data: " + json.dumps({"text": chunk}) + "\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(events(), media_type="text/event-stream")
