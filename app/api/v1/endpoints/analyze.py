from fastapi import APIRouter
from pydantic import BaseModel

import app.state as state
from app.services.dimension_state_manager import apply_absolute_score
from app.services.pipeline import run_pipeline

router = APIRouter(prefix="/analyze")


class AnalyzeRequest(BaseModel):
    problem_text: str


@router.post("")
async def analyze(payload: AnalyzeRequest):
    """
    Runs culture analysis and stores it in shared state.
    Also updates KPI states so Insight cards reflect latest study output.
    """
    result = await run_pipeline(payload.problem_text)
    severity_hints = result.get("nlp_result", {}).get("severity_hints", {})
    scope = severity_hints.get("scope", "team")

    dimension_state_updates = {}
    dimension_scores = result.get("scoring_result", {}).get("dimension_scores", {})
    for slug, score_obj in dimension_scores.items():
        if not isinstance(score_obj, dict):
            continue
        score = int(score_obj.get("score_0_100", 50))
        drivers = score_obj.get("drivers", [])
        top_driver = drivers[0] if isinstance(drivers, list) and drivers else "signal mix"
        reason = (
            f"Explore study recalibration ({scope} scope). "
            f"Primary driver: {top_driver}."
        )
        dimension_state_updates[slug] = apply_absolute_score(
            slug,
            score,
            source="explore_study",
            scope=scope,
            reason=reason,
        )

    result["dimension_state_updates"] = dimension_state_updates
    state.LAST_ANALYSIS = result
    return result
