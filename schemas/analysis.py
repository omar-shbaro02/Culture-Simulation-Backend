from pydantic import BaseModel
from typing import Any, Dict


class AnalysisResponse(BaseModel):
    stage: str
    nlp_result: Dict[str, Any]
    scoring_result: Dict[str, Any]
    benchmark_result: Dict[str, Any]
    strategy_result: Dict[str, Any]
    simulation_result: Dict[str, Any]
    explanation: Dict[str, Any]
