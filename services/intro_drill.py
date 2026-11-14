"""New-word drill: criterion-based intro sessions before the ladder.

Spec: wiki/features/new-word-drill.tech.md, ADR-040.

A newly admitted ladder word has ``word_state = 'intro'`` and goes through four
intro sessions (day 0 / 1 / 2 / 4). Each session runs until the word has been
answered right a target number of times (5 / 3 / 2 / 2), where a right answer
only *counts* when at least ``gap`` other items came since the word was last
shown, the format differs from the last counted one, and it was not "I don't
know". Sessions 2-4 open with a cold recall; missing it adds one to the target.
Passing session 4 puts the word on ladder ring 2.

The client (static/js/session/players/intro_drill.js) runs the drill and posts
each finished word's attempts; ``recount`` here re-applies the same counting
rules, so the server never trusts a client "passed".
"""

from __future__ import annotations

import logging
import math
import random
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from config import Config

logger = logging.getLogger(__name__)

ENABLED = bool(getattr(Config, 'NEW_WORD_DRILL_ENABLED', True))

INTRO_TARGETS = {1: 5, 2: 3, 3: 2, 4: 2}
INTRO_COLD_MISS_BUMP = 1
INTRO_ITEM_CAPS = {1: 12, 2: 8, 3: 6, 4: 6}
INTRO_GAP_DAYS = {2: 1, 3: 1, 4: 2}           # days after completing the previous stage
INTRO_MIN_GAP_ITEMS = 4
INTRO_STAGE_ITEMS_EST = {1: 7, 2: 4, 3: 3, 4: 3}
INTRO_ITEM_SECONDS = 10
INTRO_GRADUATE_FORM_RECOGNITION = 0.55
INTRO_BLOCK_MAX_WORDS = 40
INTRO_HISTORY_KEEP = 12
MAX_ATTEMPTS_PER_WORD = 20

COLD_FORMAT = {'ja': 'read_typed', 'zh': 'read_typed', 'en': 'recall_typed'}
# Preference order per stage. Unbuildable formats are dropped per word.
STAGE_FORMATS = {
    ('cjk', 1): ['read_typed', 'def_mc', 'read_typed2', 'rev_mc', 'cloze_mc'],
    ('en', 1): ['def_mc', 'rev_mc', 'cloze_mc', 'recall_typed', 'ex_use'],
    (None, 2): ['ex_use', 'ex_judge', 'def_mc', 'rev_mc'],
    (None, 3): ['ex_judge', 'ex_use', 'cloze_mc', 'rev_mc'],
    (None, 4): ['cloze_typed', 'ex_use', 'rev_mc', 'def_mc'],
}
KNOWN_FORMATS = {'read_typed', 'read_typed2', 'def_mc', 'rev_mc', 'cloze_mc',
                 'cloze_typed', 'recall_typed', 'ex_use', 'ex_judge'}
# Ladder exercise types the intro drill renders (client-graded by ExRenderers).
EX_GROUPS = {
    'cloze_completion': 'use', 'particle_selection': 'use', 'morphology_slot': 'use',
    'definition_match': 'use',
    'semantic_discrimination': 'judge', 'spot_incorrect_sentence': 'judge',
    'tl_nl_translation': 'judge', 'synonym_antonym_match': 'judge',
}
LANG_CODE = {1: 'zh', 2: 'en', 3: 'ja'}


# ---------------------------------------------------------------------------
# Pure rules (mirrored in static/js/session/players/intro_drill.js)
# ---------------------------------------------------------------------------

def effective_gap(n_words: int) -> int:
    """Intervening items a correct answer needs before it counts."""
    return min(INTRO_MIN_GAP_ITEMS, max(0, int(n_words) - 1))


