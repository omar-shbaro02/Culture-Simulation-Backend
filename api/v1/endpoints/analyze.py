from fastapi import APIRouter
from pydantic import BaseModel
from app.services.pipeline import run_pipeline, LAST_ANALYSIS

router = APIRouter(prefix="/analyze")


class AnalyzeRequest(BaseModel):
    problem: str


@router.post("")
async def analyze(payload: AnalyzeRequest):
    global LAST_ANALYSIS

    result = await run_pipeline(payload.problem)
    LAST_ANALYSIS = result

    return result
