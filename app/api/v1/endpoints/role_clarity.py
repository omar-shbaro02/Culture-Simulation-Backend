from fastapi import APIRouter
from app.services.advisory_engine import generate_dimension_advice

# THIS NAME MUST BE router
router = APIRouter(prefix="/advisory", tags=["Advisory"])


@router.get("/role-clarity/{score}")
def role_clarity(score: int):
    return generate_dimension_advice("role-clarity", score)