def recount(stage: int, attempts: List[dict], n_words: int, formats: List[str]) -> dict:
    """Re-apply the counting rules to one word's attempts.

    ``attempts``: [{pos, gap, format, correct, idk}] in the order served;
    ``pos`` is the item's position in the whole block and ``gap`` the spacing
    required when it was served (it shrinks as the block's other words finish;
    clamped to 0..INTRO_MIN_GAP_ITEMS and to what ``n_words`` allows). Attempts
    past the stage cap are ignored. Returns {target, counted, passed,
    cold_correct, items}.
    """
    target = INTRO_TARGETS[stage]
    cap = INTRO_ITEM_CAPS[stage]
    max_gap = effective_gap(n_words)
    distinct = len({f for f in formats if f in KNOWN_FORMATS}) >= 2
    counted, last_pos, last_fmt, cold_correct, items = 0, None, None, None, 0
    for a in sorted(attempts, key=lambda x: int(x.get('pos', 0)))[:cap]:
        pos = int(a.get('pos', 0))
        ok = bool(a.get('correct')) and not a.get('idk')
        fmt = a.get('format')
        try:
            gap = min(max(int(a.get('gap')), 0), max_gap)
        except (TypeError, ValueError):
            gap = max_gap
        if items == 0 and stage >= 2:
            cold_correct = ok
            if not ok:
                target += INTRO_COLD_MISS_BUMP
        spaced = last_pos is None or pos - last_pos - 1 >= gap
        if ok and spaced and (not distinct or fmt != last_fmt):
            counted += 1
            last_fmt = fmt
        last_pos = pos
        items += 1
        if counted >= target:
            break
    return {'target': target, 'counted': counted, 'passed': counted >= target,
            'cold_correct': cold_correct, 'items': items}


def advance(row: dict, stage: int, passed: bool, today: date, entry: dict) -> dict:
    """The ladder-row update after one finished intro session."""
    history = (list(row.get('intro_history') or []) + [entry])[-INTRO_HISTORY_KEEP:]
    upd: Dict[str, Any] = {'intro_history': history,
                           'updated_at': datetime.now(timezone.utc).isoformat()}
    if not passed:
        upd['intro_due_date'] = (today + timedelta(days=1)).isoformat()
        return upd
    if stage < 4:
        upd['intro_stage'] = stage + 1
        upd['intro_due_date'] = (today + timedelta(days=INTRO_GAP_DAYS[stage + 1])).isoformat()
        return upd
    # Graduate: intro replaces ring 1, so the word starts on ring 2.
    fc = dict(row.get('family_confidence') or {})
    fc['form_recognition'] = max(float(fc.get('form_recognition') or 0.10), INTRO_GRADUATE_FORM_RECOGNITION)
    dates = sorted({e['date'] for e in history if e.get('stage') and e.get('passed') and e.get('date')})[-2:]
    fsd = dict(row.get('family_success_dates') or {})
    fsd['form_recognition'] = dates
    upd.update({
        'word_state': 'active', 'current_ring': 2, 'intro_stage': None, 'intro_due_date': None,
        'family_confidence': fc, 'family_success_dates': fsd,
        'review_due_at': datetime.now(timezone.utc).isoformat(),
    })
    return upd


def new_intro_fields(today_iso: str, history: Optional[list] = None, stage: int = 1,
                     due_iso: Optional[str] = None) -> dict:
    """Columns of a ladder row that starts in the intro drill."""
    return {'word_state': 'intro', 'current_ring': 1, 'review_due_at': None,
            'intro_stage': stage, 'intro_due_date': due_iso or today_iso,
            'intro_history': history or []}


def bypasses_quota(row: dict) -> bool:
    """A stage-1 row that is not a brand-new word (restart, overload, or
    already started) is served regardless of today's new-word quota."""
    for e in row.get('intro_history') or []:
        if e.get('event') in ('restart', 'overload') or e.get('stage'):
            return True
    return False


def prestudy_queued(row: dict) -> bool:
    return any(e.get('event') == 'queued' and e.get('source') == 'prestudy'
               for e in row.get('intro_history') or [])


def extra_minutes_per_day(n_words: int) -> int:
    per_word = sum(INTRO_STAGE_ITEMS_EST.values()) * INTRO_ITEM_SECONDS / 60.0
    return int(math.ceil(n_words * per_word / 4)) if n_words > 0 else 0


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _today(db, user_id: str, language_id: int) -> date:
    from services.day_boundary import plan_today
    return plan_today(db, user_id, language_id)


def _language_sense_ids(db, sense_ids: List[int], language_id: int) -> set:
    if not sense_ids:
        return set()
    rows = db.table('dim_word_senses').select('id, dim_vocabulary!inner(language_id)') \
        .in_('id', sense_ids).eq('dim_vocabulary.language_id', language_id).execute().data or []
    return {int(r['id']) for r in rows}


