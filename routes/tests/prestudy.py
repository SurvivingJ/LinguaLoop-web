"""Test prestudy: study material, sessions, evidence and Produce."""

from flask import request, current_app, g
import traceback
import logging

from middleware.auth import jwt_required as supabase_jwt_required
from services.test_service import find_active_test
from services.vocabulary.knowledge_service import VocabularyKnowledgeService
from utils.responses import (
    api_success, api_error, bad_request, not_found, server_error,
    service_unavailable, forbidden,
)

from .blueprint import tests_bp

logger = logging.getLogger("routes.tests")


# ============================================================================
# Test prestudy (wiki/features/test-prestudy.md)
# ============================================================================

_PRESTUDY_TEST_COLUMNS = (
    'id, slug, title, language_id, transcript, audio_url, difficulty, target_age_tier, '
    'vocab_sense_ids, vocab_token_map, furigana_payload, pinyin_payload'
)
_PRESTUDY_MAX_ANSWERS = 400
_PRESTUDY_MAX_EXERCISE_ANSWERS = 40


def _find_test_for_prestudy(db, identifier):
    """Active test by slug, then by uuid, with the columns prestudy needs."""
    return find_active_test(db, identifier, _PRESTUDY_TEST_COLUMNS)


@tests_bp.route('/<identifier>/prestudy', methods=['GET'])
@supabase_jwt_required
def get_test_prestudy(identifier):
    """Study material for one test: passage, word map, glosses in the learner's
    language, their knowledge of each word, and ladder exercises.

    ``?mode=followup`` (after an attempt) adds ``followup_sense_ids``: the
    senses behind the questions answered wrong on the latest attempt.

    Never returns the scored questions' text, choices or answers; only each
    question's linked senses, so the page can rank the words the test turns on.
    """
    try:
        db = current_app.supabase_service
        if not db:
            return service_unavailable("Service not available")
        test = _find_test_for_prestudy(db, identifier)
        if not test:
            return not_found("Test not found")
        from services import prestudy
        from services.vocabulary.gloss_lookup import get_user_definition_language_id
        gloss_lang = get_user_definition_language_id(db, g.current_user_id)
        payload = prestudy.build_prestudy_payload(db, test, g.current_user_id, gloss_lang)
        if request.args.get('mode') == 'followup':
            attempt_id, senses = prestudy.wrong_question_senses(db, g.current_user_id, test['id'])
            if not attempt_id:
                return bad_request("Take the test before its follow-up")
            prime = prestudy.latest_prime_session(db, g.current_user_id, test['id'])
            payload['followup_sense_ids'] = senses
            payload['attempt_id'] = attempt_id
            payload['primed_sense_ids'] = (prime or {}).get('words_quizzed') or []
        return api_success(data=payload)
    except Exception as e:
        logger.error("Error loading prestudy for %s: %s", identifier, e)
        logger.error(traceback.format_exc())
        return server_error('Failed to load prestudy')


@tests_bp.route('/<identifier>/prestudy/session', methods=['POST'])
@supabase_jwt_required
def start_test_prestudy_session(identifier):
    """Open a prestudy_sessions row when the page loads.

    Body: {test_type, trigger, plan_mode, unknown_share, mode, session_block_id}.
    ``unknown_share`` is the snapshot at open and is never recomputed.
    Returns {session_id} (null until migrations/prestudy_workflow.sql is applied).
    """
    try:
        db = current_app.supabase_service
        if not db:
            return service_unavailable("Service not available")
        test = _find_test_for_prestudy(db, identifier)
        if not test:
            return not_found("Test not found")
        body = request.get_json(silent=True) or {}
        from services import prestudy
        load_date = None
        if body.get('session_block_id'):
            from services.day_boundary import plan_today_iso
            load_date = plan_today_iso(db, g.current_user_id, int(test['language_id']))
        session_id = prestudy.start_session(
            db, g.current_user_id, test,
            test_type=body.get('test_type') or 'reading', trigger=body.get('trigger') or 'opt_in',
            plan_mode=body.get('plan_mode'), unknown_share=body.get('unknown_share'),
            mode=body.get('mode') or 'prime', session_block_id=body.get('session_block_id'),
            load_date=load_date,
        )
        return api_success(data={'session_id': session_id})
    except Exception as e:
        logger.error("Error starting prestudy session for %s: %s", identifier, e)
        return server_error('Failed to start prestudy')


