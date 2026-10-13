from fastapi import APIRouter, Depends

from app.api.deps import get_executor
from app.services import cities as svc

router = APIRouter(prefix="/api/cities", tags=["cities"])


@router.get("")
def list_cities(db=Depends(get_executor)):
    """All cities in the historical database, with coordinates and date coverage."""
    return {"items": svc.list_cities(db)}
