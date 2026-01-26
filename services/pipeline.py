import re
from statistics import mean
import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
LAST_ANALYSIS = None


def call_ai(system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


# =========================
# Agent 1: NLP Normalization
# =========================


def nlp_normalize(problem_text: str) -> dict:
    text = problem_text.lower()
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

    clean_statement = (
        f"Employees report issues related to {problem_text.strip().lower()}."
    )

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


# =====================
# Agent 2: Scoring Agent
# =====================


def score_culture(taxonomy: dict) -> dict:
    """
    Produces 0–100 culture scores per dimension based on detected issues.
    Lower score = worse culture.
    """

    # baseline healthy score
    BASE_SCORE = 75

    # penalties per issue
    penalties = {
        "micromanagement": 20,
        "low_autonomy": 15,
        "burnout": 25,
        "workload_pressure": 15,
        "low_psychological_safety": 25,
        "role_clarity": 10,
    }

    dimension_scores = {}

    for dimension, issues in taxonomy.items():
        score = BASE_SCORE
        applied_penalties = []

        for issue in issues:
            if issue in penalties:
                score -= penalties[issue]
                applied_penalties.append(issue)

        score = max(score, 0)

        confidence = min(0.4 + 0.15 * len(issues), 0.95)

        dimension_scores[dimension] = {
            "score_0_100": score,
            "confidence": round(confidence, 2),
            "drivers": applied_penalties,
        }

    overall_score = round(mean(d["score_0_100"] for d in dimension_scores.values()), 1)

    return {
        "dimension_scores": dimension_scores,
        "overall_score_0_100": overall_score,
        "method": {"base_score": BASE_SCORE, "penalties": penalties},
    }


# =========================
# Agent 3: Benchmarking (Mock)
# =========================


def benchmark_culture(scoring_result: dict) -> dict:
    """
    Mock benchmarking agent.
    Simulates comparison against a Glassdoor-like cohort.
    """

    # Simulated cohort characteristics
    cohort_size = 820

    # Typical issue frequencies (mocked from common Glassdoor patterns)
    issue_frequencies = {
        "micromanagement": 38,
        "burnout": 44,
        "low_autonomy": 41,
        "workload_pressure": 47,
        "low_psychological_safety": 29,
        "role_clarity": 22,
    }

    # Percentile estimation (lower score = worse percentile)
    percentiles = {}
    for dimension, data in scoring_result["dimension_scores"].items():
        score = data["score_0_100"]
        percentile = max(5, min(95, int(score)))
        percentiles[dimension] = {"percentile": percentile, "score_0_100": score}

    # Correlated issues (mock co-occurrence rates)
    correlations = []
    if "wellbeing" in percentiles:
        correlations.append(
            {"issue_pair": ["burnout", "micromanagement"], "co_occurrence_percent": 52}
        )

    return {
        "cohort": {
            "size_n": cohort_size,
            "description": "Simulated Glassdoor cohort (technology & professional services)",
        },
        "issue_frequencies_percent": issue_frequencies,
        "dimension_percentiles": percentiles,
        "correlations": correlations,
    }


# =========================
# Agent 4: Strategy Agent
# =========================


def strategy_recommendations(
    nlp_result: dict, scoring_result: dict, benchmark_result: dict
) -> dict:
    """
    Generates concrete, prioritized culture improvement actions
    based on scores + benchmark frequencies.
    """

    recommendations = []

    # --- leadership / micromanagement ---
    if "micromanagement" in nlp_result["signals"]:
        freq = benchmark_result["issue_frequencies_percent"]["micromanagement"]

        recommendations.append(
            {
                "issue": "Micromanagement",
                "why_it_matters": (
                    f"Micromanagement appears in {freq}% of benchmarked reviews "
                    "and is strongly correlated with burnout."
                ),
                "what_to_change": [
                    "Introduce manager autonomy guidelines",
                    "Reduce approval layers for routine decisions",
                    "Train managers on outcome-based leadership",
                ],
                "kpis": [
                    "Manager approval cycle time",
                    "Employee autonomy survey score",
                    "Internal escalation frequency",
                ],
                "expected_impact": {
                    "leadership_score_change": +10,
                    "autonomy_score_change": +8,
                },
                "priority": "high",
            }
        )

    # --- burnout / workload ---
    if "burnout" in nlp_result["signals"]:
        freq = benchmark_result["issue_frequencies_percent"]["burnout"]

        recommendations.append(
            {
                "issue": "Burnout & workload pressure",
                "why_it_matters": (
                    f"Burnout is present in {freq}% of similar companies and "
                    "is the primary driver of low wellbeing scores."
                ),
                "what_to_change": [
                    "Implement workload caps per role",
                    "Enforce no-meeting focus blocks",
                    "Track overtime and redistribute load",
                ],
                "kpis": [
                    "Average weekly hours",
                    "Overtime frequency",
                    "Sick leave and disengagement signals",
                ],
                "expected_impact": {"wellbeing_score_change": +15},
                "priority": "critical",
            }
        )

    # --- overall prioritization ---
    recommendations = sorted(recommendations, key=lambda r: r["priority"] != "critical")

    return {
        "summary": {
            "total_recommendations": len(recommendations),
            "focus_area": "wellbeing and leadership effectiveness",
        },
        "recommendations": recommendations,
    }


# =========================
# Agent 5: Outcome Simulation
# =========================


def simulate_outcomes(
    scoring_result: dict, strategy_result: dict, benchmark_result: dict
) -> dict:
    """
    Simulates expected culture improvements if recommended strategies are applied.
    Uses benchmark-informed deltas (mocked for now).
    """

    current_scores = {
        dim: data["score_0_100"]
        for dim, data in scoring_result["dimension_scores"].items()
    }

    projected_scores = current_scores.copy()
    applied_changes = []

    # Apply expected impacts from strategy
    for rec in strategy_result["recommendations"]:
        impact = rec.get("expected_impact", {})

        for key, delta in impact.items():
            if key.endswith("_score_change"):
                dimension = key.replace("_score_change", "")
                if dimension in projected_scores:
                    projected_scores[dimension] = min(
                        100, projected_scores[dimension] + delta
                    )
                    applied_changes.append(
                        {
                            "dimension": dimension,
                            "delta": delta,
                            "source_issue": rec["issue"],
                        }
                    )

    # Calculate percentage improvements
    improvements = {}
    for dim, old_score in current_scores.items():
        new_score = projected_scores[dim]
        improvements[dim] = {
            "from": old_score,
            "to": new_score,
            "absolute_change": new_score - old_score,
            "percent_change": round(
                ((new_score - old_score) / max(old_score, 1)) * 100, 1
            ),
        }

    # Simulated risk reduction (proxy logic)
    burnout_reduction = 18 if "wellbeing" in improvements else 0

    return {
        "projected_scores": projected_scores,
        "improvements": improvements,
        "risk_reduction_estimates": {
            "burnout_risk_reduction_percent": burnout_reduction,
            "attrition_risk_reduction_percent": round(burnout_reduction * 0.6, 1),
        },
        "time_to_effect": {"short_term": "4–8 weeks", "mid_term": "3–6 months"},
        "assumptions": [
            "Leadership adopts recommended changes consistently",
            "Workload interventions are enforced, not optional",
            "No major organizational restructuring during period",
        ],
    }


# =========================
# Agent 0: Explainer Agent (AI)
# =========================


def explain_results(
    nlp_result: dict,
    scoring_result: dict,
    benchmark_result: dict,
    strategy_result: dict,
    simulation_result: dict,
) -> dict:
    """
    AI-powered explainer that translates analytical outputs
    into plain English. READ-ONLY. No new facts allowed.
    """

    system_prompt = """
You are a senior organizational culture consultant.

Your task:
- Explain analytical results in plain English
- Be clear, structured, and professional
- Speak to executives and managers

STRICT RULES:
- You may ONLY use the numbers and facts provided
- Do NOT invent new statistics
- Do NOT contradict the data
- Do NOT add recommendations beyond those given
- If something is uncertain, say so clearly
"""

    user_prompt = f"""
Here are the analysis results (JSON). Explain them in plain English.

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

Your output MUST include:
1) Executive summary (5–6 sentences)
2) Key problems (bullet points)
3) What the data says (benchmarks & percentiles)
4) What should be fixed first and why
5) What improvement to expect if actions are taken

Do NOT output JSON.
"""

    explanation_text = call_ai(system_prompt, user_prompt)

    return {"executive_explanation": explanation_text}


# =====================
# Pipeline Orchestrator
# =====================


import re
from statistics import mean
import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
LAST_ANALYSIS = None


def call_ai(system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


# =========================
# Agent 1: NLP Normalization
# =========================


def nlp_normalize(problem_text: str) -> dict:
    text = problem_text.lower()
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

    clean_statement = (
        f"Employees report issues related to {problem_text.strip().lower()}."
    )

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


# =====================
# Agent 2: Scoring Agent
# =====================


def score_culture(taxonomy: dict) -> dict:
    """
    Produces 0–100 culture scores per dimension based on detected issues.
    Lower score = worse culture.
    """

    # baseline healthy score
    BASE_SCORE = 75

    # penalties per issue
    penalties = {
        "micromanagement": 20,
        "low_autonomy": 15,
        "burnout": 25,
        "workload_pressure": 15,
        "low_psychological_safety": 25,
        "role_clarity": 10,
    }

    dimension_scores = {}

    for dimension, issues in taxonomy.items():
        score = BASE_SCORE
        applied_penalties = []

        for issue in issues:
            if issue in penalties:
                score -= penalties[issue]
                applied_penalties.append(issue)

        score = max(score, 0)

        confidence = min(0.4 + 0.15 * len(issues), 0.95)

        dimension_scores[dimension] = {
            "score_0_100": score,
            "confidence": round(confidence, 2),
            "drivers": applied_penalties,
        }

    overall_score = round(mean(d["score_0_100"] for d in dimension_scores.values()), 1)

    return {
        "dimension_scores": dimension_scores,
        "overall_score_0_100": overall_score,
        "method": {"base_score": BASE_SCORE, "penalties": penalties},
    }


# =========================
# Agent 3: Benchmarking (Mock)
# =========================


def benchmark_culture(scoring_result: dict) -> dict:
    """
    Mock benchmarking agent.
    Simulates comparison against a Glassdoor-like cohort.
    """

    # Simulated cohort characteristics
    cohort_size = 820

    # Typical issue frequencies (mocked from common Glassdoor patterns)
    issue_frequencies = {
        "micromanagement": 38,
        "burnout": 44,
        "low_autonomy": 41,
        "workload_pressure": 47,
        "low_psychological_safety": 29,
        "role_clarity": 22,
    }

    # Percentile estimation (lower score = worse percentile)
    percentiles = {}
    for dimension, data in scoring_result["dimension_scores"].items():
        score = data["score_0_100"]
        percentile = max(5, min(95, int(score)))
        percentiles[dimension] = {"percentile": percentile, "score_0_100": score}

    # Correlated issues (mock co-occurrence rates)
    correlations = []
    if "wellbeing" in percentiles:
        correlations.append(
            {"issue_pair": ["burnout", "micromanagement"], "co_occurrence_percent": 52}
        )

    return {
        "cohort": {
            "size_n": cohort_size,
            "description": "Simulated Glassdoor cohort (technology & professional services)",
        },
        "issue_frequencies_percent": issue_frequencies,
        "dimension_percentiles": percentiles,
        "correlations": correlations,
    }


# =========================
# Agent 4: Strategy Agent
# =========================


def strategy_recommendations(
    nlp_result: dict, scoring_result: dict, benchmark_result: dict
) -> dict:
    """
    Generates concrete, prioritized culture improvement actions
    based on scores + benchmark frequencies.
    """

    recommendations = []

    # --- leadership / micromanagement ---
    if "micromanagement" in nlp_result["signals"]:
        freq = benchmark_result["issue_frequencies_percent"]["micromanagement"]

        recommendations.append(
            {
                "issue": "Micromanagement",
                "why_it_matters": (
                    f"Micromanagement appears in {freq}% of benchmarked reviews "
                    "and is strongly correlated with burnout."
                ),
                "what_to_change": [
                    "Introduce manager autonomy guidelines",
                    "Reduce approval layers for routine decisions",
                    "Train managers on outcome-based leadership",
                ],
                "kpis": [
                    "Manager approval cycle time",
                    "Employee autonomy survey score",
                    "Internal escalation frequency",
                ],
                "expected_impact": {
                    "leadership_score_change": +10,
                    "autonomy_score_change": +8,
                },
                "priority": "high",
            }
        )

    # --- burnout / workload ---
    if "burnout" in nlp_result["signals"]:
        freq = benchmark_result["issue_frequencies_percent"]["burnout"]

        recommendations.append(
            {
                "issue": "Burnout & workload pressure",
                "why_it_matters": (
                    f"Burnout is present in {freq}% of similar companies and "
                    "is the primary driver of low wellbeing scores."
                ),
                "what_to_change": [
                    "Implement workload caps per role",
                    "Enforce no-meeting focus blocks",
                    "Track overtime and redistribute load",
                ],
                "kpis": [
                    "Average weekly hours",
                    "Overtime frequency",
                    "Sick leave and disengagement signals",
                ],
                "expected_impact": {"wellbeing_score_change": +15},
                "priority": "critical",
            }
        )

    # --- overall prioritization ---
    recommendations = sorted(recommendations, key=lambda r: r["priority"] != "critical")

    return {
        "summary": {
            "total_recommendations": len(recommendations),
            "focus_area": "wellbeing and leadership effectiveness",
        },
        "recommendations": recommendations,
    }


# =========================
# Agent 5: Outcome Simulation
# =========================


def simulate_outcomes(
    scoring_result: dict, strategy_result: dict, benchmark_result: dict
) -> dict:
    """
    Simulates expected culture improvements if recommended strategies are applied.
    Uses benchmark-informed deltas (mocked for now).
    """

    current_scores = {
        dim: data["score_0_100"]
        for dim, data in scoring_result["dimension_scores"].items()
    }

    projected_scores = current_scores.copy()
    applied_changes = []

    # Apply expected impacts from strategy
    for rec in strategy_result["recommendations"]:
        impact = rec.get("expected_impact", {})

        for key, delta in impact.items():
            if key.endswith("_score_change"):
                dimension = key.replace("_score_change", "")
                if dimension in projected_scores:
                    projected_scores[dimension] = min(
                        100, projected_scores[dimension] + delta
                    )
                    applied_changes.append(
                        {
                            "dimension": dimension,
                            "delta": delta,
                            "source_issue": rec["issue"],
                        }
                    )

    # Calculate percentage improvements
    improvements = {}
    for dim, old_score in current_scores.items():
        new_score = projected_scores[dim]
        improvements[dim] = {
            "from": old_score,
            "to": new_score,
            "absolute_change": new_score - old_score,
            "percent_change": round(
                ((new_score - old_score) / max(old_score, 1)) * 100, 1
            ),
        }

    # Simulated risk reduction (proxy logic)
    burnout_reduction = 18 if "wellbeing" in improvements else 0

    return {
        "projected_scores": projected_scores,
        "improvements": improvements,
        "risk_reduction_estimates": {
            "burnout_risk_reduction_percent": burnout_reduction,
            "attrition_risk_reduction_percent": round(burnout_reduction * 0.6, 1),
        },
        "time_to_effect": {"short_term": "4–8 weeks", "mid_term": "3–6 months"},
        "assumptions": [
            "Leadership adopts recommended changes consistently",
            "Workload interventions are enforced, not optional",
            "No major organizational restructuring during period",
        ],
    }


# =========================
# Agent 0: Explainer & Advisor Agent (AI)
# =========================

import json
from typing import Dict
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# This is updated by the pipeline after analysis
LAST_ANALYSIS: Dict | None = None


def call_ai(system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


# =====================================================
# Agent 0A: Explainer (One-time executive explanation)
# =====================================================

def explain_results(
    nlp_result: dict,
    scoring_result: dict,
    benchmark_result: dict,
    strategy_result: dict,
    simulation_result: dict,
) -> dict:
    """
    Generates a structured executive explanation.
    READ-ONLY. No new facts allowed.
    Used ONCE per analysis.
    """

    system_prompt = """
You are a senior organizational culture consultant.

Your task:
- Explain analytical results in plain English
- Be clear, structured, and professional
- Speak to executives and managers

STRICT RULES:
- Use ONLY the numbers and facts provided
- Do NOT invent statistics
- Do NOT contradict the data
- Do NOT add new recommendations
- If something is uncertain, say so explicitly
"""

    user_prompt = f"""
Here are the analysis results (JSON). Explain them in plain English.

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

Your output MUST include:
1) Executive summary (5–6 sentences)
2) Key problems (bullet points)
3) What the data says (benchmarks & percentiles)
4) What should be fixed first and why
5) What improvement to expect if actions are taken

Do NOT output JSON.
"""

    explanation_text = call_ai(system_prompt, user_prompt)

    return {
        "executive_explanation": explanation_text
    }


# =====================================================
# Agent 0B: Advisor (Chat / Q&A over existing analysis)
# =====================================================

def advisor_chat(question: str) -> str:
    """
    Conversational AI advisor.
    Answers questions using ONLY the last analysis.
    Does NOT re-run analysis.
    """

    if LAST_ANALYSIS is None:
        return (
            "No culture analysis is available yet. "
            "Please run an analysis before asking questions."
        )

    system_prompt = """
You are Agent 0: AI Culture Advisor.

You answer executive and manager questions about an existing
organizational culture analysis.

RULES:
- Use ONLY the provided data
- Quote numbers and percentiles when relevant
- Do NOT invent facts or assumptions
- Do NOT repeat the full report unless explicitly asked
- If the data does not support the question, say so clearly
- Be concise, professional, and decision-oriented
"""

    user_prompt = f"""
Here is the culture analysis (JSON):

{json.dumps(LAST_ANALYSIS, indent=2)}

User question:
"{question}"

Answer clearly and directly.
"""

    return call_ai(system_prompt, user_prompt)


# =====================
# Pipeline Orchestrator
# =====================


async def run_pipeline(problem_text: str):
    nlp_result = nlp_normalize(problem_text)
    scoring_result = score_culture(nlp_result["taxonomy"])
    benchmark_result = benchmark_culture(scoring_result)
    strategy_result = strategy_recommendations(
        nlp_result,
        scoring_result,
        benchmark_result
        
    )
    simulation_result = simulate_outcomes(
        scoring_result,
        strategy_result,
        benchmark_result
    )
    explainer_result = explain_results(
        nlp_result,
        scoring_result,
        benchmark_result,
        strategy_result,
        simulation_result
    )

    return {
        "stage": "explanation_complete",
        "nlp_result": nlp_result,
        "scoring_result": scoring_result,
        "benchmark_result": benchmark_result,
        "strategy_result": strategy_result,
        "simulation_result": simulation_result,
        "explanation": explainer_result
    }
