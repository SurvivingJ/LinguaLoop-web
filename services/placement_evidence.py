"""Vocabulary placement → knowledge model (vocab-placement tech §10; ADR-059, accepted 2026-11-18; TASK-1081).

Written once per session at ``finish()`` (abandoned sessions included), claimed through
``calibration_sessions.bkt_applied_at`` exactly like the vocabulary check (``calibration_service.
apply_calibration_to_vocabulary``). Per word outcome (scored items only; probes never write):

| outcome                                              | BKT write | counter            | practice      |
|------------------------------------------------------|-----------|--------------------|---------------|
| meaning ✓ and reading ✓ (zh: the key K)              | correct   | placement_correct  | none          |
| meaning ✓, reading ✗ or IDK (zh: K′, F, F′ or IDK)   | none      | none               | A2r (reading) |
| meaning ✗ or IDK                                     | wrong     | placement_wrong    | A2            |
| reading-exempt (ja kana-only, en): meaning ✓         | correct   | placement_correct  | none          |

The write goes to the anchor sense row, as the check writes (PQ21 default). Admission to practice reads the
sessions back (``new_word_admission._placement_ledger``) and maps each word to its own-language rank-1 sense.
NON-FATAL: a failure is logged, the claim is released so a retry can write, and the result is kept.
"""
from __future__ import annotations

import logging
from typing import Optional

from services.supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)


def items_for(words: list[dict]) -> list[dict]:
    """The rows of the §10 table that write: ``[{sense_id, is_correct}]``."""
    out = []
    for w in words:
        sid = w.get('sense_id')
        if sid is None:
            continue
        if w.get('meaning') != 'right':
            out.append({'sense_id': int(sid), 'is_correct': False})
        elif not w.get('reading_ready') or w.get('reading') in ('right', 'K'):
            out.append({'sense_id': int(sid), 'is_correct': True})
    return out


def write(user_id: str, session: dict, words: list[dict]) -> Optional[dict]:
    db = get_supabase_admin()
    sid = session['id']
    claimed = False
    try:
        claim = (db.table('calibration_sessions').update({'bkt_applied_at': 'now()'})
                 .eq('id', sid).eq('user_id', user_id).eq('mode', 'placement')
                 .is_('bkt_applied_at', 'null').execute())
        if not (claim.data or []):
            return None                                         # already applied
        claimed = True
        items = items_for(words)
        if not items:
            return {'sent': 0}
        resp = db.rpc('update_vocabulary_from_placement_batch', {
            'p_user_id': user_id, 'p_language_id': int(session['word_language_id']), 'p_items': items,
        }).execute()
        if not (resp.data or []):
            raise RuntimeError('placement batch RPC returned no rows')
        return {'sent': len(items)}
    except Exception as exc:
        logger.warning('placement evidence not written for session %s (%s); the result is kept.',
                       str(sid)[:8], str(exc)[:160])
        if claimed:
            try:
                (db.table('calibration_sessions').update({'bkt_applied_at': None})
                 .eq('id', sid).eq('user_id', user_id).execute())
            except Exception as reset_exc:
                logger.warning('could not reset bkt_applied_at for session %s: %s', str(sid)[:8], reset_exc)
        return None
