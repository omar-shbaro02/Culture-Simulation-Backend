from fastapi import APIRouter
from pydantic import BaseModel

from app.services.employee_checkin_agent import generate_employee_checkin_reply
from app.services.employee_signal_analyzer import analyze_employee_signals
from app.services.dimension_state_manager import apply_delta, get_all_dimension_states

router = APIRouter(prefix="/employee-checkin", tags=["employee-checkin"])


class EmployeeCheckInRequest(BaseModel):
    message: str
    previous_response_id: str | None = None


@router.post("/chat")
async def employee_checkin_chat(body: EmployeeCheckInRequest):
    reply, response_id = await generate_employee_checkin_reply(
        user_message=body.message,
        previous_response_id=body.previous_response_id,
    )

    signal_analysis = await analyze_employee_signals(body.message)
    scope = signal_analysis.get("scope", "team")
    updates = signal_analysis.get("updates", [])
    updated_states = {}

    for update in updates:
        dimension = update["dimension"]
        updated_states[dimension] = apply_delta(
            dimension,
            update["delta"],
            source="employee_checkin_ai",
            scope=scope,
            reason=update["reason"],
        )

    return {
        "reply": reply,
        "response_id": response_id,
        "scope": scope,
        "metric_updates": updates,
        "updated_states": updated_states,
        "all_states": get_all_dimension_states(),
    }
