"""Role-scoped dashboard metrics from the actual order database."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return DashboardService(db).summary(user)
