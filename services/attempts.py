"""Test-attempt bookkeeping shared by the submit routes.

Everything here takes the database client explicitly and never reads Flask's
``g``, ``request`` or ``current_app``, so it can run on a worker thread.
"""

from __future__ import annotations

import logging
import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional

from services.attempt_timing import AttemptTimingError, validate_attempt_window
from services.concurrency import run_parallel
from services.dimension_service import DimensionService
from services.study_time import credit_study_time
from services.test_service import TestService
from services.vocabulary.knowledge_service import VocabularyKnowledgeService

logger = logging.getLogger(__name__)

# Post-submission bookkeeping that does not feed the response (timing, daily
# slot, flashcards, ladder rows, contextual inference). The submit handler
# starts these with defer() and waits for them with join() before it answers,
# so they overlap with building the response instead of preceding it. Tasks
# must be self-contained: they must not wait on other pooled work.
_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix='attempt')


def defer(fn: Callable, *args, **kwargs) -> Future:
    return _pool.submit(fn, *args, **kwargs)


def join(futures: Iterable[Future]) -> None:
    """Wait for deferred bookkeeping. A task that raises is logged, never re-raised."""
    for f in futures:
        try:
            f.result()
        except Exception as e:
            logger.warning("post-submission bookkeeping failed (non-fatal): %s\n%s",
                           e, traceback.format_exc())


# ---------------------------------------------------------------------------
# Timing, progress, daily slot
# ---------------------------------------------------------------------------

def normalize_timing(request_body: dict) -> None:
    """Validate/clamp started_at + finished_at in place (TASK-882 / S15).

    Call BEFORE the submission RPC so a forged window is rejected (400) and
    nothing is recorded. Raises AttemptTimingError; callers return bad_request.
    """
    started, finished = validate_attempt_window(
        request_body.get('started_at'), request_body.get('finished_at'),
    )
    request_body['started_at'] = started
    request_body['finished_at'] = finished


def complete_daily_slot(db, user_id, language_id, test_id) -> None:
    """Post-submission hook — mark today's daily-load slot for this test done.

    Best-effort, like apply_timing_and_progress: the learner already has
    their result. Without this the slot was only marked on the results card's
    "Next" button, so leaving from the results card re-served the test.
    """
    if not (user_id and language_id and test_id):
        return
    try:
        TestService(supabase_admin=db)\
            .mark_daily_slot_complete_on_submit(user_id, language_id, test_id)
    except Exception as e:
        logger.warning(
            "daily slot completion on submit failed (test=%s): %s", test_id, e)


def apply_timing_and_progress(client, attempt_id, request_body,
                              user_id=None, language_id=None, kind='test') -> None:
    """Post-submission hook — persist timing + bump Study Plan counter.

    Phase 13. Best-effort: failures are logged but never bubble up to the
    learner, who has already received their submission result. Both
    timestamps are optional; missing timestamps mean the FE didn't capture
    them (older clients) and we skip the duration UPDATE while still
    incrementing the test counter.

    Args:
        client: Supabase service client.
        attempt_id: UUID returned by the submission RPC.
        request_body: the request JSON dict (we read started_at /
            finished_at from it).
        user_id, language_id: when both are given, the measured window is
            also credited to the weekly study-time ledger (weekly-minutes,
            ADR-035) as ``kind`` ('test' or 'drill').

    See migrations/phase13_apply_attempt_timing_and_progress.sql.
    """
    if not attempt_id:
        return
    started_at  = request_body.get('started_at')   # ISO timestamp or None
    finished_at = request_body.get('finished_at')
    if kind == 'drill':
        # Drill routes do not pre-validate the window like the test routes do
        # (normalize_timing); a forged/garbled window is dropped, not stored.
        try:
            started_at, finished_at = validate_attempt_window(started_at, finished_at)
        except AttemptTimingError:
            started_at, finished_at = None, None
    try:
        client.rpc('apply_attempt_timing_and_progress', {
            'p_attempt_id':  str(attempt_id),
            'p_started_at':  started_at,
            'p_finished_at': finished_at,
        }).execute()
    except Exception as e:
        # Non-fatal — timing capture and Study Plan counters are best-effort.
        logger.warning(
            f"apply_attempt_timing_and_progress failed (non-fatal) for "
            f"attempt={attempt_id}: {e}"
        )

    credit_attempt_window(
        client, attempt_id, started_at, finished_at, user_id, language_id, kind,
    )


