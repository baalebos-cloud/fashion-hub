"""
/measurements

Measurement profile and individual field CRUD for customers, used when
placing a customer order (see CreateCustomerOrderRequest.measurement_profile_id).

STATUS: scaffold stub. Wire in a MeasurementService/Repository as this
module is implemented; follow the pattern established in auth.py / orders.py.
"""
from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/measurements", tags=["Measurements"])


@router.get("/health-check")
def module_placeholder():
    return {"module": "Measurements", "status": "not yet implemented"}
