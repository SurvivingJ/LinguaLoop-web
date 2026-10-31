"""Test prestudy: the data a learner needs to study a test before taking it.

Spec: wiki/features/test-prestudy.md (modes 1 and 2, readiness check).

``build_prestudy_payload`` returns one object in the shape the prestudy page
(static/js/prestudy/prestudy.js) reads:

    {
      test:       {id, slug, title, language_id, transcript, audio_url,
                   difficulty, target_age_tier, vocab_sense_ids,
                   vocab_token_map, furigana_payload, pinyin_payload},
      questions:  [{sense_ids}],                 # question-linked senses only
      senses:     {sense_id: {lemma, pos, freq, reading,
                              glosses: {lang_id: {def, ex}}}},
      knowledge:  {sense_id: {p, status, n}},    # the learner's BKT rows
      exercises:  {sense_id: [{id, type, group, level, c}]},
      gloss_language_id, ability_zipf
    }

The scored questions' text, choices and answers are never included: prestudy
must not leak the test. Only each question's linked senses are sent, so the
page can rank the words the questions turn on first.

Functions here read the database but never write; evidence is written by the
route through VocabularyKnowledgeService.update_from_word_tests_batch.
"""

from __future__ import annotations

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

# Ladder exercise types the prestudy prime can render, the content fields each
# renderer needs, and which practice round (use / judge) it belongs to.
EXERCISE_FIELDS = {
    'cloze_completion': ['sentence_with_blank', 'options', 'correct_answer', 'explanation', 'original_sentence'],
    'cloze_typed': ['sentence_with_blank', 'answer', 'original_sentence', 'target_word'],
    'semantic_discrimination': ['sentences', 'explanation', 'target_word'],
    'spot_incorrect_sentence': ['sentences'],
    'tl_nl_translation': ['tl_sentence', 'options', 'correct_nl'],
    'jumbled_sentence': ['chunks', 'correct_ordering', 'original_sentence'],
    'definition_match': ['word', 'options', 'correct_definition', 'pronunciation'],
    'particle_selection': ['sentence_with_blank', 'options', 'correct_answer', 'original_sentence', 'nl'],
    'morphology_slot': ['sentence_with_blank', 'options', 'correct_answer', 'explanation', 'original_sentence', 'form_label'],
    'synonym_antonym_match': ['word', 'options', 'correct_answer', 'relation', 'nl'],
}
EXERCISE_GROUP = {
    'cloze_completion': 'use', 'cloze_typed': 'use', 'particle_selection': 'use',
    'morphology_slot': 'use', 'definition_match': 'use',
    'semantic_discrimination': 'judge', 'spot_incorrect_sentence': 'judge',
    'tl_nl_translation': 'judge', 'jumbled_sentence': 'judge', 'synonym_antonym_match': 'judge',
}
MAX_EXERCISES_PER_TYPE = 2
DEFAULT_ABILITY_ZIPF = 5.0


def trim_exercise(row: dict, rng: random.Random | None = None) -> Optional[dict]:
    """Keep only what a prestudy renderer needs from an ``exercises`` row."""
    t = row.get('exercise_type')
    fields = EXERCISE_FIELDS.get(t)
    content = row.get('content') or {}
    if not fields or not isinstance(content, dict):
        return None
    c = {k: content.get(k) for k in fields if k in content}
    if isinstance(c.get('nl'), dict):
        c['nl'] = {'en': c['nl'].get('en')}
    if t == 'cloze_typed':
        c['answer'] = {'accepted': ((content.get('answer') or {}).get('accepted') or [])}
    return {'id': row.get('id'), 'type': t, 'group': EXERCISE_GROUP[t],
            'level': row.get('ladder_level'), 'c': c}


def group_exercises(rows: list[dict], seed: int = 0) -> dict[str, list[dict]]:
    """At most MAX_EXERCISES_PER_TYPE trimmed exercises per sense and type."""
    rng = random.Random(seed)
    by_sense: dict[int, dict[str, list[dict]]] = {}
    for r in rows:
        item = trim_exercise(r)
        if item is None:
            continue
        by_sense.setdefault(r['word_sense_id'], {}).setdefault(item['type'], []).append(item)
    out: dict[str, list[dict]] = {}
    for sid, types in by_sense.items():
        picked: list[dict] = []
        for items in types.values():
            rng.shuffle(items)
            picked.extend(items[:MAX_EXERCISES_PER_TYPE])
        out[str(sid)] = picked
    return out


