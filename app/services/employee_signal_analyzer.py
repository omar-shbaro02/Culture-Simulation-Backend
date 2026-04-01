import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from app.services.dimension_state_manager import CANONICAL_DIMENSIONS

load_dotenv()

MODEL_NAME = os.getenv("OPENAI_EMPLOYEE_SIGNAL_MODEL", "gpt-5.2")

_api_key = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=_api_key) if _api_key else None

DIMENSION_LABELS = {
    "leadership_trust": "Leadership Trust",
    "psychological_safety": "Psychological Safety",
    "workload_sustainability": "Workload Sustainability",
    "role_clarity": "Role Clarity",
    "decision_autonomy": "Decision Autonomy",
    "feedback_quality": "Feedback Quality",
    "recognition_fairness": "Recognition Fairness",
    "change_stability": "Change Stability",
    "collaboration_health": "Collaboration Health",
}

FALLBACK_RULES = {
    "leadership_trust": [
        "boss",
        "manager",
        "leadership",
        "meetings",
        "micromanag",
        "stubborn",
        "disregard",
    ],
    "psychological_safety": [
        "risky to disagree",
        "afraid",
        "shut down",
        "blamed",
        "retaliat",
    ],
    "workload_sustainability": [
        "too much work",
        "too many projects",
        "weekend",
        "holiday",
        "off day",
        "overwhelmed",
        "burnout",
        "break",
        "hours",
    ],
    "role_clarity": [
        "unclear",
        "confusing",
        "expectation",
        "responsibilit",
        "ownership",
    ],
    "decision_autonomy": [
        "approval",
        "micromanag",
        "trusted to decide",
        "free to decide",
    ],
    "feedback_quality": [
        "feedback",
        "coaching",
        "guidance",
        "review",
    ],
    "recognition_fairness": [
        "pay cut",
        "paycut",
        "paycuts",
        "salary cut",
        "credit",
        "acknowledged",
        "recognized",
    ],
    "change_stability": [
        "priorities keep changing",
        "constant change",
        "pivot",
        "reorg",
        "stable",
    ],
    "collaboration_health": [
        "collaborat",
        "teamwork",
        "working with",
        "handoff",
        "silo",
    ],
}

SIGNAL_ANALYZER_INSTRUCTIONS = f"""
You analyze employee check-in messages and extract culture signal updates for a culture simulation product.

The only valid dimensions are:
{", ".join(CANONICAL_DIMENSIONS)}

Dimension guide:
- leadership_trust: trust in leadership judgment, fairness, reliability, respect, transparency, and whether leaders remove friction or create it
- psychological_safety: whether people can speak honestly, disagree, surface risks, and admit mistakes without fear
- workload_sustainability: pace, overload, after-hours pressure, burnout risk, interruptions, wasted time, and capacity strain
- role_clarity: clarity of ownership, expectations, priorities, and who is responsible for what
- decision_autonomy: freedom to make decisions without unnecessary approvals, blocking, or control
- feedback_quality: whether people receive timely, useful, specific feedback and coaching
- recognition_fairness: whether effort, contribution, pay, rewards, and recognition feel fair and consistent
- change_stability: whether priorities, plans, and direction are stable or constantly shifting
- collaboration_health: how well coworkers coordinate, support each other, and work across boundaries

Return JSON only in this exact shape:
{{
  "scope": "team",
  "updates": [
    {{
      "dimension": "leadership_trust",
      "delta": -4,
      "reason": "One sentence explaining the inferred cultural signal.",
      "evidence": ["short phrase from the employee message", "another phrase"]
    }}
  ]
}}

Rules:
- `scope` must be one of: team, department, organization.
- Review every dimension before deciding what to return.
- Include 0 to 6 updates.
- Only include a dimension if the message provides meaningful evidence of improvement or deterioration.
- `delta` must be an integer from -8 to 8.
- Positive delta means improvement. Negative delta means deterioration.
- Mixed messages can produce both positive and negative updates across different dimensions.
- Reasons must be specific and written in plain language.
- Evidence must be short phrases grounded in the employee message, not invented.
- It is acceptable for one message to affect several dimensions if the evidence genuinely supports that.
- Do not collapse distinct issues into only one dimension if they clearly map to different cards.
- Distinguish the type of problem:
  - leadership behavior or unfair management -> leadership_trust
  - overload, forced extra time, constant interruptions, or meeting overload -> workload_sustainability
  - unfair pay, arbitrary compensation changes, or inequitable rewards -> recognition_fairness
  - good teamwork or poor teamwork -> collaboration_health
  - fear of speaking up -> psychological_safety
  - unclear responsibilities -> role_clarity
  - blocked decisions or over-control -> decision_autonomy
  - poor coaching or weak feedback loops -> feedback_quality
  - unstable priorities or constant pivots -> change_stability
- If the same evidence affects two dimensions differently, include both with different reasons.
- Use stronger deltas only when the language is strong, repeated, or clearly harmful/helpful.
- Use semantic understanding, not only keyword matching.
"""


