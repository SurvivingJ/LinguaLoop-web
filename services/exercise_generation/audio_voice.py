"""
Per-language TTS voice config.

Resolves `dim_languages.tts_voice_ids` (jsonb list of Azure neural voice
names) and `tts_speed` once per process, so exercise-generation paths
(flashcard listening, L1 phonetic) can pass the right voice into
AudioSynthesizer without each caller having to know the schema.

Returns None for the voice if no config exists or if the list is empty —
the caller should let AudioSynthesizer fall through to its hardcoded
English default rather than crashing.
"""

import json
import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

# language_id -> {'voice_ids': [...], 'speed': float} | None
_CACHE: dict[int, Optional[dict]] = {}


def _load_config(db, language_id: int) -> Optional[dict]:
    try:
        resp = (
            db.table('dim_languages')
            .select('tts_voice_ids, tts_speed')
            .eq('id', language_id)
            .single()
            .execute()
        )
        row = resp.data or {}
    except Exception as exc:
        logger.warning("Failed to load voice config for language %s: %s", language_id, exc)
        return None

    raw = row.get('tts_voice_ids')
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = []

    voice_ids = [v for v in (raw or []) if isinstance(v, str) and v.strip()]
    if not voice_ids:
        return None

    speed = float(row.get('tts_speed') or 1.0)
    return {'voice_ids': voice_ids, 'speed': speed}


def get_language_voice_config(db, language_id: int) -> Optional[dict]:
    """Cached lookup. First call hits the DB; subsequent calls are O(1)."""
    if language_id not in _CACHE:
        _CACHE[language_id] = _load_config(db, language_id)
    return _CACHE[language_id]


def pick_voice(db, language_id: int) -> tuple[Optional[str], Optional[float]]:
    """Convenience: returns (voice, speed) ready to pass into
    AudioSynthesizer.generate_and_upload. Either element may be None,
    in which case the synthesizer's Azure default applies.
    """
    cfg = get_language_voice_config(db, language_id)
    if not cfg:
        return None, None
    return random.choice(cfg['voice_ids']), cfg['speed']


def clear_cache() -> None:
    """Test-only escape hatch."""
    _CACHE.clear()