def _chunks(seq: list, n: int = 200):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _load_senses(db, sense_ids: list[int], gloss_language_id: Optional[int]) -> dict[str, dict]:
    """Lemma, POS, frequency, reading and glosses (native + preferred) per sense."""
    rows: list[dict] = []
    for part in _chunks(sense_ids):
        rows += db.table('dim_word_senses').select(
            'id, vocab_id, sense_rank, definition, definition_language_id, example_sentence, pronunciation, '
            'dim_vocabulary(lemma, part_of_speech, frequency_rank, reading, language_id)'
        ).in_('id', part).execute().data or []
    senses: dict[str, dict] = {}
    wanted: dict[tuple, int] = {}
    for r in rows:
        v = r.get('dim_vocabulary') or {}
        sid = str(r['id'])
        senses[sid] = {
            'lemma': v.get('lemma') or '',
            'pos': v.get('part_of_speech'),
            'freq': v.get('frequency_rank'),
            'reading': v.get('reading') or r.get('pronunciation'),
            'glosses': {str(r.get('definition_language_id')): {'def': r.get('definition'), 'ex': r.get('example_sentence')}},
        }
        if gloss_language_id and gloss_language_id != r.get('definition_language_id'):
            wanted[(r['vocab_id'], r.get('sense_rank'))] = r['id']
    if wanted:
        vocab_ids = sorted({k[0] for k in wanted})
        for part in _chunks(vocab_ids):
            for g in db.table('dim_word_senses').select(
                'vocab_id, sense_rank, definition, example_sentence, definition_language_id'
            ).in_('vocab_id', part).eq('definition_language_id', gloss_language_id).execute().data or []:
                sid = wanted.get((g['vocab_id'], g.get('sense_rank')))
                if sid is not None and g.get('definition'):
                    senses[str(sid)]['glosses'][str(gloss_language_id)] = {'def': g['definition'], 'ex': g.get('example_sentence')}
    return senses


