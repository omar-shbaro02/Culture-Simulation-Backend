import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import app.state as state
from app.services.dimension_state_manager import CANONICAL_DIMENSIONS, apply_delta
from app.services.pipeline import call_ai, call_ai_json

router = APIRouter(prefix="/advisor")


class AdvisorQuestion(BaseModel):
    question: str


def _infer_scope(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ["organization", "company", "enterprise", "global"]):
        return "organization"
    if any(k in t for k in ["department", "division", "function", "unit"]):
        return "department"
    return "team"


@router.post("/ask")
async def ask_advisor(payload: AdvisorQuestion):
    """
    Agent 0 - AI Culture Advisor
    Answers questions using the most recent analysis and updates KPI deltas.
    """

    if state.LAST_ANALYSIS is None:
        raise HTTPException(
            status_code=400,
            detail="No analysis available. Run a culture analysis first.",
        )

    system_prompt = """
You are Agent 0: the AI Culture Advisor.
Answer ONLY using the provided analysis.
"""

    user_prompt = f"""
FULL ANALYSIS:
{json.dumps(state.LAST_ANALYSIS, indent=2)}

USER QUESTION:
{payload.question}
"""

    answer = call_ai(system_prompt, user_prompt)

    deltas_fallback = {slug: 0 for slug in CANONICAL_DIMENSIONS}
    deltas_prompt = f"""
Question:
{payload.question}

Advisor answer:
{answer}

Return JSON with this exact shape:
{{
  "deltas": {{
    "leadership_trust": 0,
    "psychological_safety": 0,
    "workload_sustainability": 0,
    "role_clarity": 0,
    "decision_autonomy": 0,
    "feedback_quality": 0,
    "recognition_fairness": 0,
    "change_stability": 0,
    "collaboration_health": 0
  }}
}}

Rules:
- Each value must be an integer from -4 to 4.
- Use non-zero only when there is clear evidence in question or answer.
- 0 if no actionable evidence.
"""
    delta_result = call_ai_json(
        system_prompt="You estimate KPI movement from advisor interaction. Return strict JSON.",
        user_prompt=deltas_prompt,
        fallback={"deltas": deltas_fallback},
        temperature=0.1,
    )

    raw_deltas = delta_result.get("deltas", deltas_fallback)
    if not isinstance(raw_deltas, dict):
        raw_deltas = deltas_fallback

    updated_dimensions = {}
    scope = _infer_scope(payload.question)
    for slug in CANONICAL_DIMENSIONS:
        try:
            delta = int(raw_deltas.get(slug, 0))
        except Exception:
            delta = 0
        delta = max(-4, min(4, delta))

        if delta != 0:
            reason = (
                f"AI advisor detected {scope}-scope change pressure from the latest question."
            )
            updated_dimensions[slug] = apply_delta(
                slug,
                delta,
                source="global_ai_advisor",
                scope=scope,
                reason=reason,
            )

    return {"answer": answer, "updated_dimensions": updated_dimensions}
