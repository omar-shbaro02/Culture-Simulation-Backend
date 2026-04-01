import json
from typing import Any, Dict, List

from app.services.pipeline import call_ai, call_ai_json


def _template_field(template: Dict[str, Any], key: str, default: str = "") -> str:
    value = template.get(key, default)
    return value if isinstance(value, str) else default


def _infer_focus_area(template: Dict[str, Any]) -> str:
    template_id = _template_field(template, "id").lower()
    title = _template_field(template, "title").lower()
    text = f"{template_id} {title}"

    if "leadership" in text:
        return "leadership_trust"
    if "burnout" in text or "workload" in text:
        return "workload_sustainability"
    if "psych" in text or "safety" in text:
        return "psychological_safety"
    return "collaboration_health"


def _fallback_strategy(template: Dict[str, Any], context: str) -> Dict[str, Any]:
    title = _template_field(template, "title", "Scenario")
    horizon = _template_field(template, "horizon", "6-8 weeks")
    goal = _template_field(template, "goal", "Improve team culture outcomes.")
    actions = _template_field(template, "actions", "Clarify actions and ownership.")
    focus_area = _infer_focus_area(template)

    steps: List[str] = [
        f"Define the decision owner, success metric, and weekly operating cadence for the {title.lower()} plan.",
        f"Translate this context into team-specific actions: {context}",
        f"Launch the core intervention set: {actions}",
        "Review adoption signals weekly and remove blockers within 48 hours.",
        "Run a midpoint checkpoint with managers and employees to adjust sequencing.",
    ]

    risks: List[str] = [
        "Managers may treat the plan as communication only and not change day-to-day behavior.",
        "Teams may see the intervention as extra work unless delivery priorities are rebalanced.",
        "Momentum can fade if leaders do not publish visible follow-through each week.",
    ]

    metrics: List[str] = [
        f"{focus_area} pulse score trend",
        "Weekly participation and adoption rate",
        "Manager follow-through on committed actions",
        "Employee sentiment themes from check-ins or retrospectives",
    ]

    return {
        "summary": (
            f"{title} should focus on {goal.lower()} Use the first two weeks to align "
            "owners, communicate expectations, and remove obvious blockers before scaling."
        ),
        "timeline": horizon,
        "steps": steps,
        "risks": risks,
        "metrics": metrics,
        "notes": (
            "Treat this as a managed change effort, not a one-time announcement. "
            "Visible leadership follow-through is the main success condition."
        ),
        "focus_area": focus_area,
        "source": "scenario_fallback",
    }


def generate_strategy_plan(template: Dict[str, Any], context: str) -> Dict[str, Any]:
    fallback = _fallback_strategy(template, context)
    title = _template_field(template, "title", "Scenario")
    horizon = _template_field(template, "horizon", "6-8 weeks")
    goal = _template_field(template, "goal", "Improve team culture outcomes.")
    actions = _template_field(template, "actions", "Clarify actions and ownership.")
    focus_area = _infer_focus_area(template)

    system_prompt = """
You are the Scenario Strategy Agent for a workplace culture simulator.
Return strict JSON only.
"""
    user_prompt = f"""
Scenario template:
{json.dumps(template, indent=2)}

User context:
{context}

Return JSON with this exact shape:
{{
  "summary": "string",
  "timeline": "string",
  "steps": ["string"],
  "risks": ["string"],
  "metrics": ["string"],
  "notes": "string",
  "focus_area": "string",
  "source": "ai_scenario_agent"
}}

Rules:
- This is a scenario generator, not a generic advisor.
- Build an execution-ready intervention plan for the named template.
- Tailor the plan to the provided context and constraints.
- Include 4 to 6 steps, 2 to 4 risks, and 3 to 5 metrics.
- Keep outputs concise, practical, and workplace-focused.
- Use this target focus area unless context clearly requires a close adjacent one: {focus_area}.
- Respect this intended horizon: {horizon}.
- Use this intended goal: {goal}.
- Use these starting actions as inputs, not as the final answer: {actions}.
"""

    result = call_ai_json(system_prompt, user_prompt, fallback=fallback, temperature=0.3)

    if not isinstance(result.get("steps"), list) or not result["steps"]:
        return fallback
    if not isinstance(result.get("risks"), list):
        result["risks"] = fallback["risks"]
    if not isinstance(result.get("metrics"), list):
        result["metrics"] = fallback["metrics"]

    result["summary"] = result.get("summary") or fallback["summary"]
    result["timeline"] = result.get("timeline") or horizon
    result["notes"] = result.get("notes") or fallback["notes"]
    result["focus_area"] = result.get("focus_area") or focus_area
    result["source"] = result.get("source") or "ai_scenario_agent"
    return result


def _strategy_snapshot(strategy: Any) -> str:
    try:
        return json.dumps(strategy, indent=2)
    except Exception:
        return str(strategy)


def chat_with_strategy_agent(
    template: Dict[str, Any],
    strategy: Any,
    message: str,
) -> str:
    title = _template_field(template, "title", "Scenario")
    fallback_reply = (
        f"For {title}, I would keep the plan anchored to execution clarity: "
        "tighten ownership, reduce rollout friction, and add a weekly review loop "
        "for risks, adoption, and metric movement."
    )

    system_prompt = """
You are the Scenario Strategy Agent for a workplace culture simulator.
Reply as a practical strategy coach.
"""
    user_prompt = f"""
Scenario template:
{json.dumps(template, indent=2)}

Current strategy:
{_strategy_snapshot(strategy)}

User follow-up:
{message}

Rules:
- Answer the user's question directly.
- Stay consistent with the existing scenario and strategy.
- Suggest concrete refinements, sequencing changes, risk controls, or measurement improvements.
- Keep the answer concise but useful.
"""

    try:
        return call_ai(system_prompt, user_prompt, temperature=0.3)
    except Exception:
        return fallback_reply
