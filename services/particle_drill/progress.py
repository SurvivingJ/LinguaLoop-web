"""Stores a learner's particle-drill ladder state (one small JSON row).

The drill runs in the browser and keeps its state in localStorage; this is
the cross-device copy in ``user_drill_progress``. The table arrives with
``migrations/particle_drill_progress.sql``; until that is applied every call
answers ``available: False`` and the drill simply stays on local storage.
"""
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

TABLE = 'user_drill_progress'
DRILL = 'particles_ja'
MAX_STATE_BYTES = 256 * 1024
_MISSING_TTL = 300.0
_missing_until = 0.0


def _table_missing(exc: Exception) -> bool:
    text = str(exc)
    return 'PGRST205' in text or '42P01' in text or (TABLE in text and 'does not exist' in text)


def _unavailable() -> bool:
    return time.monotonic() < _missing_until


def _mark_missing() -> None:
    global _missing_until
    _missing_until = time.monotonic() + _MISSING_TTL
    logger.warning("%s is not in the database; particle-drill progress stays in the browser", TABLE)


def load(db, user_id: str) -> Dict[str, Any]:
    """``{'available': bool, 'state': dict or None, 'updated_at': str or None}``."""
    if _unavailable():
        return {'available': False, 'state': None, 'updated_at': None}
    try:
        res = (db.table(TABLE).select('state, updated_at')
               .eq('user_id', user_id).eq('drill', DRILL).limit(1).execute())
    except Exception as exc:  # noqa: BLE001 - the drill works without the server copy
        if _table_missing(exc):
            _mark_missing()
            return {'available': False, 'state': None, 'updated_at': None}
        raise
    row = (res.data or [None])[0]
    if not row:
        return {'available': True, 'state': None, 'updated_at': None}
    return {'available': True, 'state': row.get('state'), 'updated_at': row.get('updated_at')}


def validate_state(state: Any) -> Optional[str]:
    """An error message, or None when the state can be stored."""
    if not isinstance(state, dict):
        return 'state must be an object'
    if not isinstance(state.get('skills', {}), dict) or not isinstance(state.get('conj', {}), dict):
        return 'state.skills and state.conj must be objects'
    if len(json.dumps(state, ensure_ascii=False).encode('utf-8')) > MAX_STATE_BYTES:
        return 'state is too large'
    return None


def save(db, user_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert the learner's state. ``{'available': bool, 'saved': bool}``."""
    if _unavailable():
        return {'available': False, 'saved': False}
    try:
        db.table(TABLE).upsert(
            {'user_id': user_id, 'drill': DRILL, 'state': state, 'updated_at': datetime.now(timezone.utc).isoformat()},
            on_conflict='user_id,drill',
        ).execute()
    except Exception as exc:  # noqa: BLE001
        if _table_missing(exc):
            _mark_missing()
            return {'available': False, 'saved': False}
        raise
    return {'available': True, 'saved': True}
