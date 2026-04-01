from typing import List, Dict

from app.services.pipeline import call_ai_json
from app.services.signal_rules import RULES_BY_DIMENSION

def infer_signals(dimension_slug: str, text: str) -> List[Dict]:
    if not text:
        return []

    fallback_hits = _infer_signals_rules(dimension_slug, text)

    system_prompt = """
You are an AI signal interpreter for workplace culture dimensions.
Return strict JSON only.
"""
    user_prompt = f"""
Dimension slug: {dimension_slug}
User text:\n{text}

Return JSON with this shape:
{{
  "hits": [
    {{"driver": "snake_case", "delta": 1, "matched": "short evidence phrase"}}
  ]
}}

Rules:
- Keep delta in range 1 to 5.
- Include only hits grounded in user text.
- Return an empty hits array if no credible signal is present.
"""
    result = call_ai_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        fallback={"hits": fallback_hits},
        temperature=0.2,
    )

    hits = result.get("hits", [])
    if not isinstance(hits, list):
        return fallback_hits

    cleaned = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        driver = str(hit.get("driver", "")).strip()
        matched = str(hit.get("matched", "")).strip()
        try:
            delta = int(hit.get("delta", 1))
        except Exception:
            delta = 1
        delta = max(1, min(5, delta))

        if not driver:
            continue

        cleaned.append({"driver": driver, "delta": delta, "matched": matched})

    return cleaned if cleaned else fallback_hits


def _infer_signals_rules(dimension_slug: str, text: str) -> List[Dict]:
    rules = RULES_BY_DIMENSION.get(dimension_slug, [])
    if not rules:
        return []

    t = text.lower()
    hits = []

    for rule in rules:
        for phrase in rule["signals"]:
            if phrase in t:
                hits.append({
                    "driver": rule["driver"],
                    "delta": int(rule["delta"]),
                    "matched": phrase
                })
                break

    return hits

def clamp_total_delta(hits: List[Dict], max_total: int = 10) -> List[Dict]:
    total = 0
    out = []

    for h in hits:
        if total >= max_total:
            break
        d = h["delta"]
        if total + d > max_total:
            d = max_total - total
        out.append({**h, "delta": d})
        total += d

    return out