def due_rows(db, user_id: str, language_id: int, today: date) -> List[dict]:
    """Intro rows of this language due today (stage-1 quota not applied)."""
    rows = db.table('user_word_ladder').select(
        'sense_id, intro_stage, intro_due_date, intro_history, created_at'
    ).eq('user_id', user_id).eq('word_state', 'intro') \
        .lte('intro_due_date', today.isoformat()).limit(500).execute().data or []
    keep = _language_sense_ids(db, [int(r['sense_id']) for r in rows], language_id)
    return [r for r in rows if int(r['sense_id']) in keep]


def intro_sense_ids(db, user_id: str) -> set:
    """Every sense this learner has in the intro drill (any language)."""
    rows = db.table('user_word_ladder').select('sense_id').eq('user_id', user_id) \
        .eq('word_state', 'intro').limit(2000).execute().data or []
    return {int(r['sense_id']) for r in rows}


def due_review_count(db, user_id: str, language_id: int, today: Optional[date] = None) -> int:
    """Due intro words that are reviews (sessions 2-4, restarts, overloads).

    ``today`` is the learner's local date; pass it when already resolved (it
    saves the plan read when called off the request thread)."""
    rows = due_rows(db, user_id, language_id, today or _today(db, user_id, language_id))
    return sum(1 for r in rows if (r.get('intro_stage') or 1) >= 2 or bypasses_quota(r))


def select_block_rows(rows: List[dict], mode: str, stage1_slots: int) -> List[dict]:
    """Which due intro rows this practice request serves.

    Stage 2-4 rows (and stage-1 rows that bypass the quota) are reviews: every
    mode serves them. Brand-new stage-1 rows are new words: only acquisition /
    auto serves them, at most ``stage1_slots`` of them, prestudy-queued first,
    then oldest admission.
    """
    reviews = [r for r in rows if (r.get('intro_stage') or 1) >= 2 or bypasses_quota(r)]
    reviews.sort(key=lambda r: (-(r.get('intro_stage') or 1), r.get('intro_due_date') or '', r.get('created_at') or ''))
    fresh: List[dict] = []
    if mode in ('acquisition', 'auto') and stage1_slots > 0:
        fresh = [r for r in rows if (r.get('intro_stage') or 1) == 1 and not bypasses_quota(r)]
        fresh.sort(key=lambda r: (not prestudy_queued(r), r.get('created_at') or ''))
        fresh = fresh[:stage1_slots]
    return (reviews + fresh)[:INTRO_BLOCK_MAX_WORDS]


def _gloss(sense: dict, gloss_lang: Optional[int]) -> tuple[str, str]:
    gl = sense.get('glosses') or {}
    pref = gl.get(str(gloss_lang)) if gloss_lang else None
    native = next(iter(gl.values()), {}) if gl else {}
    d = (pref or {}).get('def') or native.get('def') or ''
    # example sentence in the target language: the native-definition row's one
    ex = native.get('ex') or (pref or {}).get('ex') or ''
    return d, ex


def _reading(sense: dict, lang: str) -> Optional[dict]:
    r = sense.get('reading')
    if not r or lang == 'en':
        return None
    import re
    m = re.match(r'^(.*?)\s*\((.*)\)\s*$', r)
    shown = (m.group(1) if m else r).strip()
    if lang == 'ja':
        # legacy rows stored UniDic's loanword tag: すぴーど-speed
        shown = re.sub(r'-[A-Za-z][A-Za-z-]*(?:（[^）]*）|\([^)]*\))?', '', shown).strip()
    numbered = m.group(2).strip() if m else None
    if lang == 'zh' and not numbered:
        return None
    return {'shown': shown, 'numbered': numbered}


def _blank(sentence: str, lemma: str) -> Optional[str]:
    if sentence and lemma and lemma in sentence:
        return sentence.replace(lemma, '＿＿＿', 1)
    return None


