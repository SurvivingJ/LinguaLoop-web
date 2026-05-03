"""OpenRouter model list + pricing fetcher (with in-process cache)."""

import logging
import os
import time
import urllib.request
import json
from typing import Optional

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 3600
_models_cache: Optional[list[dict]] = None
_cache_timestamp: float = 0.0


def fetch_model_list(api_key: Optional[str] = None, force_refresh: bool = False) -> list[dict]:
    """Fetch the OpenRouter model list. Cached for 1 hour."""
    global _models_cache, _cache_timestamp

    if not force_refresh and _models_cache is not None:
        if (time.time() - _cache_timestamp) < CACHE_TTL_SECONDS:
            return _models_cache

    api_key = api_key or os.getenv('OPENROUTER_API_KEY', '')

    req = urllib.request.Request(
        'https://openrouter.ai/api/v1/models',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/json',
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode('utf-8')
    payload = json.loads(body)
    models = payload.get('data', [])

    _models_cache = models
    _cache_timestamp = time.time()
    logger.info("Fetched %d models from OpenRouter", len(models))
    return models


def get_pricing_map(api_key: Optional[str] = None) -> dict[str, dict]:
    """Return {model_id: {prompt: $/token, completion: $/token}}."""
    models = fetch_model_list(api_key)
    out: dict[str, dict] = {}
    for m in models:
        pricing = m.get('pricing') or {}
        try:
            prompt_cost = float(pricing.get('prompt', '0') or 0)
        except (TypeError, ValueError):
            prompt_cost = 0.0
        try:
            completion_cost = float(pricing.get('completion', '0') or 0)
        except (TypeError, ValueError):
            completion_cost = 0.0
        out[m['id']] = {'prompt': prompt_cost, 'completion': completion_cost}
    return out


def compute_cost(prompt_tokens: int, completion_tokens: int, pricing: dict) -> float:
    """Compute USD cost for a single LLM call from token counts and per-token pricing."""
    if not pricing:
        return 0.0
    return (prompt_tokens * pricing.get('prompt', 0.0)
            + completion_tokens * pricing.get('completion', 0.0))
