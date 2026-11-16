from __future__ import annotations

import httpx
from core.config import get_settings
from core.logger import get_logger

logger = get_logger(__name__)

_GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


async def generate_experience_text(prompt: str) -> str:
    """Call the Groq chat completions API and return the generated text.

    Uses async httpx for non-blocking I/O.
    """
    settings = get_settings()

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    model_name = settings.GROQ_MODEL.strip()
    if model_name.startswith("groq/"):
        model_name = model_name[len("groq/"):]

    # Fallback chain for narrative generation
    candidate_models = [
        model_name,
        "openai/gpt-oss-20b" if "120b" in model_name else "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
    ]
    candidate_models = list(dict.fromkeys(candidate_models))

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a world-class luxury travel narrator. "
                    "Respond with rich, immersive prose only. "
                    "No markdown, no bullet points, no headers."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 1024,
        "top_p": 0.9,
    }

    last_exception = None
    async with httpx.AsyncClient(timeout=60.0) as client:
        for candidate in candidate_models:
            payload["model"] = candidate
            logger.info("Sending request to Groq API (model=%s)", candidate)
            try:
                response = await client.post(_GROQ_CHAT_URL, headers=headers, json=payload)
                if response.status_code == 429:
                    logger.warning("Groq rate limit (429) on %s, shifting to next fallback model...", candidate)
                    continue
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"].strip()
                logger.info("Groq response received from %s (%d chars)", candidate, len(text))
                return text
            except Exception as exc:
                last_exception = exc
                logger.warning("Error with model %s: %s; trying next fallback...", candidate, exc)
                continue

    if last_exception:
        raise last_exception
    return "An extraordinary bespoke journey crafted for discerning travelers."
