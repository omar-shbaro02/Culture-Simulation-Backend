from pydantic import BaseModel
from typing import List, Dict


# ----------- REQUEST MODEL (FROM FRONTEND) -----------

class NLPRequest(BaseModel):
    problem: str


# ----------- RESPONSE MODELS (TO FRONTEND) -----------

class SeverityHints(BaseModel):
    emotional_intensity: str  # low | moderate | high
    scope: str                # individual | team | org
    urgency: str              # low | medium | high


class NLPNormalizationResult(BaseModel):
    clean_problem_statement: str
    signals: List[str]
    taxonomy: Dict[str, List[str]]
    severity_hints: SeverityHints
