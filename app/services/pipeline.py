import json
import os
import re
from statistics import mean
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY) if API_KEY else None

KPI_DIMENSIONS = [
    "leadership_trust",
    "psychological_safety",
    "workload_sustainability",
    "role_clarity",
    "decision_autonomy",
    "feedback_quality",
    "recognition_fairness",
    "change_stability",
    "collaboration_health",
]

DIMENSION_ALIASES = {
    "leadership": "leadership_trust",
    "autonomy": "decision_autonomy",
    "wellbeing": "workload_sustainability",
    "communication": "psychological_safety",
    "psychological_safety": "psychological_safety",
}


# -----------------------------
# Core AI helpers
# -----------------------------
def call_ai(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    if client is None:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


def _extract_json(text: str) -> Dict[str, Any]:
    if not text:
        raise ValueError("Empty model output")

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        parsed = json.loads(fenced.group(1))
        if isinstance(parsed, dict):
            return parsed

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        parsed = json.loads(text[start : end + 1])
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("No JSON object found")


def call_ai_json(
    system_prompt: str,
    user_prompt: str,
    fallback: Dict[str, Any],
    temperature: float = 0.2,
) -> Dict[str, Any]:
    try:
        raw = call_ai(system_prompt, user_prompt, temperature=temperature)
        parsed = _extract_json(raw)
        return parsed
    except Exception:
        return fallback


# -----------------------------
# Fallback deterministic logic
# -----------------------------
def _fallback_nlp_normalize(problem_text: str) -> dict:
    text = (problem_text or "").lower()
    signals = []

    if any(k in text for k in ["micromanage", "micromanaged", "over control"]):
        signals.append("micromanagement")

    if any(k in text for k in ["burnout", "burned out", "exhausted", "overworked"]):
        signals.append("burnout")

    if any(k in text for k in ["fear", "afraid", "retaliation"]):
        signals.append("fear_of_speaking")

    if any(k in text for k in ["unclear", "confusing", "no direction"]):
        signals.append("role_clarity_issues")

    if not signals:
        signals.append("general_dissatisfaction")

    taxonomy = {}

    if "micromanagement" in signals:
        taxonomy["leadership"] = ["micromanagement"]
        taxonomy["autonomy"] = ["low_autonomy"]

    if "burnout" in signals:
        taxonomy["wellbeing"] = ["burnout", "workload_pressure"]

    if "fear_of_speaking" in signals:
        taxonomy["communication"] = ["low_psychological_safety"]

    if "role_clarity_issues" in signals:
        taxonomy.setdefault("communication", []).append("role_clarity")

    emotional_intensity = "moderate"
    urgency = "medium"
    scope = "team"

    if any(k in text for k in ["always", "never", "toxic", "breaking"]):
        emotional_intensity = "high"
        urgency = "high"

    clean_statement = f"Employees report issues related to {problem_text.strip().lower()}."

    return {
        "clean_problem_statement": clean_statement,
        "signals": signals,
        "taxonomy": taxonomy,
        "severity_hints": {
            "emotional_intensity": emotional_intensity,
            "scope": scope,
            "urgency": urgency,
        },
    }


def _fallback_score_culture(taxonomy: dict) -> dict:
    base_score = 50
    penalties = {
        "micromanagement": 20,
        "low_autonomy": 15,
        "burnout": 25,
        "workload_pressure": 15,
        "low_psychological_safety": 25,
        "role_clarity": 10,
    }
    boosts = {
        "high_transparency": 8,
        "role_clarity": 4,
        "recognition": 6,
        "healthy_collaboration": 8,
        "constructive_feedback": 7,
    }

    dimension_scores = {
        dim: {"score_0_100": base_score, "confidence": 0.5, "drivers": []}
        for dim in KPI_DIMENSIONS
    }

    for dimension, issues in taxonomy.items():
        canonical_dim = DIMENSION_ALIASES.get(dimension, dimension)
        if canonical_dim not in dimension_scores:
            continue

        score = dimension_scores[canonical_dim]["score_0_100"]
        applied_drivers = list(dimension_scores[canonical_dim]["drivers"])

        for issue in issues:
            if issue in penalties:
                score -= penalties[issue]
                applied_drivers.append(f"-{issue}")
            elif issue in boosts:
                score += boosts[issue]
                applied_drivers.append(f"+{issue}")

        confidence = min(0.5 + 0.08 * len(issues), 0.95)
        dimension_scores[canonical_dim] = {
            "score_0_100": max(0, min(100, score)),
            "confidence": round(confidence, 2),
            "drivers": applied_drivers,
        }

    overall_score = round(
        mean(d["score_0_100"] for d in dimension_scores.values()), 1
    )

    return {
        "dimension_scores": dimension_scores,
        "overall_score_0_100": overall_score,
        "method": {
            "type": "fallback_rules",
            "base_score": base_score,
            "penalties": penalties,
            "boosts": boosts,
        },
    }


def _normalize_dimension_slug(slug: str) -> str:
    if slug in KPI_DIMENSIONS:
        return slug
    if slug in DIMENSION_ALIASES:
        return DIMENSION_ALIASES[slug]
    return slug


def _fallback_benchmark_culture(scoring_result: dict) -> dict:
    issue_frequencies = {
        "micromanagement": 38,
        "burnout": 44,
        "low_autonomy": 41,
        "workload_pressure": 47,
        "low_psychological_safety": 29,
        "role_clarity": 22,
    }

    percentiles = {}
    for dimension, data in scoring_result["dimension_scores"].items():
        score = int(data.get("score_0_100", 50))
        percentiles[dimension] = {"percentile": max(5, min(95, score)), "score_0_100": score}

    return {
        "cohort": {
            "size_n": 820,
            "description": "Simulated workplace culture benchmark cohort",
        },
        "issue_frequencies_percent": issue_frequencies,
        "dimension_percentiles": percentiles,
        "correlations": [
            {"issue_pair": ["burnout", "micromanagement"], "co_occurrence_percent": 52}
        ],
        "method": "fallback_rules",
    }


def _fallback_strategy_recommendations(nlp_result: dict, benchmark_result: dict) -> dict:
    recommendations = []
    signals = nlp_result.get("signals", [])

    if "micromanagement" in signals:
        recommendations.append(
            {
                "issue": "Micromanagement",
                "why_it_matters": (
                    f"Micromanagement appears in {benchmark_result['issue_frequencies_percent'].get('micromanagement', 0)}% "
                    "of benchmarked cases and often drags autonomy and trust."
                ),
                "what_to_change": [
                    "Define manager decision boundaries",
                    "Reduce low-value approvals",
                    "Coach managers on outcomes over control",
                ],
                "kpis": ["Decision cycle time", "Autonomy score", "Escalation frequency"],
                "expected_impact": {
                    "leadership_trust_score_change": 8,
                    "decision_autonomy_score_change": 7,
                },
                "priority": "high",
            }
        )

    if "burnout" in signals:
        recommendations.append(
            {
                "issue": "Burnout and workload pressure",
                "why_it_matters": (
                    f"Burnout appears in {benchmark_result['issue_frequencies_percent'].get('burnout', 0)}% "
                    "of benchmarked cases and is tied to attrition risk."
                ),
                "what_to_change": [
                    "Set workload caps by role",
                    "Protect focus time",
                    "Track overtime and rebalance staffing",
                ],
                "kpis": ["Weekly hours", "Overtime frequency", "Sick leave trend"],
                "expected_impact": {"workload_sustainability_score_change": 12},
                "priority": "critical",
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "issue": "General cultural friction",
                "why_it_matters": "Signal quality is broad, so first focus on diagnosis depth.",
                "what_to_change": [
                    "Run manager listening sessions",
                    "Map role clarity gaps",
                    "Set short-cycle intervention experiments",
                ],
                "kpis": ["Employee sentiment", "Role clarity score", "Manager follow-through"],
                "expected_impact": {"collaboration_health_score_change": 6},
                "priority": "medium",
            }
        )

    priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    recommendations = sorted(recommendations, key=lambda r: priority_rank.get(r.get("priority", "medium"), 2))

    return {
        "summary": {
            "total_recommendations": len(recommendations),
            "focus_area": "culture intervention sequencing",
        },
        "recommendations": recommendations,
        "method": "fallback_rules",
    }


def _fallback_simulate_outcomes(scoring_result: dict, strategy_result: dict) -> dict:
    current_scores = {
        dim: data.get("score_0_100", 50)
        for dim, data in scoring_result.get("dimension_scores", {}).items()
    }
    projected_scores = current_scores.copy()

    for rec in strategy_result.get("recommendations", []):
        for key, delta in rec.get("expected_impact", {}).items():
            if not key.endswith("_score_change"):
                continue
            target = key.replace("_score_change", "")
            if target in projected_scores:
                projected_scores[target] = min(100, projected_scores[target] + int(delta))

    improvements = {}
    for dim, old_value in current_scores.items():
        new_value = projected_scores.get(dim, old_value)
        improvements[dim] = {
            "from": old_value,
            "to": new_value,
            "absolute_change": new_value - old_value,
            "percent_change": round(((new_value - old_value) / max(old_value, 1)) * 100, 1),
        }

    return {
        "projected_scores": projected_scores,
        "improvements": improvements,
        "risk_reduction_estimates": {
            "burnout_risk_reduction_percent": 16,
            "attrition_risk_reduction_percent": 9.6,
        },
        "time_to_effect": {"short_term": "4-8 weeks", "mid_term": "3-6 months"},
        "assumptions": [
            "Leadership adopts actions consistently",
            "Interventions are resourced and monitored",
            "No major restructuring during the cycle",
        ],
        "method": "fallback_rules",
    }


# -----------------------------
# AI-first agents
# -----------------------------
def nlp_normalize(problem_text: str) -> dict:
    fallback = _fallback_nlp_normalize(problem_text)
    system_prompt = """
You are Agent 1: AI NLP Normalization for workplace culture analysis.
Return strict JSON only.
"""
    user_prompt = f"""
Input problem statement:
{problem_text}

Return JSON with this exact shape:
{{
  "clean_problem_statement": "string",
  "signals": ["snake_case_signal"],
  "taxonomy": {{"dimension_slug": ["issue_slug"]}},
  "severity_hints": {{
    "emotional_intensity": "low|moderate|high",
    "scope": "team|department|organization",
    "urgency": "low|medium|high"
  }}
}}

Rules:
- Keep 3 to 10 signals when possible.
- Use concise stable slugs.
- Keep taxonomy dimensions relevant to organizational culture.
"""
    result = call_ai_json(system_prompt, user_prompt, fallback=fallback)

    if not isinstance(result.get("signals"), list):
        return fallback
    if not isinstance(result.get("taxonomy"), dict):
        return fallback
    if not isinstance(result.get("severity_hints"), dict):
        return fallback

    return result


def score_culture(problem_text: str, nlp_result: dict) -> dict:
    fallback = _fallback_score_culture(nlp_result.get("taxonomy", {}))
    system_prompt = """
You are Agent 2: AI Culture Scoring.
Return strict JSON only.
"""
    user_prompt = f"""
Problem text:
{problem_text}

NLP result:
{json.dumps(nlp_result, indent=2)}

Return JSON with this exact shape:
{{
  "dimension_scores": {{
    "dimension_slug": {{
      "score_0_100": 0,
      "confidence": 0.0,
      "drivers": ["driver_slug"]
    }}
  }},
  "overall_score_0_100": 0,
  "method": {{
    "type": "ai_scoring",
    "notes": "short text"
  }}
}}

Rules:
- Scores must be integers from 0 to 100.
- Confidence must be between 0 and 1.
- Use exactly these dimension keys (all required):
  leadership_trust
  psychological_safety
  workload_sustainability
  role_clarity
  decision_autonomy
  feedback_quality
  recognition_fairness
  change_stability
  collaboration_health
"""
    result = call_ai_json(system_prompt, user_prompt, fallback=fallback)

    if not isinstance(result.get("dimension_scores"), dict) or not result["dimension_scores"]:
        return fallback

    clean_scores = {
        dim: {"score_0_100": 50, "confidence": 0.45, "drivers": []}
        for dim in KPI_DIMENSIONS
    }
    for dim, data in result["dimension_scores"].items():
        if not isinstance(data, dict):
            continue
        canonical_dim = _normalize_dimension_slug(dim)
        if canonical_dim not in clean_scores:
            continue
        try:
            score = int(data.get("score_0_100", 50))
        except Exception:
            score = 50
        score = max(0, min(100, score))

        try:
            confidence = float(data.get("confidence", 0.5))
        except Exception:
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        drivers = data.get("drivers", [])
        if not isinstance(drivers, list):
            drivers = []

        clean_scores[canonical_dim] = {
            "score_0_100": score,
            "confidence": round(confidence, 2),
            "drivers": drivers,
        }

    if not clean_scores:
        return fallback

    try:
        overall = int(result.get("overall_score_0_100", round(mean(d["score_0_100"] for d in clean_scores.values()))))
    except Exception:
        overall = int(round(mean(d["score_0_100"] for d in clean_scores.values())))

    return {
        "dimension_scores": clean_scores,
        "overall_score_0_100": max(0, min(100, overall)),
        "method": result.get("method", {"type": "ai_scoring"}),
    }


def benchmark_culture(problem_text: str, nlp_result: dict, scoring_result: dict) -> dict:
    fallback = _fallback_benchmark_culture(scoring_result)
    system_prompt = """
You are Agent 3: AI Benchmarking Agent for workplace culture.
Return strict JSON only.
"""
    user_prompt = f"""
Problem text:
{problem_text}

NLP result:
{json.dumps(nlp_result, indent=2)}

Scoring result:
{json.dumps(scoring_result, indent=2)}

Return JSON with this shape:
{{
  "cohort": {{"size_n": 0, "description": "string"}},
  "issue_frequencies_percent": {{"issue_slug": 0}},
  "dimension_percentiles": {{"dimension_slug": {{"percentile": 0, "score_0_100": 0}}}},
  "correlations": [{{"issue_pair": ["a", "b"], "co_occurrence_percent": 0}}],
  "method": "ai_estimate"
}}

Rules:
- Frequencies and percentiles must be integers between 0 and 100.
- Keep percentiles consistent with score direction.
- Treat outputs as model-based benchmark estimates.
"""
    result = call_ai_json(system_prompt, user_prompt, fallback=fallback)

    if not isinstance(result.get("dimension_percentiles"), dict):
        return fallback

    return result


def strategy_recommendations(
    problem_text: str,
    nlp_result: dict,
    scoring_result: dict,
    benchmark_result: dict,
) -> dict:
    fallback = _fallback_strategy_recommendations(nlp_result, benchmark_result)
    system_prompt = """
You are Agent 4: AI Strategy Agent.
Return strict JSON only.
"""
    user_prompt = f"""
Problem text:
{problem_text}

NLP result:
{json.dumps(nlp_result, indent=2)}

Scoring result:
{json.dumps(scoring_result, indent=2)}

Benchmark result:
{json.dumps(benchmark_result, indent=2)}

Return JSON with this shape:
{{
  "summary": {{
    "total_recommendations": 0,
    "focus_area": "string"
  }},
  "recommendations": [
    {{
      "issue": "string",
      "why_it_matters": "string",
      "what_to_change": ["string"],
      "kpis": ["string"],
      "expected_impact": {{"dimension_score_change": 0}},
      "priority": "critical|high|medium|low"
    }}
  ],
  "method": "ai_strategy"
}}

Rules:
- Provide 2 to 5 recommendations.
- Keep recommendations concrete and execution-ready.
- Use only dimensions and issues grounded in prior stage outputs.
"""
    result = call_ai_json(system_prompt, user_prompt, fallback=fallback)

    recommendations = result.get("recommendations")
    if not isinstance(recommendations, list) or not recommendations:
        return fallback

    return result


def simulate_outcomes(
    problem_text: str,
    scoring_result: dict,
    strategy_result: dict,
    benchmark_result: dict,
) -> dict:
    fallback = _fallback_simulate_outcomes(scoring_result, strategy_result)
    system_prompt = """
You are Agent 5: AI Outcome Simulation Agent.
Return strict JSON only.
"""
    user_prompt = f"""
Problem text:
{problem_text}

Scoring result:
{json.dumps(scoring_result, indent=2)}

Strategy result:
{json.dumps(strategy_result, indent=2)}

Benchmark result:
{json.dumps(benchmark_result, indent=2)}

Return JSON with this shape:
{{
  "projected_scores": {{"dimension_slug": 0}},
  "improvements": {{
    "dimension_slug": {{
      "from": 0,
      "to": 0,
      "absolute_change": 0,
      "percent_change": 0.0
    }}
  }},
  "risk_reduction_estimates": {{
    "burnout_risk_reduction_percent": 0,
    "attrition_risk_reduction_percent": 0
  }},
  "time_to_effect": {{
    "short_term": "string",
    "mid_term": "string"
  }},
  "assumptions": ["string"],
  "method": "ai_simulation"
}}

Rules:
- Keep scores between 0 and 100.
- Make improvements directionally consistent with strategy impacts.
- Include at least 3 assumptions.
"""
    result = call_ai_json(system_prompt, user_prompt, fallback=fallback)

    if not isinstance(result.get("projected_scores"), dict):
        return fallback
    if not isinstance(result.get("improvements"), dict):
        return fallback

    return result


# -----------------------------
# Agent 0A: Explainer
# -----------------------------
def explain_results(
    nlp_result: dict,
    scoring_result: dict,
    benchmark_result: dict,
    strategy_result: dict,
    simulation_result: dict,
) -> dict:
    system_prompt = """
You are a senior organizational culture consultant.
Explain analysis results clearly for leadership teams.
"""

    user_prompt = f"""
Explain the following data in plain English.

NLP Analysis:
{json.dumps(nlp_result, indent=2)}

Culture Scores:
{json.dumps(scoring_result, indent=2)}

Benchmark Comparison:
{json.dumps(benchmark_result, indent=2)}

Recommended Actions:
{json.dumps(strategy_result, indent=2)}

Simulated Outcomes:
{json.dumps(simulation_result, indent=2)}

Structure:
1) Executive summary (5-6 sentences)
2) Key problems
3) What data says
4) What to fix first and why
5) Expected improvements
"""

    try:
        explanation_text = call_ai(system_prompt, user_prompt, temperature=0.3)
    except Exception:
        explanation_text = (
            "Executive summary: The analysis indicates material culture risk with clear intervention opportunities. "
            "The most important next step is sequencing high-impact actions against the lowest-scoring dimensions. "
            "Benchmark and simulation outputs should be treated as directional estimates and reviewed with local context."
        )

    return {"executive_explanation": explanation_text}


# -----------------------------
# Agent 0B: Advisor Chat
# -----------------------------
def advisor_chat(last_analysis: dict, question: str) -> str:
    system_prompt = """
You are Agent 0: AI Culture Advisor.
Answer only using the provided analysis.
Use numbers and benchmark references where possible.
"""
    user_prompt = f"""
FULL ANALYSIS:
{json.dumps(last_analysis, indent=2)}

USER QUESTION:
{question}
"""

    try:
        return call_ai(system_prompt, user_prompt, temperature=0.3)
    except Exception:
        return "I cannot access the AI backend right now. Please retry once the model service is available."


# -----------------------------
# Pipeline Orchestrator
# -----------------------------
async def run_pipeline(problem_text: str) -> dict:
    nlp_result = nlp_normalize(problem_text)
    scoring_result = score_culture(problem_text, nlp_result)
    benchmark_result = benchmark_culture(problem_text, nlp_result, scoring_result)
    strategy_result = strategy_recommendations(
        problem_text, nlp_result, scoring_result, benchmark_result
    )
    simulation_result = simulate_outcomes(
        problem_text, scoring_result, strategy_result, benchmark_result
    )
    explainer_result = explain_results(
        nlp_result,
        scoring_result,
        benchmark_result,
        strategy_result,
        simulation_result,
    )

    return {
        "stage": "explanation_complete",
        "agent_mode": "ai_first_with_fallback",
        "nlp_result": nlp_result,
        "scoring_result": scoring_result,
        "benchmark_result": benchmark_result,
        "strategy_result": strategy_result,
        "simulation_result": simulation_result,
        "explanation": explainer_result,
    }