def _record_prestudy_exercises(db, user_id, exercise_answers, allowed):
    """Ladder exercises answered in the prime -> exercise_attempts (source
    prestudy) + exercise BKT. Only exercises of this test's senses count."""
    from services.practice_session_service import get_practice_session_service
    ids = []
    by_id = {}
    for a in exercise_answers[:_PRESTUDY_MAX_EXERCISE_ANSWERS]:
        if isinstance(a, dict) and isinstance(a.get('exercise_id'), str) and a['exercise_id'] not in by_id:
            by_id[a['exercise_id']] = a
            ids.append(a['exercise_id'])
    if not ids:
        return 0
    rows = db.table('exercises').select('id, exercise_type, word_sense_id, language_id') \
        .in_('id', ids).eq('is_active', True).execute().data or []
    svc = get_practice_session_service()
    recorded = 0
    for ex in rows:
        if ex.get('word_sense_id') not in allowed:
            continue
        a = by_id.get(str(ex['id'])) or {}
        try:
            svc.record_prestudy_exercise_attempt(
                user_id, ex, bool(a.get('correct')) and not a.get('idk'),
                user_response={'given': str(a.get('given') or '')[:500], 'idk': bool(a.get('idk'))},
            )
            recorded += 1
        except Exception as e:
            logger.warning("prestudy exercise %s not recorded: %s", ex.get('id'), e)
    return recorded


@tests_bp.route('/<identifier>/prestudy/evidence', methods=['POST'])
@supabase_jwt_required
def submit_test_prestudy_evidence(identifier):
    """Record a finished prime (or post-test follow-up) in one call.

    Body: {session_id?, mode?: 'prime'|'followup', answers: [{sense_id, correct,
    idk, stage}], exercise_answers?: [{exercise_id, correct, idk, given}],
    metrics?: {...}}.

    * Word answers: one word-test evidence point per sense (majority of its
      answers; "I don't know" counts as wrong). The prime writes with
      side_effects=False (no ladder admission, no new-word quota); the
      follow-up writes with side effects, so its senses enter Queue A1 as the
      post-test quiz's do.
    * Exercise answers: exercise_attempts tagged source=prestudy + exercise BKT.
    * Session: measurement record, minutes to the ledger (kind prestudy),
      next-day review rows, generation requests for primed words that have no
      exercises.
    Only senses of this test are accepted.
    """
    try:
        db = current_app.supabase_service
        if not db:
            return service_unavailable("Service not available")
        test = _find_test_for_prestudy(db, identifier)
        if not test:
            return not_found("Test not found")
        body = request.get_json(silent=True) or {}
        answers = body.get('answers') or []
        exercise_answers = body.get('exercise_answers') or []
        if not isinstance(answers, list) or not isinstance(exercise_answers, list):
            return bad_request("answers and exercise_answers must be lists")
        if not answers and not exercise_answers and not body.get('session_id'):
            return bad_request("answers must be a non-empty list")
        if len(answers) > _PRESTUDY_MAX_ANSWERS:
            return bad_request(f"at most {_PRESTUDY_MAX_ANSWERS} answers")
        from services import prestudy
        user_id = g.current_user_id
        language_id = int(test['language_id'])
        allowed = prestudy.test_sense_ids(db, test)
        session = prestudy.get_session(db, user_id, body.get('session_id'))
        if session and session.get('test_id') != test['id']:
            session = None
        mode = 'followup' if (body.get('mode') == 'followup' or (session or {}).get('mode') == 'followup') else 'prime'

        rows = prestudy.evidence_rows(answers, allowed)
        updates = []
        if rows:
            updates = VocabularyKnowledgeService(db).update_from_word_tests_batch(
                user_id=user_id, language_id=language_id,
                results=rows, side_effects=(mode == 'followup'),
            ) or []
        n_ex = _record_prestudy_exercises(db, user_id, exercise_answers, allowed) if exercise_answers else 0

        out = {'updates': updates, 'recorded': len(rows), 'exercises_recorded': n_ex, 'session': None}
        if session and session.get('status') == 'open':
            reasons = prestudy.followups_from_answers(answers, allowed)
            if mode == 'followup':
                prime = prestudy.latest_prime_session(db, user_id, test['id'])
                reasons.update(prestudy.primed_missed((prime or {}).get('words_quizzed'), answers, allowed))
            metrics = body.get('metrics') if isinstance(body.get('metrics'), dict) else {}
            out['session'] = prestudy.complete_session(db, user_id, session, metrics, allowed, reasons)
            if mode == 'prime':
                # Primed words with no ladder exercises -> generation (reason prestudy)
                quizzed = [int(s) for s in (metrics.get('words_quizzed') or []) if str(s).isdigit()]
                quizzed = [s for s in quizzed if s in allowed]
                have = prestudy.senses_with_exercises(db, quizzed) if quizzed else set()
                out['generation_queued'] = prestudy.request_generation(
                    db, quizzed, language_id, {str(s): [True] for s in have})
        if mode == 'prime':
            # New-word drill (ADR-040): drilled words enter the ladder's intro
            # drill; a word that met session 1's target in the prime starts at
            # session 2. Words over today's quota come back as `overflow`.
            try:
                from services import intro_drill
                from services.practice_session_service import PracticeSessionService
                metrics = body.get('metrics') if isinstance(body.get('metrics'), dict) else {}
                drilled = [int(s) for s in (metrics.get('words_quizzed') or []) if str(s).isdigit() and int(s) in allowed]
                met = {int(s) for s in (metrics.get('met_sense_ids') or []) if str(s).isdigit()}
                out['intro'] = intro_drill.admit_prestudy(
                    PracticeSessionService(db), user_id, language_id, drilled, met)
            except Exception as e:
                logger.warning("prestudy intro admission failed for %s: %s", identifier, e)
        return api_success(data=out)
    except Exception as e:
        logger.error("Error recording prestudy evidence for %s: %s", identifier, e)
        logger.error(traceback.format_exc())
        return server_error('Failed to record prestudy answers')