def _load_knowledge(db, user_id: str, sense_ids: list[int]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for part in _chunks(sense_ids):
        for k in db.table('user_vocabulary_knowledge').select(
            'sense_id, p_known, status, evidence_count'
        ).eq('user_id', user_id).in_('sense_id', part).execute().data or []:
            out[str(k['sense_id'])] = {'p': float(k['p_known']), 'status': k.get('status'), 'n': k.get('evidence_count') or 0}
    return out


def _load_exercises(db, sense_ids: list[int]) -> dict[str, list[dict]]:
    rows: list[dict] = []
    for part in _chunks(sense_ids):
        rows += db.table('exercises').select(
            'id, word_sense_id, exercise_type, content, ladder_level'
        ).eq('is_active', True).in_('word_sense_id', part).in_('exercise_type', list(EXERCISE_FIELDS)).execute().data or []
    return group_exercises(rows)


def _ability_zipf(db, user_id: str, language_id: int) -> float:
    try:
        r = db.table('user_calibration_state').select('ability_zipf').eq('user_id', user_id) \
            .eq('language_id', language_id).limit(1).execute().data
        if r and r[0].get('ability_zipf') is not None:
            return float(r[0]['ability_zipf'])
    except Exception as e:  # optional signal; the prior falls back to the default
        logger.info("ability_zipf lookup skipped for %s: %s", user_id, e)
    return DEFAULT_ABILITY_ZIPF


def build_prestudy_payload(db, test: dict, user_id: str, gloss_language_id: Optional[int]) -> dict:
    """Everything the prestudy page needs for one test (see module docstring).

    ``test`` is a ``tests`` row with at least id, slug, title, language_id,
    transcript, audio_url, difficulty, target_age_tier, vocab_sense_ids,
    vocab_token_map, furigana_payload, pinyin_payload.
    """
    sense_ids = sorted({int(s) for s in (test.get('vocab_sense_ids') or []) if s})
    questions = db.table('questions').select('sense_ids').eq('test_id', test['id']).execute().data or []
    q_sense_ids = sorted({int(s) for q in questions for s in (q.get('sense_ids') or []) if s})
    all_ids = sorted(set(sense_ids) | set(q_sense_ids))
    senses = _load_senses(db, all_ids, gloss_language_id) if all_ids else {}
    return {
        'test': {k: test.get(k) for k in (
            'id', 'slug', 'title', 'language_id', 'transcript', 'audio_url', 'difficulty',
            'target_age_tier', 'vocab_sense_ids', 'vocab_token_map', 'furigana_payload', 'pinyin_payload')},
        'questions': [{'sense_ids': q.get('sense_ids') or []} for q in questions],
        'senses': senses,
        'knowledge': _load_knowledge(db, user_id, all_ids) if all_ids else {},
        'exercises': _load_exercises(db, sense_ids) if sense_ids else {},
        'gloss_language_id': gloss_language_id or int(test.get('language_id') or 0),
        'ability_zipf': _ability_zipf(db, user_id, int(test.get('language_id') or 0)),
    }


def evidence_rows(answers: list[dict], allowed_sense_ids: set[int]) -> list[dict]:
    """Collapse the prime's answers into one word-test evidence row per sense.

    Each answer is {sense_id, correct, idk}. "I don't know" counts as wrong,
    the same as calibration's explicit skip. A sense is recorded correct only
    when its correct answers outnumber its wrong ones: the batch RPC merges
    duplicate rows with bool_or, so sending every answer would let one late
    correct answer erase four misses. Senses not in the test are dropped, so
    the endpoint cannot write evidence for arbitrary words.
    """
    tally: dict[int, list[int]] = {}
    for a in answers or []:
        try:
            sid = int(a.get('sense_id'))
        except (TypeError, ValueError):
            continue
        if sid not in allowed_sense_ids:
            continue
        ok = bool(a.get('correct')) and not a.get('idk')
        t = tally.setdefault(sid, [0, 0])
        t[0 if ok else 1] += 1
    return [{'sense_id': sid, 'is_correct': c > w} for sid, (c, w) in sorted(tally.items())]


# ---------------------------------------------------------------------------
# Sessions, measurement and next-day review (migrations/prestudy_workflow.sql)
#
# Every function below is best-effort around the new tables: until the
# migration is applied PostgREST answers "relation not found" and prestudy
# keeps working unmeasured (start returns None, nothing is verified).
# ---------------------------------------------------------------------------

from datetime import date, datetime, timedelta, timezone  # noqa: E402

PRESTUDY_WINDOW_HOURS = 6
TRIGGERS = ('opt_in', 'auto', 'retry')
PLAN_MODES = ('full', 'light', 'none')
FOLLOWUP_REASONS = ('idk_twice', 'readiness_missed', 'primed_missed_in_test', 'omitted_in_produce')
MAX_ACTIVE_SECONDS = 3600
GENERATION_REASON = 'prestudy'
MAX_GENERATION_PER_SESSION = 8


def is_missing_relation_error(exc) -> bool:
    """PostgREST/PG "table or column does not exist" (migration not applied)."""
    text = str(exc)
    return any(code in text for code in ('PGRST205', 'PGRST204', '42P01', '42703')) \
        or 'does not exist' in text or 'Could not find the table' in text


def _int(v, lo: int = 0, hi: int = 100000) -> int:
    if isinstance(v, bool):
        return lo
    try:
        n = int(v)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, n))


def _sense_list(values, allowed: set[int], limit: int = 200) -> list[int]:
    out: list[int] = []
    for v in values or []:
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if n in allowed and n not in out:
            out.append(n)
        if len(out) >= limit:
            break
    return out


def test_sense_ids(db, test: dict) -> set[int]:
    """The senses a prestudy for ``test`` may write about: the passage's linked
    senses plus every question's senses."""
    allowed = {int(s) for s in (test.get('vocab_sense_ids') or []) if s}
    rows = db.table('questions').select('sense_ids').eq('test_id', test['id']).execute().data or []
    allowed |= {int(s) for q in rows for s in (q.get('sense_ids') or []) if s}
    return allowed


