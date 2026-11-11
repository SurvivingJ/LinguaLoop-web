"""Call an RPC that bundles several reads, falling back cleanly when it is absent.

Used by the daily-session read merges (ADR-043 option B,
migrations/latency_2026_11_session_merges.sql). Callers keep their original
per-table reads as the fallback, so the app works the same before the
migration is applied, and if a bundle ever errors.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# name -> monotonic time until which the function is treated as missing.
_missing_until: Dict[str, float] = {}
_MISSING_RECHECK_SECONDS = 600


def call_bundle(db, name: str, params: Dict[str, Any]) -> Optional[dict]:
    """The RPC's jsonb result as a dict, or None (missing, error, or not a dict).

    A "function not found" error (PostgREST PGRST202) is remembered for ten
    minutes so requests do not pay a failing round trip before the migration
    is applied.
    """
    if _missing_until.get(name, 0.0) > time.monotonic():
        return None
    try:
        data = db.rpc(name, params).execute().data
    except Exception as exc:  # network, missing function, SQL error
        text = str(exc)
        if 'PGRST202' in text or 'Could not find the function' in text:
            _missing_until[name] = time.monotonic() + _MISSING_RECHECK_SECONDS
            logger.info('%s not deployed yet; using per-table reads', name)
        else:
            logger.warning('%s failed (%s); using per-table reads', name, exc)
        return None
    if isinstance(data, list) and len(data) == 1:
        data = data[0]
    return data if isinstance(data, dict) else None


def reset() -> None:
    """Forget remembered-missing functions (tests)."""
    _missing_until.clear()
