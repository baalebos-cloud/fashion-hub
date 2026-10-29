"""Authenticated object uploads. ID/KYB documents never receive public URLs."""
from typing import Literal
from uuid import UUID
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.stored_media import StoredMedia
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from app.core.dependencies import get_current_user
from app.core.permissions import Role
from app.models.user import User
from app.services.media_service import save_media

router = APIRouter(prefix="/media", tags=["Media"])


@router.post("/upload", status_code=201)
async def upload_media(
    purpose: Literal["product", "kyc", "kyb", "delivery"],
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    if purpose == "product" and user.role != Role.VENDOR.value:
        raise HTTPException(status_code=403, detail="Material Vendor account required.")
    if purpose == "kyb" and user.role not in {Role.VENDOR.value, Role.TAILOR.value, Role.DESIGNER.value}:
        raise HTTPException(status_code=403, detail="Business account required.")
    return await save_media(file, owner_id=user.id, purpose=purpose, public=purpose == "product")


@router.get("/files/{file_id}")
def view_media(file_id: UUID, db: Session = Depends(get_db)):
    """Only catalog images can be retrieved anonymously. KYC and KYB stay private."""
    media = db.get(StoredMedia, file_id)
    if media is None or not media.is_public or not media.storage_key.startswith("product/"):
        raise HTTPException(status_code=404, detail="Media not found.")
    return Response(media.content, media_type=media.content_type,
                    headers={"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"})


@router.get("/private/{file_id}")
def view_private_media(file_id: UUID, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """Authenticated document retrieval for its uploader or a platform admin."""
    media = db.get(StoredMedia, file_id)
    if media is None or (media.owner_user_id != user.id and user.role != Role.ADMIN.value):
        raise HTTPException(status_code=404, detail="Media not found.")
    return Response(media.content, media_type=media.content_type,
                    headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
