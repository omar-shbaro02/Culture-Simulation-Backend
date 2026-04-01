from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.scenario_agent import (
    chat_with_strategy_agent,
    generate_strategy_plan,
)

router = APIRouter(prefix="/strategy", tags=["Strategy"])


class StrategyTemplate(BaseModel):
    id: str
    title: str
    horizon: str
    goal: str
    actions: str


class StrategyGenerateRequest(BaseModel):
    template: StrategyTemplate
    context: str


class StrategyChatRequest(BaseModel):
    template: StrategyTemplate
    message: str
    strategy: Dict[str, Any] | list[Any] | str | None = None


@router.post("/generate")
async def generate_strategy(payload: StrategyGenerateRequest):
    context = payload.context.strip()
    if not context:
        raise HTTPException(status_code=400, detail="Context is required.")

    return generate_strategy_plan(payload.template.model_dump(), context)


@router.post("/chat")
async def chat_strategy(payload: StrategyChatRequest):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required.")

    reply = chat_with_strategy_agent(
        template=payload.template.model_dump(),
        strategy=payload.strategy,
        message=message,
    )
    return {"reply": reply}
