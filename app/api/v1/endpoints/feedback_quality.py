from fastapi import APIRouter
from app.services.advisory_engine import generate_dimension_advice

# THIS NAME MUST BE router
router = APIRouter(prefix="/advisory", tags=["Advisory"])


@router.get("/feedback-quality/{score}")
def feedback_quality(score: int):
    return generate_dimension_advice("feedback-quality", score)
