from app.services.pipeline import call_ai_json


def _score_level(score: int) -> str:
    if score >= 70:
        return "healthy"
    if score >= 50:
        return "moderate"
    return "needs_attention"


def _fallback_dimension_advice(dimension: str, score: int) -> dict:
    level = _score_level(score)
    base_actions = {
        "healthy": [
            "Preserve current practices and monitor trend drift monthly.",
            "Document what is working so managers can replicate it."
        ],
        "moderate": [
            "Run focused manager coaching on this dimension.",
            "Set explicit team-level behavior expectations and track compliance.",
            "Review progress every 2 weeks and adjust fast."
        ],
        "needs_attention": [
            "Treat this as a priority risk and assign executive sponsorship.",
            "Deploy a 30-60 day intervention plan with weekly checkpoints.",
            "Track leading indicators and employee sentiment to verify recovery."
        ],
    }
    recommendations = [
        {"driver": "leadership_practice", "actions": base_actions[level]},
    ]

    return {
        "dimension": dimension,
        "score": score,
        "level": level,
        "recommendations": recommendations,
        "method": "fallback_rules",
    }


def generate_dimension_advice(dimension_slug: str, score: int) -> dict:
    dimension_name = dimension_slug.replace("-", " ").replace("_", " ").title()
    fallback = _fallback_dimension_advice(dimension_name, score)

    system_prompt = """
You are an AI culture dimension advisor.
Return strict JSON only.
"""
    user_prompt = f"""
Dimension: {dimension_name}
Score: {score}

Return JSON with this exact shape:
{{
  "dimension": "string",
  "score": 0,
  "level": "healthy|moderate|needs_attention",
  "recommendations": [
    {{
      "driver": "snake_case_driver",
      "actions": ["action 1", "action 2", "action 3"]
    }}
  ],
  "method": "ai_dimension_advisor"
}}

Rules:
- Keep recommendations practical and workplace-focused.
- Include 2 to 5 recommendation objects.
- Keep actions concise and executable.
"""
    result = call_ai_json(system_prompt, user_prompt, fallback=fallback, temperature=0.3)

    if not isinstance(result.get("recommendations"), list):
        return fallback

    result["dimension"] = result.get("dimension") or dimension_name
    result["score"] = score
    if result.get("level") not in {"healthy", "moderate", "needs_attention"}:
        result["level"] = _score_level(score)
    return result


def generate_leadership_trust_advice(score: int):
    return generate_dimension_advice("leadership-trust", score)
