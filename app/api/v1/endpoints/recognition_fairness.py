from fastapi import APIRouter
from app.services.advisory_engine import generate_dimension_advice

# THIS NAME MUST BE router
router = APIRouter(prefix="/advisory", tags=["Advisory"])


@router.get("/recognition-fairness/{score}")
def recognition_fairness(score: int):
    return generate_dimension_advice("recognition-fairness", score)