def start_session(db, user_id: str, test: dict, *, test_type: str = 'reading', trigger: str = 'opt_in',
                  plan_mode: Optional[str] = None, unknown_share=None, mode: str = 'prime',
                  session_block_id: Optional[str] = None, load_date: Optional[str] = None) -> Optional[str]:
    """Insert an ``open`` prestudy_sessions row; returns its id or None."""
    try:
        share = float(unknown_share)
        share = round(max(0.0, min(1.0, share)), 3)
    except (TypeError, ValueError):
        share = None
    row = {
        'user_id': user_id,
        'language_id': int(test['language_id']),
        'test_id': test['id'],
        'test_type': test_type if test_type in ('reading', 'listening') else 'reading',
        'mode': mode if mode in ('prime', 'followup') else 'prime',
        'trigger': trigger if trigger in TRIGGERS else 'opt_in',
        'plan_mode': plan_mode if plan_mode in PLAN_MODES else None,
        'unknown_share_at_open': share,
        'session_block_id': (str(session_block_id)[:64] if session_block_id else None),
        'load_date': load_date,
        'minutes_source': 'tests_share' if session_block_id else 'free',
    }
    try:
        res = db.table('prestudy_sessions').insert(row).execute()
        return (res.data or [{}])[0].get('id')
    except Exception as e:
        if is_missing_relation_error(e):
            logger.info("prestudy_sessions not available yet: %s", e)
        else:
            logger.warning("prestudy session start failed: %s", e)
        return None


def get_session(db, user_id: str, session_id: str) -> Optional[dict]:
    if not session_id:
        return None
    try:
        rows = db.table('prestudy_sessions').select('*').eq('id', session_id).eq('user_id', user_id) \
            .limit(1).execute().data or []
    except Exception as e:
        logger.info("prestudy session lookup skipped: %s", e)
        return None
    return rows[0] if rows else None


def followups_from_answers(answers: list[dict], allowed: set[int]) -> dict[int, str]:
    """Senses that earn a next-day review, from the prime's own answers:
    "I don't know" twice -> idk_twice; missed in the readiness check ->
    readiness_missed. Server-derived, so the client cannot add arbitrary words."""
    idk: dict[int, int] = {}
    out: dict[int, str] = {}
    for a in answers or []:
        try:
            sid = int(a.get('sense_id'))
        except (TypeError, ValueError):
            continue
        if sid not in allowed:
            continue
        if a.get('idk'):
            idk[sid] = idk.get(sid, 0) + 1
        if a.get('stage') == 'readiness' and (a.get('idk') or not a.get('correct')):
            out.setdefault(sid, 'readiness_missed')
    for sid, n in idk.items():
        if n >= 2:
            out[sid] = 'idk_twice'
    return out


def _tomorrow_iso(db, user_id: str, language_id: int) -> str:
    try:
        from services.day_boundary import plan_today_iso
        today = date.fromisoformat(plan_today_iso(db, user_id, language_id))
    except Exception:
        today = datetime.now(timezone.utc).date()
    return (today + timedelta(days=1)).isoformat()


def add_followups(db, user_id: str, language_id: int, session_id: Optional[str],
                  reasons: dict[int, str]) -> int:
    """Insert next-day review rows (idempotent per user, sense, due date)."""
    rows = [r for r in reasons.items() if r[1] in FOLLOWUP_REASONS]
    if not rows:
        return 0
    due = _tomorrow_iso(db, user_id, language_id)
    payload = [{'user_id': user_id, 'language_id': int(language_id), 'sense_id': int(sid),
                'session_id': session_id, 'reason': reason, 'due_date': due} for sid, reason in rows]
    try:
        db.table('prestudy_followups').upsert(payload, on_conflict='user_id,sense_id,due_date',
                                              ignore_duplicates=True).execute()
        return len(payload)
    except Exception as e:
        logger.info("prestudy followups not written: %s", e)
        return 0


