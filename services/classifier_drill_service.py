# services/classifier_drill_service.py
"""Measure-Word Drill service.

Thin wrapper around the get_classifier_drill_session and
process_classifier_drill_submission RPCs. Caches the per-language sentinel
test_id so submission calls don't have to re-query.
"""

import logging
from typing import Optional
from uuid import uuid4

from services.supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)

# language_id -> sentinel test slug
_SENTINEL_SLUGS = {
    1: '__classifier_drill_zh',
}

# language_id -> tests.id (populated lazily)
_sentinel_id_cache: dict[int, str] = {}


def _fetch_sentinel_test_id(language_id: int) -> Optional[str]:
    """Look up (and cache) the sentinel test UUID for a language."""
    if language_id in _sentinel_id_cache:
        return _sentinel_id_cache[language_id]

    slug = _SENTINEL_SLUGS.get(language_id)
    if not slug:
        return None

    db = get_supabase_admin()
    resp = (
        db.table('tests')
          .select('id')
          .eq('slug', slug)
          .single()
          .execute()
    )
    if not resp.data:
        logger.error("Classifier drill sentinel test not found for language_id=%s slug=%s", language_id, slug)
        return None

    _sentinel_id_cache[language_id] = resp.data['id']
    return _sentinel_id_cache[language_id]


def get_session(user_id: str, language_id: int, count: int = 20) -> list[dict]:
    """Fetch a batch of drill items via the session RPC.

    Returns a list of dicts ready for JSON serialization. Empty list on error.
    """
    db = get_supabase_admin()
    try:
        resp = db.rpc('get_classifier_drill_session', {
            'p_user_id': user_id,
            'p_language_id': language_id,
            'p_count': count,
        }).execute()
        rows = resp.data or []
    except Exception as e:
        logger.error("get_classifier_drill_session RPC failed: %s", e)
        return []

    items = []
    for r in rows:
        items.append({
            'pair_id':                 r.get('out_pair_id'),
            'noun_lemma':              r.get('out_noun_lemma'),
            'noun_sense_id':           r.get('out_noun_sense_id'),
            'noun_gloss':              r.get('out_noun_gloss'),
            'noun_pronunciation':      r.get('out_noun_pronunciation'),
            'correct_classifier_ids':  r.get('out_correct_classifier_ids') or [],
            'correct_classifier_hanzi': r.get('out_correct_classifier_hanzi') or [],
            'distractor_ids':          r.get('out_distractor_ids') or [],
            'distractor_hanzi':        r.get('out_distractor_hanzi') or [],
            'distractor_pinyin':       r.get('out_distractor_pinyin') or [],
            'semantic_label':          r.get('out_semantic_label'),
            'distractor_group_label':  r.get('out_distractor_group_label'),
        })
    return items


def submit_session(
    user_id: str,
    language_id: int,
    test_type_id: int,
    correct_items: int,
    total_items: int,
    idempotency_key: Optional[str] = None,
) -> Optional[dict]:
    """Persist a completed drill session and update ELO.

    Returns the RPC's JSONB envelope, or None on hard failure.
    """
    test_id = _fetch_sentinel_test_id(language_id)
    if not test_id:
        logger.error("No sentinel test for language_id=%s", language_id)
        return None

    db = get_supabase_admin()
    try:
        resp = db.rpc('process_classifier_drill_submission', {
            'p_user_id':        user_id,
            'p_test_id':        test_id,
            'p_language_id':    language_id,
            'p_test_type_id':   test_type_id,
            'p_correct_items':  int(correct_items),
            'p_total_items':    int(total_items),
            'p_was_free_test':  True,
            'p_idempotency_key': idempotency_key or str(uuid4()),
        }).execute()
        return resp.data
    except Exception as e:
        # The RPC encodes its own errors in the JSONB envelope; only network
        # / parse failures land here.
        error_data = e.json() if hasattr(e, 'json') else (e.args[0] if e.args else {})
        if isinstance(error_data, dict) and error_data.get('success'):
            return error_data
        logger.error("process_classifier_drill_submission failed: %s", error_data or e)
        return None
