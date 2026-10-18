import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import PaginationParams
from app.core.permissions import Role, require_roles
from app.models.user import User
from app.schemas.inventory import RestockRequest, InventoryResponse
from app.services.inventory_service import InventoryService

router = APIRouter(prefix='/vendor-inventory', tags=['Vendor Inventory'])


@router.get('', response_model=list[InventoryResponse])
def inventory(pagination: PaginationParams = Depends(), user: User = Depends(require_roles(Role.VENDOR)), db: Session = Depends(get_db)):
    return InventoryService(db).list(user.id, offset=pagination.offset, limit=pagination.page_size)


@router.post('/{variant_id}/restock', response_model=InventoryResponse)
def restock(variant_id: uuid.UUID, payload: RestockRequest, user: User = Depends(require_roles(Role.VENDOR)), db: Session = Depends(get_db)):
    return InventoryService(db).restock(variant_id, owner_user_id=user.id, quantity_to_add=payload.quantity_to_add)