def credit_attempt_window(client, attempt_id, started_at, finished_at,
                          user_id, language_id, kind) -> None:
    """Credit the validated, clamped attempt window to the study-time ledger.

    Never raises. No window (older clients) or an invalid one earns nothing:
    missing test timing is not estimated (weekly-minutes tech spec, decision 3).
    """
    if not user_id or language_id is None:
        return
    try:
        # Re-validate/clamp: drill routes pass the raw body, and this keeps
        # the credit bounded by MAX_CREDITED_ATTEMPT_SECONDS regardless.
        start_iso, finish_iso = validate_attempt_window(started_at, finished_at)
        if not start_iso or not finish_iso:
            return
        seconds = int((datetime.fromisoformat(finish_iso)
                       - datetime.fromisoformat(start_iso)).total_seconds())
        credit_study_time(
            client, user_id, language_id, kind, seconds,
            'test_attempts', str(attempt_id),
        )
    except Exception as e:
        logger.warning(
            f"study-time credit skipped (non-fatal) for attempt={attempt_id}: {e}"
        )


# ---------------------------------------------------------------------------
# Comprehension submit: questions, vocabulary tracking, response
# ---------------------------------------------------------------------------

def load_question_rows(db, test_id) -> Optional[List[dict]]:
    """The test's questions as the submit path needs them (id, sense_ids,
    answer_explanation), read once. None when the read fails; the callers
    each degrade as they did when their own read failed."""
    try:
        return db.table('questions') \
            .select('id, sense_ids, answer_explanation') \
            .eq('test_id', str(test_id)).execute().data or []
    except Exception as e:
        logger.warning("questions read for submit failed (non-fatal): %s", e)
        return None


def attach_explanations(result: dict, question_rows: Optional[List[dict]]) -> None:
    """Add ``answer_explanation`` to each question_result (TASK-882 / S14).

    The explanation (like the correct answer, which the grading RPC already
    returns in question_results) is revealed only here, after submit. Without
    question rows the learner just sees no explanation.
    """
    if question_rows is None:
        return
    try:
        by_id = {str(r['id']): r.get('answer_explanation') for r in question_rows}
        for qr in result.get('question_results') or []:
            if isinstance(qr, dict):
                qr['answer_explanation'] = by_id.get(str(qr.get('question_id')))
    except Exception as e:
        logger.warning("answer_explanation lookup failed (non-fatal): %s", e)


def _contextual_inference(knowledge_svc, user_id, language_id, test_id,
                          question_results, score_ratio, question_rows) -> None:
    count = knowledge_svc.apply_contextual_inference(
        user_id=user_id, language_id=language_id,
        test_id=str(test_id),
        question_results=question_results,
        score_ratio=score_ratio,
        question_rows=question_rows,
    )
    if count:
        logger.info(f"BKT: {count} contextual senses boosted")


