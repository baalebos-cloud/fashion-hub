"""Authenticated object uploads. ID/KYB documents never receive public URLs."""
from typing import Literal
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