def request_generation(db, sense_ids: list[int], language_id: int, exercises: dict) -> int:
    """Queue exercise generation for primed words that have no ladder exercises
    (reason ``prestudy``); the nightly drain picks them up."""
    missing = [s for s in sense_ids if not exercises.get(str(s))][:MAX_GENERATION_PER_SESSION]
    if not missing:
        return 0
    try:
        from services.vocabulary_ladder import queue_drain
    except Exception as e:
        logger.warning("generation queue unavailable: %s", e)
        return 0
    queued = 0
    for sid in missing:
        try:
            if queue_drain.enqueue(db, int(sid), int(language_id), GENERATION_REASON, detail={'source': 'prestudy'}):
                queued += 1
        except Exception as e:
            logger.warning("could not queue sense %s for generation: %s", sid, e)
    return queued


def senses_with_exercises(db, sense_ids: list[int]) -> set[int]:
    out: set[int] = set()
    for part in _chunks(sorted(set(sense_ids))):
        for r in db.table('exercises').select('word_sense_id').eq('is_active', True) \
                .in_('word_sense_id', part).execute().data or []:
            out.add(int(r['word_sense_id']))
    return out


def complete_session(db, user_id: str, session: dict, metrics: dict, allowed: set[int],
                     followup_reasons: dict[int, str]) -> dict:
    """Write the measurement record, credit the minutes, add next-day reviews.

    ``metrics`` is the client's summary; every number is clamped and every
    sense list is restricted to ``allowed`` (the test's senses).
    """
    m = metrics or {}
    words_quizzed = _sense_list(m.get('words_quizzed'), allowed)
    next_day = sorted(set(_sense_list(m.get('next_day_review_senses'), allowed)) | set(followup_reasons))
    readiness_n = _int(m.get('readiness_n'), 0, 20)
    update = {
        'words_shown': _sense_list(m.get('words_shown'), allowed),
        'words_quizzed': words_quizzed,
        'exposures': _int(m.get('exposures')),
        'first_try_correct': _int(m.get('first_try_correct')),
        'first_try_total': _int(m.get('first_try_total')),
        'idk_count': _int(m.get('idk_count')),
        'boosters': _int(m.get('boosters')),
        'ladder_exercises': _int(m.get('ladder_exercises')),
        'readiness_score': _int(m.get('readiness_score'), 0, readiness_n) if readiness_n else None,
        'readiness_n': readiness_n or None,
        'readiness_rounds': _int(m.get('readiness_rounds'), 0, 5),
        'ready': bool(m.get('ready')) if m.get('ready') is not None else None,
        'next_day_review_senses': next_day,
        'minutes_est': _int(m.get('minutes_est'), 0, 60),
        'active_seconds': _int(m.get('active_seconds'), 0, MAX_ACTIVE_SECONDS),
        'tests_dropped_today': _int(m.get('tests_dropped_today'), 0, 3),
        'status': 'completed' if session.get('status') == 'open' else session.get('status'),
        'completed_at': datetime.now(timezone.utc).isoformat(),
    }
    if session.get('mode') == 'followup':
        update['followup'] = {'words': words_quizzed, 'first_try_correct': update['first_try_correct'],
                              'first_try_total': update['first_try_total']}
    try:
        db.table('prestudy_sessions').update(update).eq('id', session['id']).eq('user_id', user_id).execute()
    except Exception as e:
        logger.warning("prestudy session complete failed: %s", e)
    credited = False
    if update['active_seconds'] > 0:
        try:
            from services.study_time import credit_study_time
            credited = credit_study_time(db, user_id, session['language_id'], 'prestudy',
                                         update['active_seconds'], 'prestudy_sessions', session['id'])
        except Exception as e:
            logger.warning("prestudy minutes not credited: %s", e)
    n_follow = add_followups(db, user_id, int(session['language_id']), session['id'], followup_reasons)
    return {'session_id': session['id'], 'credited': credited, 'followups': n_follow,
            'next_day_review_senses': next_day}


