from fastapi import APIRouter
from app.services.advisory_engine import generate_dimension_advice

# THIS NAME MUST BE router
router = APIRouter(prefix="/advisory", tags=["Advisory"])


@router.get("/workload-sustainability/{score}")
def workload_sustainability(score: int):
    return generate_dimension_advice("workload-sustainability", score)
