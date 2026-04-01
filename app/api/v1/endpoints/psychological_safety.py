from fastapi import APIRouter
from app.services.advisory_engine import generate_dimension_advice

# THIS NAME MUST BE router
router = APIRouter(prefix="/advisory", tags=["Advisory"])


@router.get("/psychological-safety/{score}")
def psychological_safety(score: int):
    return generate_dimension_advice("psychological-safety", score)