def _infer_scope_fallback(message: str) -> str:
    lowered = (message or "").lower()
    if any(term in lowered for term in ["company-wide", "company wide", "organization", "company", "everyone"]):
        return "organization"
    if any(term in lowered for term in ["department", "division", "function", "unit"]):
        return "department"
    return "team"


def _fallback_updates(message: str) -> dict:
    lowered = (message or "").lower()
    updates = []

    for dimension, terms in FALLBACK_RULES.items():
      matches = [term for term in terms if term in lowered]
      if not matches:
          continue

      negative = sum(
          1
          for term in matches
          if term not in {"stable", "recognized", "acknowledged", "trusted to decide", "free to decide"}
      )
      positive = len(matches) - negative
      delta = max(-6, min(6, positive - negative))

      if delta == 0:
          delta = -2

      updates.append(
          {
              "dimension": dimension,
              "delta": delta,
              "reason": f"Employee check-in suggested a change in {DIMENSION_LABELS[dimension].lower()}.",
              "evidence": matches[:3],
          }
      )

    return {
        "scope": _infer_scope_fallback(message),
        "updates": updates[:5],
    }


async def analyze_employee_signals(message: str) -> dict:
    if client is None:
        return _fallback_updates(message)

    prompt = f"""
Employee message:
{message}
"""

    try:
        response = await client.responses.create(
            model=MODEL_NAME,
            instructions=SIGNAL_ANALYZER_INSTRUCTIONS,
            input=prompt,
            max_output_tokens=700,
            reasoning={"effort": "high"},
            temperature=0.2,
        )
        raw = (response.output_text or "").strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return _fallback_updates(message)

        parsed = json.loads(raw[start : end + 1])
        scope = parsed.get("scope")
        if scope not in {"team", "department", "organization"}:
            scope = _infer_scope_fallback(message)

        normalized_updates = []
        for update in parsed.get("updates", [])[:5]:
            dimension = str(update.get("dimension", "")).strip().lower()
            if dimension not in DIMENSION_LABELS:
                continue

            try:
                delta = int(update.get("delta", 0))
            except Exception:
                delta = 0

            evidence = [
                str(item).strip()
                for item in update.get("evidence", [])
                if str(item).strip()
            ][:3]

            reason = str(update.get("reason", "")).strip() or (
                f"Employee check-in suggested a change in {DIMENSION_LABELS[dimension].lower()}."
            )

            if delta == 0:
                continue

            normalized_updates.append(
                {
                    "dimension": dimension,
                    "title": DIMENSION_LABELS[dimension],
                    "delta": max(-8, min(8, delta)),
                    "reason": reason,
                    "evidence": evidence,
                }
            )

        return {
            "scope": scope,
            "updates": normalized_updates,
        }
    except Exception:
        return _fallback_updates(message)
