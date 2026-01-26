import re
from app.schemas.nlp import NLPNormalizationResult, SeverityHints


class NLPNormalizationAgent:
    """
    Agent 1: NLP Normalization & Signal Extraction
    Purpose:
    - Normalize human language
    - Extract culture-relevant signals
    - Map them into internal taxonomy buckets
    """

    def run(self, text: str) -> NLPNormalizationResult:
        lowered = text.lower()

        signals = []

        # --- signal detection (rule-based for now; LLM later) ---
        if any(k in lowered for k in ["micromanage", "micromanaged", "over control"]):
            signals.append("micromanagement")

        if any(k in lowered for k in ["burnout", "burned out", "exhausted", "overworked"]):
            signals.append("burnout")

        if any(k in lowered for k in ["fear", "afraid", "retaliation"]):
            signals.append("fear_of_speaking")

        if any(k in lowered for k in ["unclear", "confusing", "no direction"]):
            signals.append("role_clarity_issues")

        if not signals:
            signals.append("general_dissatisfaction")

        # --- taxonomy mapping ---
        taxonomy = {
            "leadership": [],
            "wellbeing": [],
            "autonomy": [],
            "communication": []
        }

        for s in signals:
            if s == "micromanagement":
                taxonomy["leadership"].append("micromanagement")
                taxonomy["autonomy"].append("low_autonomy")

            if s == "burnout":
                taxonomy["wellbeing"].append("burnout")
                taxonomy["wellbeing"].append("workload_pressure")

            if s == "fear_of_speaking":
                taxonomy["communication"].append("low_psychological_safety")

            if s == "role_clarity_issues":
                taxonomy["communication"].append("role_clarity")

        taxonomy = {k: v for k, v in taxonomy.items() if v}

        # --- severity heuristics ---
        emotional_intensity = "moderate"
        urgency = "medium"
        scope = "team"

        if any(k in lowered for k in ["always", "never", "toxic", "breaking"]):
            emotional_intensity = "high"
            urgency = "high"

        clean_statement = self._normalize_statement(text)

        return NLPNormalizationResult(
            clean_problem_statement=clean_statement,
            signals=signals,
            taxonomy=taxonomy,
            severity_hints=SeverityHints(
                emotional_intensity=emotional_intensity,
                scope=scope,
                urgency=urgency
            )
        )

    def _normalize_statement(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text.strip())
        return f"Employees report issues related to {text.lower()}."