def find_prestudy_for_attempt(db, user_id: str, test_id: str, now: Optional[datetime] = None):
    """The completed, unspent prime session for this test in the last 6 hours.

    Returns (session_id | None, verifiable). ``verifiable`` is False when the
    table does not exist yet, so the caller may fall back to the client flag.
    """
    now = now or datetime.now(timezone.utc)
    since = (now - timedelta(hours=PRESTUDY_WINDOW_HOURS)).isoformat()
    try:
        rows = db.table('prestudy_sessions').select('id, status, mode, completed_at') \
            .eq('user_id', user_id).eq('test_id', test_id).eq('mode', 'prime').eq('status', 'completed') \
            .gte('completed_at', since).order('completed_at', desc=True).limit(1).execute().data or []
    except Exception as e:
        if is_missing_relation_error(e):
            return None, False
        logger.warning("prestudy verification failed: %s", e)
        return None, True
    return (rows[0]['id'] if rows else None), True


def consume_session(db, session_id: str, attempt_id: Optional[str]) -> None:
    try:
        db.table('prestudy_sessions').update({
            'status': 'consumed', 'attempt_id': attempt_id,
            'consumed_at': datetime.now(timezone.utc).isoformat(),
        }).eq('id', session_id).execute()
    except Exception as e:
        logger.warning("prestudy session %s not marked consumed: %s", session_id, e)


# ---------------------------------------------------------------------------
# Post-test follow-up and Produce
# ---------------------------------------------------------------------------

#: Mean reference tightness a Produce window needs, per test language
#: (wiki/evaluations/sentence-refs-pilot-2026-10-30.md: ja 0.65, zh 0.70, en 0.60).
PRODUCE_TIGHTNESS_FLOOR = {1: 0.70, 2: 0.60, 3: 0.65}
FOLLOWUP_MAX_WORDS = 5
_USABLE_VERDICTS = ('pass', 'rewritten')


def wrong_question_senses(db, user_id: str, test_id: str) -> tuple[Optional[str], list[int]]:
    """Senses behind the questions answered wrong on the learner's latest
    attempt at this test: (attempt_id, sense ids in question order)."""
    att = db.table('test_attempts').select('id').eq('user_id', user_id).eq('test_id', test_id) \
        .order('created_at', desc=True).limit(1).execute().data or []
    if not att:
        return None, []
    attempt_id = att[0]['id']
    qar = db.table('question_attempt_results').select('question_id, is_correct') \
        .eq('attempt_id', attempt_id).eq('user_id', user_id).execute().data or []
    wrong_q = [r['question_id'] for r in qar if r.get('is_correct') is False]
    if not wrong_q:
        return attempt_id, []
    qs = db.table('questions').select('id, sense_ids').in_('id', wrong_q).execute().data or []
    out: list[int] = []
    for q in qs:
        for s in q.get('sense_ids') or []:
            if s and int(s) not in out:
                out.append(int(s))
    return attempt_id, out


def latest_prime_session(db, user_id: str, test_id: str, hours: int = 24) -> Optional[dict]:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    try:
        rows = db.table('prestudy_sessions').select('id, words_quizzed, produce, status, language_id') \
            .eq('user_id', user_id).eq('test_id', test_id).eq('mode', 'prime') \
            .in_('status', ['completed', 'consumed']).gte('started_at', since) \
            .order('started_at', desc=True).limit(1).execute().data or []
    except Exception as e:
        logger.info("prime session lookup skipped: %s", e)
        return None
    return rows[0] if rows else None


def primed_missed(prime_words, followup_answers: list[dict], allowed: set[int]) -> dict[int, str]:
    """Primed in Study and still behind a wrong question -> next-day review."""
    primed = {int(s) for s in (prime_words or [])}
    out: dict[int, str] = {}
    for a in followup_answers or []:
        try:
            sid = int(a.get('sense_id'))
        except (TypeError, ValueError):
            continue
        if sid in primed and sid in allowed:
            out[sid] = 'primed_missed_in_test'
    return out


