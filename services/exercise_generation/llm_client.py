# services/exercise_generation/llm_client.py

import json
import logging
import os
from openai import OpenAI

logger = logging.getLogger(__name__)

# Module-level singleton client
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv('OPENROUTER_API_KEY', '')
        _client = OpenAI(
            api_key=api_key,
            base_url='https://openrouter.ai/api/v1',
        )
    return _client


def call_llm(
    prompt: str,
    model: str = 'google/gemini-flash-1.5',
    response_format: str = 'json',
) -> dict | list:
    """
    Call the LLM via OpenRouter. Returns parsed JSON or raw text.

    Args:
        prompt:          complete prompt string
        model:           LLM model string
        response_format: 'json' or 'text'

    Returns:
        Parsed JSON dict/list for 'json' format, or raw text string for 'text'.
    """
    client = _get_client()

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        timeout=30,
    )

    if not response.choices:
        raise RuntimeError("No response from LLM")

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Empty response from LLM")

    if response_format == 'text':
        return content

    # Parse JSON — strip markdown code fences if present
    text = content.strip()
    if text.startswith('```'):
        text = text.replace('```json', '', 1).replace('```', '', 1)
    if text.endswith('```'):
        text = text.rsplit('```', 1)[0]
    text = text.strip()

    return json.loads(text)
