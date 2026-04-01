
from fastapi import APIRouter
from app.services.advisory_engine import generate_leadership_trust_advice

router = APIRouter()

@router.get("/advisory/leadership-trust/{score}")
def leadership_trust(score: int):
    return generate_leadership_trust_advice(score)
