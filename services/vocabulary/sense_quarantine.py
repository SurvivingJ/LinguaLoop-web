"""Senses whose dictionary row is known to be wrong (TASK-767).

``calibration_anchor_blocklist`` is the quarantine list. Correctness is enforced
in the database — triggers keep every exercise on a quarantined sense inactive
and drop the sense from ``generation_queue`` (see
migrations/task767_sense_quarantine_guards.sql). This module exists so that
generators can skip a quarantined sense *before* spending an LLM call on output
the database would retire anyway.

Fails open: if the lookup errors, nothing is reported quarantined and the
generator proceeds. The triggers still stop the output being served, so the
worst case is wasted spend, not a bad item reaching a learner.
"""

from __future__ import annotations

import logging
from typing import Iterable

logger = logging.getLogger(__name__)

QUARANTINE_TABLE = 'calibration_anchor_blocklist'
_CHUNK = 500


def quarantined_sense_ids(db, sense_ids: Iterable[int]) -> set[int]:
    """The subset of ``sense_ids`` that is quarantined."""
    ids = [int(s) for s in sense_ids if s is not None]
    found: set[int] = set()
    for start in range(0, len(ids), _CHUNK):
        chunk = ids[start:start + _CHUNK]
        try:
            resp = (db.table(QUARANTINE_TABLE)
                    .select('sense_id')
                    .in_('sense_id', chunk)
                    .execute())
        except Exception as exc:
            logger.warning('sense quarantine lookup failed, proceeding: %s', exc)
            return found
        found.update(row['sense_id'] for row in (resp.data or []))
    return found


def is_quarantined(db, sense_id: int) -> bool:
    return bool(quarantined_sense_ids(db, [sense_id]))
