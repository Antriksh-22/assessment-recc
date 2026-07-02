import logging
from typing import Iterable

import httpx

from .catalog import CatalogItem
from .config import Settings
from .response_builder import catalog_snippets

logger = logging.getLogger(__name__)


async def polish_reply(
    settings: Settings,
    deterministic_reply: str,
    conversation_summary: str,
    decision_type: str,
    recommendations: Iterable[CatalogItem],
) -> str:
    if not settings.use_llm or not settings.sarvam_api_key:
        return deterministic_reply

    prompt = (
        "Polish this SHL assessment recommender reply. Do not choose or change recommendations. "
        "Do not output JSON. Keep it concise and grounded in the supplied catalog snippets.\n\n"
        f"Conversation summary:\n{conversation_summary[:1500]}\n\n"
        f"Decision type: {decision_type}\n\n"
        f"Validated recommendations:\n{catalog_snippets(recommendations)}\n\n"
        f"Draft reply:\n{deterministic_reply}"
    )
    headers = {
        "api-subscription-key": settings.sarvam_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.sarvam_model,
        "messages": [
            {"role": "system", "content": "You only polish reply text. Do not choose recommendations."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 300,
    }
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.post(settings.sarvam_base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content or deterministic_reply
    except Exception as exc:
        logger.warning("Sarvam polishing failed: %s", exc)
        return deterministic_reply

