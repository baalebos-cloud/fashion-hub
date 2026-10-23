"""Real read endpoints for public professional reviews and private buyer history."""
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundError
from app.models.professional import Professional
from app.models.user import User
from app.schemas.review import ReviewResponse
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("", response_model=list[ReviewResponse])
def list_professional_reviews(professional_id: uuid.UUID, db: Session = Depends(get_db)):
    professional = db.get(Professional, professional_id)
    if not professional:
        raise NotFoundError("Professional not found.")
    return ReviewService(db).list_reviews(reviewee_user_id=professional.user_id)


@router.get("/mine", response_model=list[ReviewResponse])
def my_reviews(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ReviewService(db).list_reviews(reviewer_user_id=current_user.id)
