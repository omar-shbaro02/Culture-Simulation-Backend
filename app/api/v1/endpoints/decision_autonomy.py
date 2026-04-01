from fastapi import APIRouter
from app.services.advisory_engine import generate_dimension_advice

# THIS NAME MUST BE router
router = APIRouter(prefix="/advisory", tags=["Advisory"])


@router.get("/decision-autonomy/{score}")
def decision_autonomy(score: int):
    return generate_dimension_advice("decision-autonomy", score)
