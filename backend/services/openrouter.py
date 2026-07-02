# services/openrouter.py
import os
import asyncio
from openai import OpenAI, RateLimitError

# Lazy init
_client = None

MAX_RETRIES = 2
BASE_DELAY_SECONDS = 2  # matches the retry_after_seconds OpenRouter typically sends


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
    return _client


async def explain(prompt: str) -> str:
    client = _get_client()

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model="google/gemma-4-26b-a4b-it:free",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Explain the following like the reader is 5 years old. "
                            "Rules: plain text only, no markdown (no asterisks, no bullet points, "
                            "no headers, no bold). Write 2-4 short sentences max. "
                            "Just explain it directly, don't restate the question or add caveats."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=150,
                extra_body={"reasoning": {"enabled": False}},
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError(f"Empty response from Gemma: {response}")
            return content.strip()

        except RateLimitError as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                # Backoff: 2s, then 4s
                delay = BASE_DELAY_SECONDS * (2 ** attempt)
                await asyncio.sleep(delay)
                continue
            # Retries exhausted — raise a clean, user-facing message instead of
            # the raw OpenRouter/provider error blob
            raise RuntimeError(
                "Gemma is temporarily overloaded on the free tier. Try again in a few seconds, "
                "or switch to Gemini or Groq for now."
            ) from e

    # Shouldn't reach here, but just in case
    raise RuntimeError("Gemma failed after retries.") from last_error
