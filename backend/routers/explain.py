# routers/explain.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from middleware.rate_limit import check_and_increment, get_status
from services import gemini, groq, openrouter

router = APIRouter()

MAX_HIGHLIGHT_WORDS = 500
MAX_CONTEXT_CHARS = 1000  # per side


class ExplainRequest(BaseModel):
    highlighted: str
    context_before: str = ""
    context_after: str = ""
    model: str  # "gemini" | "groq" | "openrouter"
    simplify_note: str = ""

    @field_validator("highlighted", "context_before", "context_after", "simplify_note")
    @classmethod
    def must_be_string(cls, v):
        # Enforce plain string — treat all page content as text only
        if not isinstance(v, str):
            raise ValueError("Field must be a string")
        return v

    @field_validator("model")
    @classmethod
    def valid_model(cls, v):
        if v not in ("gemini", "groq", "openrouter"):
            raise ValueError("model must be one of: gemini, groq, openrouter")
        return v


def build_prompt(req: ExplainRequest) -> str:
    # Truncate context server-side as a safety net (frontend already limits this)
    before = req.context_before[-MAX_CONTEXT_CHARS:]
    after = req.context_after[:MAX_CONTEXT_CHARS]

    parts = []
    if before.strip():
        parts.append(f"Context before:\n{before}")
    parts.append(f">>> Text to explain:\n{req.highlighted}")
    if after.strip():
        parts.append(f"Context after:\n{after}")

    context_block = "\n\n".join(parts)

    return (
        f"{context_block}\n\n"
        f"Explain the highlighted text to someone with no background knowledge. "
        f"Use simple, everyday language — short sentences, no jargon. "
        f"Use the surrounding context to make the explanation more accurate and relevant."
        f"{req.simplify_note}"
    )

@router.get("/usage")
async def usage():
    return get_status()

@router.post("/explain")
async def explain(req: ExplainRequest):
    # Word count check (server-side, not just frontend)
    highlighted_stripped = req.highlighted.strip()
    word_count = len(highlighted_stripped.split())

    if word_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No text highlighted. Please highlight some text first.",
        )

    if word_count > MAX_HIGHLIGHT_WORDS:
        raise HTTPException(
            status_code=400,
            detail=f"Highlighted text is {word_count} words. Please highlight under {MAX_HIGHLIGHT_WORDS} words.",
        )

    # Rate limit check — both global and per-model
    allowed, global_remaining, model_remaining = check_and_increment(req.model)
    if not allowed:
        if model_remaining <= 0 and global_remaining > 0:
            raise HTTPException(
                status_code=429,
                detail=f"{req.model.capitalize()}'s daily limit reached. Try a different model.",
            )
        raise HTTPException(
            status_code=429,
            detail="Daily limit reached. Try again tomorrow.",
        )

    prompt = build_prompt(req)

    # Route to the right service
    try:
        if req.model == "gemini":
            explanation = await gemini.explain(prompt)
        elif req.model == "groq":
            explanation = await groq.explain(prompt)
        elif req.model == "openrouter":
            explanation = await openrouter.explain(prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")

    return {
        "explanation": explanation,
        "calls_remaining_today": global_remaining,
        "model_calls_remaining_today": model_remaining,
    }
