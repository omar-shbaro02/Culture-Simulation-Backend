from fastapi import APIRouter
from pydantic import BaseModel
from app.services.dimension_state_manager import (
    get_dimension_state,
    apply_delta,
    reset_all_dimension_states,
)

router = APIRouter(prefix="/dimension", tags=["Dimension State"])

class DeltaInput(BaseModel):
    delta: int

@router.get("/{slug}")
def read_dimension(slug: str):
    return get_dimension_state(slug)

@router.post("/{slug}/update")
def update_dimension(slug: str, data: DeltaInput):
    return apply_delta(slug, data.delta)


@router.post("/reset-all")
def reset_all_dimensions():
    return reset_all_dimension_states()