def word_formats(stage: int, lang: str, has_reading: bool, has_sentence: bool,
                 ex_groups: set) -> List[str]:
    """Formats for one word: cold recall first (stages 2-4), then the stage's
    preference order with unbuildable formats dropped; never fewer than two."""
    base = STAGE_FORMATS[('cjk' if lang in ('ja', 'zh') else 'en', 1)] if stage == 1 else STAGE_FORMATS[(None, stage)]
    cold = COLD_FORMAT.get(lang, 'recall_typed')
    if cold == 'read_typed' and not has_reading:
        cold = 'recall_typed'
    out: List[str] = [cold] if stage >= 2 else []
    for f in base:
        if f in ('read_typed', 'read_typed2') and not has_reading:
            continue
        if f in ('cloze_mc', 'cloze_typed') and not has_sentence:
            continue
        if f == 'ex_use' and 'use' not in ex_groups:
            continue
        if f == 'ex_judge' and 'judge' not in ex_groups:
            continue
        if f not in out:
            out.append(f)
    if stage == 1 and not has_reading and 'recall_typed' not in out:
        out.append('recall_typed')
    for f in ('def_mc', 'rev_mc', 'recall_typed'):
        if len(out) >= 2:
            break
        if f not in out:
            out.append(f)
    return out


def _distractor_pool(db, language_id: int, gloss_lang: Optional[int], near_ids: List[int],
                     exclude: set, n: int = 24) -> List[dict]:
    """Other senses of the same language for multiple-choice options."""
    if not near_ids:
        return []
    try:
        q = db.table('dim_word_senses').select(
            'id, definition, definition_language_id, dim_vocabulary!inner(lemma, language_id, part_of_speech)'
        ).eq('dim_vocabulary.language_id', language_id).gte('id', max(0, min(near_ids) - 400))
        if gloss_lang:
            q = q.eq('definition_language_id', gloss_lang)
        rows = q.order('id').limit(n * 3).execute().data or []
    except Exception as e:
        logger.warning('intro distractor pool failed: %s', e)
        return []
    out, seen = [], set()
    for r in rows:
        lemma = (r.get('dim_vocabulary') or {}).get('lemma')
        if r['id'] in exclude or not lemma or not r.get('definition') or lemma in seen:
            continue
        seen.add(lemma)
        out.append({'lemma': lemma, 'def': r['definition'],
                    'pos': (r.get('dim_vocabulary') or {}).get('part_of_speech')})
    random.Random(sum(near_ids)).shuffle(out)
    return out[:n]


def build_block(db, user_id: str, language_id: int, rows: List[dict]) -> Optional[dict]:
    """The ``intro_drill`` payload for the selected rows (None when empty)."""
    if not rows:
        return None
    from services import prestudy
    from services.vocabulary.gloss_lookup import get_user_definition_language_id
    lang = LANG_CODE.get(int(language_id), 'en')
    gloss_lang = get_user_definition_language_id(db, user_id)
    sids = [int(r['sense_id']) for r in rows]
    senses = prestudy._load_senses(db, sids, gloss_lang)
    ex_rows = db.table('exercises').select('id, word_sense_id, exercise_type, content, ladder_level') \
        .eq('is_active', True).in_('word_sense_id', sids).in_('exercise_type', list(EX_GROUPS)) \
        .limit(400).execute().data or []
    by_sense: Dict[int, Dict[str, list]] = {}
    for e in ex_rows:
        by_sense.setdefault(int(e['word_sense_id']), {}).setdefault(EX_GROUPS[e['exercise_type']], []).append({
            'exercise_id': e['id'], 'sense_id': int(e['word_sense_id']),
            'exercise_type': e['exercise_type'], 'content': e.get('content') or {},
            'ladder_level': e.get('ladder_level'),
        })
    words = []
    for r in rows:
        sid = int(r['sense_id'])
        s = senses.get(str(sid))
        if not s or not s.get('lemma'):
            continue
        stage = int(r.get('intro_stage') or 1)
        d, ex = _gloss(s, gloss_lang)
        if not d:
            continue
        rd = _reading(s, lang)
        sent = _blank(ex, s['lemma'])
        groups = by_sense.get(sid, {})
        formats = word_formats(stage, lang, rd is not None, sent is not None, set(groups))
        words.append({
            'sense_id': sid, 'stage': stage, 'target': INTRO_TARGETS[stage], 'pos': s.get('pos'),
            'cap': INTRO_ITEM_CAPS[stage], 'cold': stage >= 2,
            'lemma': s['lemma'], 'reading': rd, 'gloss': d,
            'sentence': sent, 'example': ex or None, 'formats': formats,
            'exercises': {g: v[:2] for g, v in groups.items()},
        })
    if not words:
        return None
    pool = _distractor_pool(db, language_id, gloss_lang, sids, set(sids))
    items = sum(INTRO_STAGE_ITEMS_EST[w['stage']] for w in words)
    return {
        'id': f"intro-{_today(db, user_id, language_id).isoformat()}",
        'language_id': int(language_id), 'lang': lang,
        'words': words, 'pool': pool,
        'est_minutes': max(1, int(math.ceil(items * INTRO_ITEM_SECONDS / 60.0))),
    }