@tests_bp.route('/<identifier>/prestudy/admit-overflow', methods=['POST'])
@supabase_jwt_required
def admit_prestudy_overflow(identifier):
    """'Add them all now': start the prime's over-quota words today.

    Body: {sense_ids: [...]}. Only words of this test that the prime queued in
    the last 6 hours qualify (services.intro_drill.overload).
    """
    try:
        db = current_app.supabase_service
        if not db:
            return service_unavailable("Service not available")
        test = _find_test_for_prestudy(db, identifier)
        if not test:
            return not_found("Test not found")
        body = request.get_json(silent=True) or {}
        ids = body.get('sense_ids')
        if not isinstance(ids, list) or not ids or len(ids) > 200:
            return bad_request("sense_ids must be a list of 1-200 ids")
        from services import prestudy, intro_drill
        allowed = prestudy.test_sense_ids(db, test)
        ids = [int(s) for s in ids if str(s).isdigit() and int(s) in allowed]
        done = intro_drill.overload(db, g.current_user_id, int(test['language_id']), ids)
        return api_success(data={'started': done})
    except Exception as e:
        logger.error("Error admitting prestudy overflow for %s: %s", identifier, e)
        return server_error('Failed to add words')


@tests_bp.route('/<identifier>/prestudy/produce', methods=['POST'])
@supabase_jwt_required
def start_test_prestudy_produce(identifier):
    """Produce: open a dual-translation passage on the window of this test with
    the most primed senses (tie-break: senses behind wrong questions, then
    shorter). Requires an attempt (DT's rule). Body: {l1_language_id?}.

    Returns the same object as POST /api/dual-translation/passage-from-sentences
    plus ``sentence_start``/``sentence_end``; 422 NO_WINDOW when no 2-4
    sentence window has usable references in the learner's language.
    """
    try:
        db = current_app.supabase_service
        if not db:
            return service_unavailable("Service not available")
        test = _find_test_for_prestudy(db, identifier)
        if not test:
            return not_found("Test not found")
        from services import prestudy
        from services.vocabulary.gloss_lookup import get_user_definition_language_id
        user_id = g.current_user_id
        body = request.get_json(silent=True) or {}
        try:
            l1 = int(body.get('l1_language_id') or get_user_definition_language_id(db, user_id) or 2)
        except (TypeError, ValueError):
            return bad_request("l1_language_id must be a language id")
        if l1 == int(test['language_id']):
            l1 = 2 if int(test['language_id']) != 2 else None
        if not l1:
            return api_error("No reference language for this test", 422, error_code="NO_WINDOW")
        attempt_id, wrong = prestudy.wrong_question_senses(db, user_id, test['id'])
        if not attempt_id:
            return forbidden("Take the test before Produce")
        prime = prestudy.latest_prime_session(db, user_id, test['id'])
        primed = [int(s) for s in ((prime or {}).get('words_quizzed') or [])]
        if not primed:
            # prime skipped or not recorded: target the words the client says
            # were unknown (still restricted to this test's senses below)
            primed = [int(s) for s in (body.get('fallback_sense_ids') or []) if str(s).isdigit()][:24]
        allowed = prestudy.test_sense_ids(db, test)
        primed = [s for s in primed if s in allowed][:24]
        window = prestudy.choose_produce_window(db, test, l1, primed, wrong)
        if not window:
            return api_error("No sentence window with references in your language", 422, error_code="NO_WINDOW")
        from routes.dual_translation import open_range_passage
        return open_range_passage(
            db, user_id, str(test['id']), window[0], window[1], l1, primed,
            extra={'sentence_start': window[0], 'sentence_end': window[1], 'test_id': test['id']},
        )
    except Exception as e:
        logger.error("Error starting Produce for %s: %s", identifier, e)
        logger.error(traceback.format_exc())
        return server_error('Failed to start Produce')
