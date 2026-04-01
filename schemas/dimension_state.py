from pydantic import BaseModel
from typing import List

class DimensionState(BaseModel):
    slug: str
    current_score: int
    history: List[int] = []
