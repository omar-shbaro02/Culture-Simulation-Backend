from fastapi import APIRouter
from pydantic import BaseModel

from app.services.ai_culture_agent import generate_reply, infer_kpi_delta
from app.services.dimension_state_manager import apply_delta

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


def _infer_scope(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ["organization", "company", "enterprise", "global"]):
        return "organization"
    if any(k in t for k in ["department", "division", "function", "unit"]):
        return "department"
    return "team"


@router.post("/{dimension}")
async def chat_with_agent(dimension: str, body: ChatRequest):
    normalized_dimension = dimension.replace("-", "_").strip().lower()

    reply = await generate_reply(
        dimension=normalized_dimension,
        user_message=body.message,
    )

    delta = await infer_kpi_delta(
        dimension=normalized_dimension,
        user_message=body.message,
        assistant_reply=reply,
    )
    scope = _infer_scope(body.message)
    reason = (
        f"Dimension advisor interpreted new {scope}-level evidence from the latest chat."
    )
    updated_state = apply_delta(
        normalized_dimension,
        delta,
        source="dimension_advisor_chat",
        scope=scope,
        reason=reason,
    )

    return {
        "reply": reply,
        "updated_state": updated_state,
    }