def stage1_slots(service, user_id: str, language_id: int) -> int:
    """Today's room for brand-new intro words: effective quota - started today."""
    state = service.new_word_state(user_id, language_id)
    if not state:
        return 0
    return max(0, int(state['effective']) - int(state['started_today']))


def block_for_session(service, user_id: str, language_id: int, mode: str) -> Optional[dict]:
    db = service.db
    today = _today(db, user_id, language_id)
    rows = due_rows(db, user_id, language_id, today)
    if not rows:
        return None
    slots = stage1_slots(service, user_id, language_id) if mode in ('acquisition', 'auto') else 0
    return build_block(db, user_id, language_id, select_block_rows(rows, mode, slots))


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------

def _invalidate_new_word_state(user_id) -> None:
    """A ladder write changes today's new-word counts; see request_cache."""
    from services.request_cache import invalidate
    invalidate('new_word_state', str(user_id))


def complete_word(db, user_id: str, result: dict) -> dict:
    """Record one finished word of an intro block and advance its stage.

    ``result``: {sense_id, stage, n_words, formats, attempts:[{pos, format,
    correct, idk, ms, exercise_id?, given?}]}. Rejected (ok False) when the
    sense is not this user's intro row at that stage (also makes replays no-ops).
    """
    sid = int(result['sense_id'])
    stage = int(result['stage'])
    rows = db.table('user_word_ladder').select(
        'sense_id, word_state, intro_stage, intro_history, family_confidence, family_success_dates'
    ).eq('user_id', user_id).eq('sense_id', sid).limit(1).execute().data or []
    if not rows or rows[0].get('word_state') != 'intro' or int(rows[0].get('intro_stage') or 0) != stage:
        return {'sense_id': sid, 'ok': False, 'reason': 'not_due'}
    row = rows[0]
    lang_rows = db.table('dim_word_senses').select('dim_vocabulary(language_id)').eq('id', sid).limit(1).execute().data or []
    language_id = int(((lang_rows[0] if lang_rows else {}).get('dim_vocabulary') or {}).get('language_id') or 0)

    attempts = sorted([a for a in (result.get('attempts') or [])[:MAX_ATTEMPTS_PER_WORD]
                       if isinstance(a, dict) and a.get('format') in KNOWN_FORMATS],
                      key=lambda a: int(a.get('pos') or 0))
    formats = [f for f in (result.get('formats') or []) if f in KNOWN_FORMATS]
    rc = recount(stage, attempts, int(result.get('n_words') or 1), formats)
    today = _today(db, user_id, language_id) if language_id else date.today()

    # exercise_attempts rows (source intro); a bogus exercise id is dropped, not trusted
    ex_ids = {str(a['exercise_id']) for a in attempts if a.get('exercise_id')}
    valid_ex = set()
    if ex_ids:
        valid_ex = {str(r['id']) for r in db.table('exercises').select('id')
                    .in_('id', list(ex_ids)).eq('word_sense_id', sid).execute().data or []}
    now = datetime.now(timezone.utc).isoformat()
    seen_fmt: set = set()
    ins, total_ms = [], 0
    for a in attempts[:rc['items']]:
        ms = a.get('ms')
        ms = int(ms) if isinstance(ms, (int, float)) and not isinstance(ms, bool) and 0 < ms < 600000 else None
        total_ms += min(ms or 0, 300000)
        ins.append({
            'user_id': user_id, 'sense_id': sid, 'source': 'intro',
            'exercise_id': str(a['exercise_id']) if str(a.get('exercise_id')) in valid_ex else None,
            'exercise_type': 'intro_' + a['format'],
            'is_correct': bool(a.get('correct')) and not a.get('idk'),
            'is_first_attempt': a['format'] not in seen_fmt,
            'time_taken_ms': ms,
            'user_response': {'given': str(a.get('given') or '')[:200], 'idk': bool(a.get('idk')), 'stage': stage},
            'created_at': now,
        })
        seen_fmt.add(a['format'])

    entry = {'stage': stage, 'date': today.isoformat(), 'at': now, 'target': rc['target'],
             'counted': rc['counted'], 'items': rc['items'], 'cold_correct': rc['cold_correct'],
             'passed': rc['passed'], 'formats': sorted({a['format'] for a in attempts})}
    upd = advance(row, stage, rc['passed'], today, entry)
    # Attempt rows + ladder row in one transaction; false = the row is no
    # longer at this stage (a replay or a concurrent post): record nothing.
    committed = db.rpc('intro_commit_word', {
        'p_user_id': user_id, 'p_sense_id': sid, 'p_stage': stage,
        'p_attempts': [{k: v for k, v in r.items() if k not in ('user_id', 'sense_id', 'source')} for r in ins],
        'p_update': {k: v for k, v in upd.items() if k != 'updated_at'},
    }).execute().data
    if committed is not True:
        return {'sense_id': sid, 'ok': False, 'reason': 'not_due'}

    # one knowledge-evidence point per word per session
    if stage == 1:
        ok_n = sum(1 for a in ins if a['is_correct'])
        evidence = ok_n > len(ins) - ok_n
    else:
        evidence = bool(rc['cold_correct'])
    if ins and language_id:
        try:
            from services.vocabulary.knowledge_service import VocabularyKnowledgeService
            VocabularyKnowledgeService(db).update_from_word_tests_batch(
                user_id=user_id, language_id=language_id,
                results=[{'sense_id': sid, 'is_correct': evidence}], side_effects=False)
        except Exception as e:
            logger.warning('intro evidence failed for sense %s: %s', sid, e)

    if total_ms and language_id:
        from services.study_time import credit_study_time
        credit_study_time(db, user_id, language_id, 'practice', total_ms / 1000.0,
                          'intro_drill', f'{sid}:{stage}:{now}')
    if stage == 1 and rc['passed'] and language_id:
        _request_generation_if_short(db, sid, language_id)
    return {'sense_id': sid, 'ok': True, **rc, 'graduated': upd.get('current_ring') == 2,
            'next_stage': upd.get('intro_stage'), 'next_due': upd.get('intro_due_date')}


