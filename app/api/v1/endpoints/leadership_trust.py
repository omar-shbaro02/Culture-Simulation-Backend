from fastapi import APIRouter
from app.services.advisory_engine import (
    generate_leadership_trust_advice,
    generate_dimension_advice,
)

# THIS NAME MUST BE router
router = APIRouter(prefix="/advisory", tags=["Advisory"])

@router.get("/leadership-trust/{score}")
def leadership_trust(score: int):
    return generate_leadership_trust_advice(score)


@router.get("/{dimension}/{score}")
def advisory_by_dimension(dimension: str, score: int):
    return generate_dimension_advice(dimension, score)
