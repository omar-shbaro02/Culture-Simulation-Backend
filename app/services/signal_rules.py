LEADERSHIP_TRUST_RULES = [
    {
        "driver": "transparency",
        "signals": ["weekly update", "context update", "share constraints", "trade-off", "explain why", "decision rationale"],
        "delta": 4,
    },
    {
        "driver": "transparency",
        "signals": ["roadmap", "visibility", "clarity on priorities", "communicate priorities"],
        "delta": 3,
    },
    {
        "driver": "reliability",
        "signals": ["kept promise", "delivered", "on time", "commitment", "met deadline", "follow-through"],
        "delta": 4,
    },
    {
        "driver": "reliability",
        "signals": ["public commitments", "track commitments", "accountability"],
        "delta": 3,
    },
    {
        "driver": "autonomy",
        "signals": ["decision boundaries", "ownership", "empowered", "reduce approvals", "no micromanagement", "less micromanaging"],
        "delta": 5,
    },
    {
        "driver": "autonomy",
        "signals": ["delegated", "trust team", "autonomous decisions"],
        "delta": 3,
    },
    {
        "driver": "empathy",
        "signals": ["listening session", "1:1", "people impact", "check in", "care", "empathy", "support"],
        "delta": 4,
    },
]

RULES_BY_DIMENSION = {
    "leadership_trust": LEADERSHIP_TRUST_RULES,
}
