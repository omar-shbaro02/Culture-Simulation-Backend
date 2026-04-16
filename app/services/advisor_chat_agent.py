import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

MODEL_NAME = os.getenv("OPENAI_ADVISOR_CHAT_MODEL", "gpt-5.2-chat-latest")

_api_key = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=_api_key) if _api_key else None

ADVISOR_CHAT_INSTRUCTIONS = """
You are George, Maya's management-side counterpart inside a culture simulation product.

Your job:
- Sound like George: a thoughtful human advisor, not a bot.
- Keep the same natural, warm, attentive conversational feel Maya has in check-in.
- Stay management-oriented: help leaders, HR partners, and managers interpret risk, make decisions, and sequence action.
- Answer only from the provided analysis and the user's question.
- Usually write 2 to 5 sentences.
- Ask at most one follow-up question, and only when it helps narrow a decision.
- Make the exchange feel alive, responsive, and practical.

Important style rules:
- Do not say you are an AI, model, assistant, or system.
- Do not sound clinical, generic, or repetitive.
- Do not answer like a dashboard export or consultant slide.
- Vary your openings. Do not keep repeating phrases like "Based on the analysis" or "The data suggests".
- Pull out one or two concrete details from the analysis or the user's wording so the reply feels genuinely attentive.
- If there are mixed signals, acknowledge the tension plainly.
- When useful, name the practical management implication: trust, execution risk, sequencing, manager load, credibility, or follow-through.
- Be candid about uncertainty. If the analysis does not support a claim, say so plainly.
- Do not invent facts, metrics, benchmarks, or causal claims that are not present in the provided analysis.
- Use numbers or benchmark references when they are available in the analysis, but weave them in naturally.
- Keep the tone warm and conversational even when the advice is firm.

Conversation moves to rotate between:
- reflective: mirror what leadership is really facing
- contrast-aware: notice where one strength is being undercut by another weak spot
- prioritizing: identify what should happen first and why
- risk-aware: explain what gets worse if they push the wrong lever
- forward-looking: suggest the next move, checkpoint, or decision to test

Avoid:
- repeating the same sentence structure across turns
- bloated executive-summary language
- turning every answer into a numbered framework unless the user asks for one
- drifting into employee-first emotional support language instead of management guidance
"""


def fallback_advisor_reply(question: str, analysis: dict | None = None) -> str:
    text = (question or "").strip().lower()
    dimension_scores = (
        ((analysis or {}).get("scoring_result") or {}).get("dimension_scores") or {}
    )

    weakest_dimension = None
    weakest_score = None
    for slug, payload in dimension_scores.items():
        try:
            score = int(payload.get("score_0_100", 50))
        except Exception:
            continue
        if weakest_score is None or score < weakest_score:
            weakest_dimension = slug.replace("_", " ")
            weakest_score = score

    if any(term in text for term in ["first", "priority", "start", "sequence"]):
        if weakest_dimension and weakest_score is not None:
            return (
                f"I'd start with {weakest_dimension}, because that looks like the softest spot in the current analysis at around {weakest_score}/100. "
                "If you try to fix everything at once, teams usually just feel more motion and not more clarity. "
                "Pick one visible move there first, then use the next check-in cycle to see whether confidence and execution actually improve."
            )

        return (
            "I would start with the area creating the most immediate execution drag, then keep the first intervention narrow enough that people can feel the difference quickly. "
            "If the first move is too broad, it usually creates noise instead of trust."
        )

    if any(term in text for term in ["risk", "burnout", "trust", "leadership"]):
        return (
            "The management read here is that the culture risk is not just sentiment, it is operational. "
            "When trust or workload pressure starts showing up repeatedly, leaders usually pay for it through slower decisions, lower follow-through, and more skepticism about change. "
            "The strongest next step is the one that reduces friction people can see, not just the one that sounds reassuring."
        )

    return (
        "There is enough here to give direction, but I would keep the next move practical. "
        "Look for the point where leadership behavior, workload, or clarity is shaping day-to-day execution most directly, then intervene there first. "
        "If you want, we can narrow this to sequencing, manager behavior, or rollout risk."
    )


async def generate_advisor_reply(
    question: str,
    analysis: dict,
    previous_response_id: str | None = None,
) -> tuple[str, str | None]:
    if client is None:
        return fallback_advisor_reply(question, analysis), None

    prompt = f"""
ANALYSIS SNAPSHOT:
{json.dumps(analysis, indent=2)}

MANAGEMENT QUESTION:
{(question or '').strip()}
"""

    try:
        response = await client.responses.create(
            model=MODEL_NAME,
            instructions=ADVISOR_CHAT_INSTRUCTIONS,
            input=prompt,
            previous_response_id=previous_response_id or None,
            max_output_tokens=420,
            temperature=1.0,
        )

        reply = (response.output_text or "").strip()
        if not reply:
            return fallback_advisor_reply(question, analysis), None

        return reply, response.id
    except Exception:
        return fallback_advisor_reply(question, analysis), None
