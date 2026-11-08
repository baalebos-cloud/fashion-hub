"""
/devices

Phones registered for push notifications from the iPhone and Android apps. Registering a
token that another account used moves it to the person signed in now, so a shared or
handed-down phone never notifies the previous owner.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.core.timezone import utcnow
from app.models.device_token import DeviceToken
from app.models.user import User

router = APIRouter(prefix="/devices", tags=["Devices"])


class RegisterDevice(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    platform: Literal["ios", "android"]
    token: str = Field(min_length=16, max_length=512, pattern=r"^[A-Za-z0-9:_\-.]+$")


@router.post("", status_code=204)
@limiter.limit("20/hour")
def register_device(request: Request, payload: RegisterDevice, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    device = db.query(DeviceToken).filter(DeviceToken.token == payload.token).with_for_update().first()
    if device is None:
        db.add(DeviceToken(user_id=user.id, platform=payload.platform, token=payload.token, last_seen_at=utcnow()))
    else:
        device.user_id, device.platform, device.last_seen_at = user.id, payload.platform, utcnow()
    db.commit()


@router.delete("/{token}", status_code=204)
def unregister_device(token: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Only your own registration; unknown tokens are fine (sign-out is best effort).
    db.query(DeviceToken).filter(DeviceToken.token == token, DeviceToken.user_id == user.id).delete()
    db.commit()