def _request_generation_if_short(db, sid: int, language_id: int) -> None:
    try:
        n = len(db.table('exercises').select('id').eq('word_sense_id', sid)
                .eq('is_active', True).limit(3).execute().data or [])
        if n < 3:
            from services.vocabulary_ladder import queue_drain
            queue_drain.enqueue(db, sid, int(language_id), 'intro', detail={'source': 'intro'})
    except Exception as e:
        logger.info('intro generation request skipped for %s: %s', sid, e)


def restart_if_demoted(db, user_id: str, sense_id: int, language_id: Optional[int], result: dict) -> bool:
    """A word demoted from ring 2 that came through the intro restarts at
    session 1 (decided 2026-11-09). Legacy words keep the ring-1 path."""
    if not ENABLED or not isinstance(result, dict) or not result.get('demoted'):
        return False
    if int(result.get('current_ring') or 0) != 1:
        return False
    rows = db.table('user_word_ladder').select('intro_history, family_success_dates') \
        .eq('user_id', user_id).eq('sense_id', sense_id).limit(1).execute().data or []
    if not rows or not rows[0].get('intro_history'):
        return False
    today = _today(db, user_id, language_id) if language_id else date.today()
    fsd = dict(rows[0].get('family_success_dates') or {})
    fsd['form_recognition'] = []
    history = (list(rows[0]['intro_history']) + [{'event': 'restart', 'date': today.isoformat(),
                                                  'at': datetime.now(timezone.utc).isoformat()}])[-INTRO_HISTORY_KEEP:]
    upd = new_intro_fields(today.isoformat(), history, 1, (today + timedelta(days=1)).isoformat())
    upd['family_success_dates'] = fsd
    db.table('user_word_ladder').update(upd).eq('user_id', user_id).eq('sense_id', sense_id).execute()
    _invalidate_new_word_state(user_id)
    return True


# ---------------------------------------------------------------------------
# Test prestudy admission (TASK-918)
# ---------------------------------------------------------------------------