def track_vocabulary(user_id, test_id, language_id, rpc_result,
                     question_rows: Optional[List[dict]] = None,
                     pending: Optional[List[Future]] = None):
    """Run BKT vocabulary tracking and build a word quiz from question results.

    Returns a word_quiz dict or None. Failures are logged but never raised.

    ``question_rows``: the test's questions (``sense_ids``) when the caller
    already read them. ``pending``: when given, the steps that do not feed the
    quiz (flashcards, ladder rows, contextual inference) are deferred and
    their futures appended, for the caller to join(); otherwise they run here.
    Call from the request thread.
    """
    try:
        question_results_raw = rpc_result.get('question_results', [])
        logger.info(f"BKT: {len(question_results_raw)} question results from RPC")

        if not question_results_raw:
            return None

        bkt_question_results = [
            {'question_id': str(qr['question_id']), 'is_correct': qr.get('is_correct', False)}
            for qr in question_results_raw
            if qr.get('question_id')
        ]
        logger.info(f"BKT: {len(bkt_question_results)} valid question results")

        if not bkt_question_results:
            return None

        knowledge_svc = VocabularyKnowledgeService()
        db = knowledge_svc.db

        from services.vocabulary.gloss_lookup import get_user_definition_language_id

        def _definition_language():
            try:
                return get_user_definition_language_id(db, user_id)
            except Exception as e:  # raised later, where the quiz needs it
                return e

        vocab_updates, preferred_def_lang_id = run_parallel(
            lambda: knowledge_svc.update_from_comprehension(
                user_id=user_id, language_id=language_id,
                question_results=bkt_question_results, side_effects=False,
            ),
            _definition_language,
        )
        logger.info(f"BKT: {len(vocab_updates)} vocab updates returned")

        def _run(fn, *args):
            if pending is None:
                fn(*args)
            else:
                pending.append(defer(fn, *args))

        # Flashcards and ladder rows are independent of each other. Frequency
        # inference can raise p_known, which the ladder step and the quiz
        # read, so when it will fire everything keeps its original order.
        if knowledge_svc.crosses_known_threshold(vocab_updates):
            knowledge_svc.apply_side_effects(user_id, language_id, vocab_updates)
        else:
            _run(knowledge_svc.create_flashcards, user_id, language_id, vocab_updates)
            _run(knowledge_svc.seed_ladder, user_id, language_id, vocab_updates)

        # Contextual inference: dampened update for transcript words not
        # directly tested (disjoint from the question senses the quiz reads)
        score = rpc_result.get('score', 0)
        total = rpc_result.get('total_questions', 1) or 1
        score_ratio = score / total
        if question_rows is None:
            question_rows = db.table('questions') \
                .select('sense_ids').eq('test_id', str(test_id)).execute().data
        _run(_contextual_inference, knowledge_svc, user_id, language_id, test_id,
             bkt_question_results, score_ratio, question_rows)

        # Collect all sense_ids from questions for quiz candidate selection
        all_sense_ids = set()
        for q in (question_rows or []):
            if q.get('sense_ids'):
                all_sense_ids.update(q['sense_ids'])

        logger.info(f"BKT: {len(all_sense_ids)} unique sense_ids from questions")

        if not all_sense_ids:
            logger.warning("BKT: No sense_ids on questions — run backfill_question_sense_ids.py")
            return None

        if isinstance(preferred_def_lang_id, Exception):
            raise preferred_def_lang_id

        quiz_candidates = knowledge_svc.build_quiz_with_distractors(
            user_id=user_id, sense_ids=list(all_sense_ids),
            language_id=language_id, max_words=5,
            preferred_definition_language_id=preferred_def_lang_id,
        )
        logger.info(f"BKT: {len(quiz_candidates)} quiz candidates with distractors")

        if quiz_candidates:
            attempt_id = rpc_result.get('attempt_id')
            return {
                'candidates': quiz_candidates,
                'attempt_id': str(attempt_id) if attempt_id else None,
            }
        return None

    except Exception as e:
        logger.error(f"BKT/word quiz failed (non-fatal): {e}\n{traceback.format_exc()}")
        return None


def elo_changes(rpc_result: dict) -> dict:
    """The ``user_elo_change`` / ``test_elo_change`` blocks every submit returns."""
    return {
        'user_elo_change': {
            'before': rpc_result.get('user_elo_before'),
            'after': rpc_result.get('user_elo_after'),
            'change': rpc_result.get('user_elo_change', 0)
        },
        'test_elo_change': {
            'before': rpc_result.get('test_elo_before'),
            'after': rpc_result.get('test_elo_after'),
            'change': rpc_result.get('test_elo_change', 0)
        },
    }


def attempt_id_str(rpc_result: dict) -> Optional[str]:
    attempt_id = rpc_result.get('attempt_id')
    return str(attempt_id) if attempt_id else None


def build_submission_response(rpc_result, test_mode, word_quiz):
    """Construct the API response dict from RPC results and optional word quiz."""
    result = {
        'score': rpc_result.get('score'),
        'total_questions': rpc_result.get('total_questions'),
        'percentage': rpc_result.get('percentage'),
        'question_results': rpc_result.get('question_results', []),
        'is_first_attempt': rpc_result.get('is_first_attempt', True),
        **elo_changes(rpc_result),
        'elo_reduction_factor': rpc_result.get('elo_reduction_factor'),
        'test_mode': test_mode,
        'attempt_id': attempt_id_str(rpc_result),
    }
    if word_quiz:
        result['word_quiz'] = word_quiz
    return result


# ---------------------------------------------------------------------------
# Dictation
# ---------------------------------------------------------------------------

def attach_dictation_senses(diff, token_map) -> None:
    """Map canonical tokens → sense_ids via vocab_token_map, in place.

    Token map is a list of (surface_form, sense_id) pairs aligned to the
    test's tokenization. We do a lemma-agnostic surface match
    (post-normalization) on the canonical token strings.
    """
    if not token_map:
        return
    from services.dictation.tokenizer import normalize as _norm
    surface_to_sense = {}
    for entry in token_map:
        if not entry or len(entry) < 2:
            continue
        surface, sense_id = entry[0], entry[1]
        if not sense_id:
            continue
        # First mapping wins (avoid overwriting with later duplicates)
        surface_to_sense.setdefault(_norm(str(surface)), sense_id)

    for d in diff:
        if d.correct:
            d.sense_id = surface_to_sense.get(d.correct)


