from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict

DEFAULT_BASELINE = 50

CANONICAL_DIMENSIONS = [
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

DELTA_SCOPE_MULTIPLIER = {
    "team": 1.0,
    "department": 1.5,
    "organization": 2.0,
}

ABSOLUTE_SCOPE_MULTIPLIER = {
    "team": 0.5,
    "department": 0.75,
    "organization": 1.0,
}


def _new_state() -> Dict[str, Any]:
    return {
        "current_score": DEFAULT_BASELINE,
        "previous_score": DEFAULT_BASELINE,
        "history": [DEFAULT_BASELINE],
        "last_change": {
            "source": "baseline",
            "scope": "organization",
            "raw_delta": 0,
            "effective_delta": 0,
            "from_score": DEFAULT_BASELINE,
            "to_score": DEFAULT_BASELINE,
            "reason": "Initial baseline set to 50.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "changes": [],
    }


# Temporary in-memory state
# Later this can move to DB persistence
dimension_memory: Dict[str, Dict[str, Any]] = {
    slug: _new_state() for slug in CANONICAL_DIMENSIONS
}


def _ensure_dimension(slug: str):
    if slug not in dimension_memory:
        dimension_memory[slug] = _new_state()


def _clamp_score(value: int) -> int:
    return max(0, min(100, int(value)))


def _scope_or_default(scope: str | None) -> str:
    if scope in {"team", "department", "organization"}:
        return scope
    return "team"


def _record_change(
    slug: str,
    source: str,
    scope: str,
    raw_delta: int,
    effective_delta: int,
    old_score: int,
    new_score: int,
    reason: str,
):
    state = dimension_memory[slug]
    change = {
        "source": source,
        "scope": scope,
        "raw_delta": int(raw_delta),
        "effective_delta": int(effective_delta),
        "from_score": int(old_score),
        "to_score": int(new_score),
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    state["last_change"] = change
    state["changes"].append(change)
    state["changes"] = state["changes"][-20:]


def get_dimension_state(slug: str):
    _ensure_dimension(slug)
    return deepcopy(dimension_memory[slug])


def get_all_dimension_states():
    return deepcopy(dimension_memory)


def reset_all_dimension_states():
    global dimension_memory
    dimension_memory = {
        slug: _new_state() for slug in CANONICAL_DIMENSIONS
    }
    return deepcopy(dimension_memory)


def apply_delta(
    slug: str,
    delta: int,
    source: str = "interaction",
    scope: str = "team",
    reason: str = "New evidence from advisor interaction.",
):
    _ensure_dimension(slug)
    state = dimension_memory[slug]

    normalized_scope = _scope_or_default(scope)
    multiplier = DELTA_SCOPE_MULTIPLIER[normalized_scope]
    raw_delta = int(delta)
    effective_delta = int(round(raw_delta * multiplier))

    old_score = int(state["current_score"])
    new_score = _clamp_score(old_score + effective_delta)

    state["previous_score"] = old_score
    state["current_score"] = new_score
    state["history"].append(new_score)

    _record_change(
        slug=slug,
        source=source,
        scope=normalized_scope,
        raw_delta=raw_delta,
        effective_delta=effective_delta,
        old_score=old_score,
        new_score=new_score,
        reason=reason,
    )

    return deepcopy(state)


def apply_absolute_score(
    slug: str,
    score: int,
    source: str = "study",
    scope: str = "team",
    reason: str = "Score recalibrated from latest culture study.",
):
    _ensure_dimension(slug)
    state = dimension_memory[slug]

    normalized_scope = _scope_or_default(scope)
    multiplier = ABSOLUTE_SCOPE_MULTIPLIER[normalized_scope]

    old_score = int(state["current_score"])
    target_score = _clamp_score(score)

    raw_delta = target_score - old_score
    effective_delta = int(round(raw_delta * multiplier))
    new_score = _clamp_score(old_score + effective_delta)

    state["previous_score"] = old_score
    state["current_score"] = new_score
    state["history"].append(new_score)

    _record_change(
        slug=slug,
        source=source,
        scope=normalized_scope,
        raw_delta=raw_delta,
        effective_delta=effective_delta,
        old_score=old_score,
        new_score=new_score,
        reason=reason,
    )

    return deepcopy(state)