def admit_prestudy(service, user_id: str, language_id: int, drilled: List[int], met: set) -> dict:
    """Admit the words a prestudy prime drilled into the intro drill.

    Words already on the ladder are left alone. Within today's remaining
    new-word room: a word that met session 1's criterion in the prime starts
    at session 2 (due tomorrow); others at session 1 today. Words over the
    room are queued (session 1, served on later days) and returned as
    ``overflow`` so the page can offer to add them all now.
    """
    out = {'admitted': [], 'queued': [], 'overflow': None}
    if not ENABLED or not drilled:
        return out
    db = service.db
    drilled = list(dict.fromkeys(int(s) for s in drilled))
    existing = {int(r['sense_id']) for r in db.table('user_word_ladder').select('sense_id')
                .eq('user_id', user_id).in_('sense_id', drilled).execute().data or []}
    fresh = sorted([s for s in drilled if s not in existing], key=lambda s: s not in met)
    if not fresh:
        return out
    room = stage1_slots(service, user_id, language_id)
    today = _today(db, user_id, language_id)
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for i, sid in enumerate(fresh):
        is_met = sid in met
        if i < room and is_met:
            fields = new_intro_fields(today.isoformat(), [{
                'stage': 1, 'source': 'prestudy', 'date': today.isoformat(), 'at': now,
                'target': INTRO_TARGETS[1], 'counted': INTRO_TARGETS[1], 'passed': True}],
                2, (today + timedelta(days=INTRO_GAP_DAYS[2])).isoformat())
            out['admitted'].append(sid)
        elif i < room:
            fields = new_intro_fields(today.isoformat(), [{'event': 'queued', 'source': 'prestudy', 'at': now}])
            out['admitted'].append(sid)
        else:
            fields = new_intro_fields(today.isoformat(), [{'event': 'queued', 'source': 'prestudy',
                                                           'met': is_met, 'at': now}])
            out['queued'].append(sid)
        rows.append({'user_id': user_id, 'sense_id': sid, **_fresh_ladder_columns(), **fields})
    db.table('user_word_ladder').insert(rows).execute()
    _invalidate_new_word_state(user_id)
    if out['queued']:
        out['overflow'] = {'fits': len(out['admitted']), 'over': len(out['queued']),
                           'sense_ids': out['queued'],
                           'extra_minutes_per_day': extra_minutes_per_day(len(out['queued']))}
    return out


def overload(db, user_id: str, language_id: int, sense_ids: List[int]) -> List[int]:
    """'Add them all now': queued prestudy words start today, past the quota.

    Only rows still at session 1 with a prestudy 'queued' entry from the last
    6 hours qualify. A word that met session 1 in today's prime starts at
    session 2 instead.
    """
    if not sense_ids:
        return []
    rows = db.table('user_word_ladder').select('sense_id, word_state, intro_stage, intro_history') \
        .eq('user_id', user_id).in_('sense_id', [int(s) for s in sense_ids][:200]).execute().data or []
    today = _today(db, user_id, language_id)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
    now = datetime.now(timezone.utc).isoformat()
    done = []
    for r in rows:
        if r.get('word_state') != 'intro' or int(r.get('intro_stage') or 0) != 1 or bypasses_quota(r):
            continue
        q = next((e for e in r.get('intro_history') or []
                  if e.get('event') == 'queued' and e.get('source') == 'prestudy'), None)
        try:
            fresh = q and datetime.fromisoformat(q['at']) >= cutoff
        except (KeyError, TypeError, ValueError):
            fresh = False
        if not fresh:
            continue
        hist = list(r['intro_history'])
        if q.get('met'):
            hist.append({'stage': 1, 'source': 'prestudy', 'date': today.isoformat(), 'at': now,
                         'target': INTRO_TARGETS[1], 'counted': INTRO_TARGETS[1], 'passed': True})
            upd = {'intro_history': hist, 'intro_stage': 2,
                   'intro_due_date': (today + timedelta(days=INTRO_GAP_DAYS[2])).isoformat()}
        else:
            hist.append({'event': 'overload', 'at': now})
            upd = {'intro_history': hist, 'intro_due_date': today.isoformat()}
        db.table('user_word_ladder').update(upd).eq('user_id', user_id).eq('sense_id', r['sense_id']).execute()
        _invalidate_new_word_state(user_id)
        done.append(int(r['sense_id']))
    return done


def _fresh_ladder_columns() -> dict:
    return {
        'family_confidence': {k: 0.10 for k in (
            'form_recognition', 'meaning_recall', 'form_production', 'collocation',
            'semantic_discrimination', 'contextual_use')},
        'gates_passed': {'gate_a': False, 'gate_b': False},
    }
