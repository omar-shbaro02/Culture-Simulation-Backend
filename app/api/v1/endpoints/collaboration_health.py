from fastapi import APIRouter
from app.services.advisory_engine import generate_dimension_advice

# THIS NAME MUST BE router
router = APIRouter(prefix="/advisory", tags=["Advisory"])


@router.get("/collaboration-health/{score}")
def collaboration_health(score: int):
    return generate_dimension_advice("collaboration-health", score)
