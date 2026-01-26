from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.pipeline import LAST_ANALYSIS, call_ai
import json

router = APIRouter()


class AdvisorQuestion(BaseModel):
    question: str


class AdvisorAnswer(BaseModel):
    answer: str


@router.post("/ask", response_model=AdvisorAnswer)
async def ask_advisor(payload: AdvisorQuestion):
    """
    Agent 0 — AI Culture Advisor
    Answers questions using the most recent analysis only.
    """

    if LAST_ANALYSIS is None:
        raise HTTPException(
            status_code=400,
            detail="No analysis available. Run a culture analysis first."
        )

    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    system_prompt = """
You are Agent 0: the AI Culture Advisor.

You have access to the FULL analysis results of a company culture simulation.

RULES:
- Answer ONLY using the provided analysis
- Be clear, executive-friendly, and structured
- Use numbers and benchmarks where relevant
- Do NOT invent new data
- Do NOT add recommendations beyond those provided
- If the question cannot be answered, say so clearly
"""

    user_prompt = f"""
Here is the full analysis (JSON):

{json.dumps(LAST_ANALYSIS, indent=2)}

User question:
"{question}"

Answer as an expert culture advisor.
"""

    try:
        answer = call_ai(system_prompt, user_prompt)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
