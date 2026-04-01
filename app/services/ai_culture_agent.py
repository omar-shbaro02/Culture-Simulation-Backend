import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DIMENSION_SYSTEM_PROMPTS = {
    "leadership_trust": """
You are a science-backed leadership trust advisor.
Use organizational psychology principles: transparency, psychological safety,
leadership reliability, empathy, and autonomy.
Give practical workplace guidance.
"""
}


def _fallback_delta(text: str) -> int:
    t = (text or "").lower()
    negative_terms = [
        "burnout",
        "afraid",
        "micromanage",
        "retaliation",
        "toxic",
        "unclear",
        "overworked",
    ]
    positive_terms = [
        "improved",
        "better",
        "clear",
        "trust",
        "safe",
        "recognition",
        "collaboration",
        "autonomy",
    ]

    neg = sum(1 for term in negative_terms if term in t)
    pos = sum(1 for term in positive_terms if term in t)
    raw = pos - neg
    return max(-6, min(6, raw))


async def generate_reply(dimension: str, user_message: str):
    system_prompt = DIMENSION_SYSTEM_PROMPTS.get(
        dimension,
        "You are a workplace culture advisor focused on actionable, evidence-based guidance.",
    )

    response = await client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.6,
    )

    return response.choices[0].message.content


async def infer_kpi_delta(dimension: str, user_message: str, assistant_reply: str) -> int:
    fallback = _fallback_delta(user_message)

    system_prompt = """
You estimate KPI delta for a workplace culture dimension.
Return JSON only.
"""
    user_prompt = f"""
Dimension: {dimension}
User message:
{user_message}

Assistant reply:
{assistant_reply}

Return JSON exactly like:
{{"delta": 0}}

Rules:
- delta must be an integer from -8 to 8.
- Positive delta when new evidence indicates stronger culture behavior.
- Negative delta when new evidence indicates worsening culture risk.
- 0 when unclear or neutral.
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        text = response.choices[0].message.content or ""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return fallback

        parsed = json.loads(text[start : end + 1])
        delta = int(parsed.get("delta", fallback))
        return max(-8, min(8, delta))
    except Exception:
        return fallback