def choose_produce_window(db, test: dict, l1_language_id: int, primed: list[int],
                          wrong: list[int]) -> Optional[tuple[int, int]]:
    """The 2-4 sentence window with the most primed senses (then wrong-question
    senses, then shorter) whose references all exist in ``l1_language_id`` and
    clear the language's tightness floor."""
    from services.dual_translation.passage_builder import select_window_for_primed
    rows = db.table('test_sentences').select('id, idx, l2_text, token_start, token_end, transcript_hash') \
        .eq('test_id', test['id']).order('idx').execute().data or []
    if not rows:
        return None
    by_id = {r['id']: r for r in rows}
    refs = []
    for part in _chunks(list(by_id)):
        refs += db.table('test_sentence_references').select('sentence_id, tightness, review_verdict') \
            .in_('sentence_id', part).eq('l1_language_id', int(l1_language_id)).eq('is_active', True) \
            .in_('review_verdict', list(_USABLE_VERDICTS)).execute().data or []
    refs_ok, tight = set(), {}
    for r in refs:
        row = by_id.get(r['sentence_id'])
        if not row:
            continue
        refs_ok.add(int(row['idx']))
        if r.get('tightness') is not None:
            tight[int(row['idx'])] = float(r['tightness'])
    floor = PRODUCE_TIGHTNESS_FLOOR.get(int(test['language_id']), 0.6)
    return select_window_for_primed(rows, primed, wrong, refs_ok, tight, floor,
                                    token_map=test.get('vocab_token_map'))


def record_produce(db, user_id: str, test_id: str, language_id: int, submission_id,
                   target_rows: list[dict]) -> int:
    """After a Produce grade: store the result on the prime session and send
    omitted primed words to next-day review. Never raises."""
    try:
        rows = [r for r in (target_rows or []) if r.get('sense_id')]
        if not rows:
            return 0
        omitted = {int(r['sense_id']): 'omitted_in_produce' for r in rows if r.get('status') == 'omitted'}
        session = latest_prime_session(db, user_id, test_id)
        if session:
            try:
                db.table('prestudy_sessions').update({'produce': {
                    'submission_id': submission_id,
                    'produced': sum(1 for r in rows if r.get('status') == 'produced'),
                    'variant': sum(1 for r in rows if r.get('status') == 'variant'),
                    'omitted': len(omitted),
                    'senses': [int(r['sense_id']) for r in rows],
                }}).eq('id', session['id']).eq('user_id', user_id).execute()
            except Exception as e:
                logger.info("produce result not stored: %s", e)
        return add_followups(db, user_id, language_id, session['id'] if session else None, omitted)
    except Exception as e:
        logger.warning("record_produce failed (non-fatal): %s", e)
        return 0


# ---------------------------------------------------------------------------
# Next-day review: served inside the Maintenance practice pool
# ---------------------------------------------------------------------------

def due_followup_senses(db, user_id: str, language_id: int, today_iso: str, limit: int = 10) -> list[int]:
    """Senses whose prestudy next-day review is due and not yet done."""
    try:
        rows = db.table('prestudy_followups').select('sense_id') \
            .eq('user_id', user_id).eq('language_id', int(language_id)) \
            .lte('due_date', today_iso).is_('completed_at', 'null') \
            .order('due_date').limit(limit).execute().data or []
    except Exception as e:
        if not is_missing_relation_error(e):
            logger.warning("prestudy followups lookup failed: %s", e)
        return []
    out: list[int] = []
    for r in rows:
        if r['sense_id'] not in out:
            out.append(int(r['sense_id']))
    return out


def mark_followups(db, user_id: str, sense_ids: list[int], field: str = 'served_at') -> None:
    if not sense_ids or field not in ('served_at', 'completed_at'):
        return
    try:
        q = db.table('prestudy_followups').update({field: datetime.now(timezone.utc).isoformat()}) \
            .eq('user_id', user_id).in_('sense_id', [int(s) for s in sense_ids]).is_('completed_at', 'null')
        if field == 'served_at':
            q = q.is_('served_at', 'null')
        q.execute()
    except Exception as e:
        logger.info("prestudy followups not marked %s: %s", field, e)


# ---------------------------------------------------------------------------
# Daily session planning (Triggers; Time, shown honestly)
# ---------------------------------------------------------------------------

import math  # noqa: E402

