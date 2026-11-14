"""Sentence spans of a test with the learner's L1 references."""

from flask import request, current_app, g
import traceback
import logging

from middleware.auth import jwt_required as supabase_jwt_required
from services.day_boundary import local_day_start_utc, plan_timezone
from services.dual_translation.sentence_refs import LANG_ID as SENTENCE_L1_IDS
from services.test_service import find_active_test
from utils.responses import (
    api_success, api_error, bad_request, not_found, server_error, service_unavailable,
)

from .blueprint import tests_bp

logger = logging.getLogger("routes.tests")


# ============================================================================
# TASK-909 — sentence spans + L1 references (ADR-037)
# ============================================================================

# Fallback L1 while users.native_language_id is unset for most rows — id 2 =
# English (config.py LANGUAGES); mirrors routes/dual_translation.py.
_DEFAULT_L1_LANGUAGE_ID = 2

_SENTENCE_COLUMNS = 'id, idx, l2_text, char_start, char_end, token_start, token_end, transcript_hash'


def _find_test_for_sentences(db, identifier):
    """Active test by slug, then by uuid; the columns the sentences endpoint needs."""
    return find_active_test(db, identifier, 'id, slug, language_id, transcript_hash')


def _resolve_sentence_l1(db, user_id, l1_code):
    """``?l1=<code>`` -> dim_languages id; absent -> users.native_language_id,
    else English. Unknown codes return None (400 at the route)."""
    if l1_code:
        return SENTENCE_L1_IDS.get(str(l1_code).lower())
    try:
        resp = db.table('users').select('native_language_id').eq('id', user_id).limit(1).execute()
        if resp.data and resp.data[0].get('native_language_id'):
            return int(resp.data[0]['native_language_id'])
    except Exception as e:  # best-effort; the default is always usable
        logger.warning("native_language_id lookup failed for %s: %s", user_id, e)
    return _DEFAULT_L1_LANGUAGE_ID


def _has_attempt_today(db, user_id, test_id, language_id):
    """True when the user has a ``test_attempts`` row for this test since the
    start of their local day (ADR-022) — the same check
    ``TestService.mark_daily_test_complete`` makes. This is the ``?mode=produce``
    withholding rule: before today's attempt is submitted the L2 text stays
    hidden, exactly as ``?mode=dictation`` hides the transcript."""
    day_start = local_day_start_utc(plan_timezone(db, user_id, language_id))
    resp = (
        db.table('test_attempts').select('id')
        .eq('user_id', user_id).eq('test_id', test_id)
        .gte('created_at', day_start.isoformat())
        .limit(1).execute()
    )
    return bool(resp.data)


def _load_sentence_rows(db, test_id):
    resp = (
        db.table('test_sentences').select(_SENTENCE_COLUMNS)
        .eq('test_id', test_id).order('idx').execute()
    )
    return resp.data or []


def _load_active_references(db, sentence_ids, l1_language_id):
    """``{sentence_id: {l1_text, tightness, review_verdict}}`` for the active
    reference of each sentence in this L1 (at most one active per pair)."""
    if not sentence_ids:
        return {}
    resp = (
        db.table('test_sentence_references')
        .select('sentence_id, l1_text, tightness, review_verdict')
        .in_('sentence_id', list(sentence_ids))
        .eq('l1_language_id', l1_language_id)
        .eq('is_active', True)
        .execute()
    )
    return {row['sentence_id']: row for row in (resp.data or [])}


def build_sentence_payload(rows, references, withhold_l2):
    """Shape the endpoint's ``sentences`` list from ``test_sentences`` rows and
    the active-reference map. ``l2_text`` is dropped when ``withhold_l2``."""
    out = []
    for row in rows:
        ref = references.get(row.get('id'))
        item = {
            'idx': row['idx'],
            'char_start': row['char_start'],
            'char_end': row['char_end'],
            'token_start': row.get('token_start'),
            'token_end': row.get('token_end'),
            'reference': (
                {'l1_text': ref['l1_text'], 'tightness': ref.get('tightness')} if ref else None
            ),
        }
        if not withhold_l2:
            item['l2_text'] = row['l2_text']
        out.append(item)
    return out


@tests_bp.route('/<identifier>/sentences', methods=['GET'])
@supabase_jwt_required
def get_test_sentences(identifier):
    """Sentence spans of a test with the learner's L1 references (TASK-909).

    ``?l1=<code>`` picks the reference language (default: the user's native
    language, else English). ``?mode=produce`` withholds ``l2_text`` until the
    user has submitted an attempt today — the Produce stage must not leak the
    passage before the test. 404 unknown test; 409 when the sentence rows were
    segmented from a different transcript than the one now stored (stale —
    the backfill script re-segments); an empty ``sentences`` list means the
    test has no rows yet (the client falls back to its own split).
    """
    try:
        db = current_app.supabase_service
        if not db:
            return service_unavailable("Service not available")

        test = _find_test_for_sentences(db, identifier)
        if not test:
            return not_found("Test not found")

        l1_language_id = _resolve_sentence_l1(db, g.current_user_id, request.args.get('l1'))
        if l1_language_id is None:
            return bad_request("Unknown l1 language code")

        rows = _load_sentence_rows(db, test['id'])
        stored_hash = test.get('transcript_hash')
        if rows and stored_hash and any(r.get('transcript_hash') != stored_hash for r in rows):
            return api_error(
                "Sentence rows are stale for this transcript", 409, error_code="SENTENCES_STALE",
            )

        mode = (request.args.get('mode') or '').lower()
        withhold = mode == 'produce' and not _has_attempt_today(
            db, g.current_user_id, test['id'], test.get('language_id'),
        )

        references = _load_active_references(db, [r['id'] for r in rows], l1_language_id)
        return api_success(data={
            'test_id': test['id'],
            'l1_language_id': l1_language_id,
            'l2_withheld': withhold,
            'sentences': build_sentence_payload(rows, references, withhold),
        })

    except Exception as e:
        logger.error("Error loading sentences for %s: %s", identifier, e)
        logger.error(traceback.format_exc())
        return server_error('Failed to load sentences')
