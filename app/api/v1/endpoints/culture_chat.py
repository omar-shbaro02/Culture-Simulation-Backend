from fastapi import APIRouter
from pydantic import BaseModel
from app.services.culture_agent_engine import ask_culture_agent

router = APIRouter(prefix="/chat", tags=["Culture Chat"])

class ChatInput(BaseModel):
    message: str

@router.post("/{dimension_slug}")
def culture_chat(dimension_slug: str, data: ChatInput):
    reply = ask_culture_agent(dimension_slug, data.message)
    return {"reply": reply}