AUTO_THRESHOLD = 0.25          # unknown share above which a new test gets a full prestudy block
LIGHT_THRESHOLD = 0.05         # 5-25%: light prime (three words)
PRESTUDY_TEST_TYPES = ('reading', 'listening')
PRESTUDY_MODES = ('auto', 'ask', 'off')
_PRIOR_K = 1.5
_PRIOR_B = math.log(0.85 / 0.15)


def prior_p_known(freq, ability: float) -> float:
    """Zipf prior used when a learner has no row for a sense (matches the page)."""
    if freq is None:
        return 0.3
    return 1.0 / (1.0 + math.exp(-(_PRIOR_K * (float(freq) - ability) + _PRIOR_B)))


def estimate_minutes(unknown: int, with_exercises: int, plan_mode: str) -> int:
    """Study-first estimate: ~5 exposures x 8 s per primed word, two ladder
    exercises x 20 s where the word has them, the readiness check and a
    minute of preview. Same formula as static/js/prestudy/prestudy.js."""
    if plan_mode == 'light':
        return 1
    k = min(8, unknown)
    ex = min(k, with_exercises)
    return int(min(10, max(2, round((60 + k * 5 * 8 + ex * 2 * 20 + 5 * 8) / 60))))


def get_prestudy_mode(db, user_id: str, language_id: int) -> str:
    try:
        rows = db.table('user_study_plans').select('prestudy_mode').eq('user_id', user_id) \
            .eq('language_id', language_id).limit(1).execute().data or []
        mode = (rows[0].get('prestudy_mode') if rows else None) or 'auto'
        return mode if mode in PRESTUDY_MODES else 'auto'
    except Exception as e:
        logger.info("prestudy_mode not readable (%s); using auto", e)
        return 'auto'


def plan_for_tests(db, user_id: str, language_id: int, tests: list[dict]) -> dict[str, dict]:
    """Unknown share and study estimate per reading/listening test.

    ``tests`` are daily-load test dicts (id, test_type, slot_type, is_completed).
    Returns {test_id: {unknown_share, unknown, n, plan_mode, minutes_est}} for
    tests that have linked senses. One query per table for the whole day.
    """
    wanted = [t for t in tests if t.get('test_type') in PRESTUDY_TEST_TYPES and t.get('id')]
    if not wanted:
        return {}
    rows = db.table('tests').select('id, vocab_sense_ids').in_('id', [t['id'] for t in wanted]).execute().data or []
    senses_by_test = {r['id']: sorted({int(s) for s in (r.get('vocab_sense_ids') or []) if s}) for r in rows}
    all_ids = sorted({s for ids in senses_by_test.values() for s in ids})
    if not all_ids:
        return {}
    knowledge = _load_knowledge(db, user_id, all_ids)
    missing = [s for s in all_ids if str(s) not in knowledge]
    freq: dict[int, Optional[float]] = {}
    for part in _chunks(missing):
        for r in db.table('dim_word_senses').select('id, dim_vocabulary(frequency_rank)').in_('id', part) \
                .execute().data or []:
            freq[int(r['id'])] = (r.get('dim_vocabulary') or {}).get('frequency_rank')
    ability = _ability_zipf(db, user_id, language_id)

    def p(sid: int) -> float:
        k = knowledge.get(str(sid))
        return float(k['p']) if k else prior_p_known(freq.get(sid), ability)

    unknown_by_test = {tid: [s for s in ids if p(s) < 0.5] for tid, ids in senses_by_test.items()}
    top = sorted({s for u in unknown_by_test.values() for s in u[:8]})
    have_ex = senses_with_exercises(db, top) if top else set()
    plans: dict[str, dict] = {}
    for tid, ids in senses_by_test.items():
        if not ids:
            continue
        unknown = unknown_by_test[tid]
        share = len(unknown) / len(ids)
        plan_mode = 'full' if share > AUTO_THRESHOLD else ('light' if share >= LIGHT_THRESHOLD else 'none')
        plans[tid] = {
            'unknown_share': round(share, 3),
            'unknown': len(unknown),
            'n': len(ids),
            'plan_mode': plan_mode,
            'minutes_est': estimate_minutes(len(unknown), len([s for s in unknown[:8] if s in have_ex]), plan_mode),
        }
    return plans
