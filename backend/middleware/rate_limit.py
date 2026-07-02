# middleware/rate_limit.py
# Tracks a global daily call counter plus per-model daily counters.
# Resets at midnight UTC. Stored in memory (single process, fine for personal use).

from datetime import datetime, timezone

DAILY_LIMIT_GLOBAL = 500

# Per-model daily caps. Hardcoded because none of the providers expose a clean
# "quota remaining" endpoint. Revisit if a provider changes its free tier.
MODEL_LIMITS = {
    "gemini": 100,      # Gemini 2.0 Flash free tier: 100 RPD
    "groq": 1000,       # Groq free tier, Llama 3.3 70B — conservative planning number
    "openrouter": 50,   # OpenRouter free model cap: 50/day (1000/day with $10+ credits)
}

_state = {
    "date": datetime.now(timezone.utc).date(),
    "global_count": 0,
    "model_counts": {model: 0 for model in MODEL_LIMITS},
}


def _reset_if_new_day():
    today = datetime.now(timezone.utc).date()
    if _state["date"] != today:
        _state["date"] = today
        _state["global_count"] = 0
        _state["model_counts"] = {model: 0 for model in MODEL_LIMITS}


def check_and_increment(model: str) -> tuple[bool, int, int]:
    """
    Checks both the global daily limit and the per-model daily limit.
    Only increments both counters if the call is allowed by both.
    Returns (allowed, global_remaining, model_remaining).
    """
    _reset_if_new_day()

    global_remaining = DAILY_LIMIT_GLOBAL - _state["global_count"]
    model_remaining = MODEL_LIMITS[model] - _state["model_counts"][model]

    if global_remaining <= 0 or model_remaining <= 0:
        return False, max(0, global_remaining), max(0, model_remaining)

    _state["global_count"] += 1
    _state["model_counts"][model] += 1

    global_remaining = DAILY_LIMIT_GLOBAL - _state["global_count"]
    model_remaining = MODEL_LIMITS[model] - _state["model_counts"][model]

    return True, global_remaining, model_remaining


def get_status() -> dict:
    _reset_if_new_day()

    models = {}
    for model, limit in MODEL_LIMITS.items():
        used = _state["model_counts"][model]
        models[model] = {
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used),
            "percent_used": round(min(100, (used / limit) * 100), 1) if limit else 0,
        }

    return {
        "global": {
            "used": _state["global_count"],
            "limit": DAILY_LIMIT_GLOBAL,
            "remaining": max(0, DAILY_LIMIT_GLOBAL - _state["global_count"]),
        },
        "models": models,
        "resets": "midnight UTC",
    }