def record_dictation_bkt(user_id, language_id, test_id, diff) -> None:
    """Per-word BKT updates — single batched RPC instead of N round-trips.

    'insert' ops (extra user words) have no canonical sense_id and are
    excluded; 'equal' / 'replace' / 'delete' all carry canonical-side
    sense_ids when the token maps to a dim_word_senses row. Never raises.
    """
    try:
        word_results = [
            {'sense_id': d.sense_id, 'is_correct': bool(d.is_correct)}
            for d in diff
            if d.sense_id and d.op in ('equal', 'replace', 'delete')
        ]
        if word_results:
            bkt_rows = VocabularyKnowledgeService().update_from_word_tests_batch(
                user_id=user_id,
                language_id=language_id,
                results=word_results,
            )
            logger.info(
                f"Dictation BKT: user={user_id} test={test_id} "
                f"{len(word_results)} inputs → {len(bkt_rows)} senses updated (batched)"
            )
    except Exception as e:
        logger.error(f"Dictation BKT update failed (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Self-scored modes: how many items the test really has
# ---------------------------------------------------------------------------

def _tokens(payload) -> list:
    return [t for t in payload if isinstance(t, dict)] if isinstance(payload, list) else []


def pinyin_item_count(payload) -> int:
    """Playable characters of a pinyin payload (static/js/session/players/pinyin.js)."""
    return sum(1 for t in _tokens(payload) if not t.get('is_punctuation'))


def pitch_item_count(payload) -> int:
    """Drillable accent phrases of a pitch payload (players/pitch_accent.js)."""
    return sum(
        1 for t in _tokens(payload)
        if not t.get('is_punctuation') and (t.get('mora_count') or 0) > 0
        and t.get('pattern_class') != 'unknown'
    )


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

def _test_type_names(client, type_ids) -> Dict[Any, str]:
    """{test_type_id: type_name} from the DimensionService cache; the table is
    read only when the cache does not cover every id (inactive type, cache
    not loaded)."""
    names = {t['id']: t['type_name'] for t in DimensionService._test_types_metadata
             if isinstance(t, dict) and 'id' in t and 'type_name' in t}
    if all(i in names for i in type_ids):
        return names
    try:
        types_res = client.table('dim_test_types').select('id, type_name').execute()
        return {t['id']: t['type_name'] for t in types_res.data or []}
    except Exception as e:
        logger.debug(f"dim_test_types lookup skipped: {e}")
        return {}


def list_test_history(client, admin, user_id, language_id=None, test_type_id=None,
                      limit=25, offset=0) -> List[dict]:
    """A page of the user's attempts, newest first, with test title and slug."""
    query = client.table('test_attempts')\
        .select('id, test_id, score, total_questions, percentage, user_elo_after, created_at, test_type_id, elo_reduction_factor')\
        .eq('user_id', user_id)\
        .order('created_at', desc=True)\
        .range(offset, offset + limit - 1)

    if language_id:
        query = query.eq('language_id', language_id)
    if test_type_id:
        query = query.eq('test_type_id', test_type_id)

    attempts = query.execute().data or []
    if not attempts:
        return []

    test_ids = list(set(a['test_id'] for a in attempts))

    tests_map = {}
    if test_ids and admin:
        tests_result = admin.table('tests')\
            .select('id, title, slug')\
            .in_('id', test_ids)\
            .execute()
        for t in tests_result.data or []:
            tests_map[t['id']] = t

    type_map = _test_type_names(client, {a['test_type_id'] for a in attempts})

    history = []
    for attempt in attempts:
        test_id = attempt['test_id']
        test_detail = tests_map.get(test_id, {})
        history.append({
            'id': attempt['id'],
            'test_id': test_id,
            'test_title': test_detail.get('title', 'Unknown Test'),
            'test_slug': test_detail.get('slug', ''),
            'test_type': type_map.get(attempt['test_type_id'], 'Unknown'),
            'test_type_id': attempt['test_type_id'],
            'score': attempt['score'],
            'total_questions': attempt['total_questions'],
            'percentage': attempt['percentage'],
            'user_elo_after': attempt['user_elo_after'],
            'elo_reduction_factor': attempt.get('elo_reduction_factor'),
            'created_at': attempt['created_at']
        })
    return history
