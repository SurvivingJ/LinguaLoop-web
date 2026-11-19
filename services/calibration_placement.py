"""Vocabulary placement service (vocab-placement tech §1, §8, §10–§14; TASK-1080).

A placement is a vocabulary-check session with ``mode = 'placement'``. Item building and grading run in SQL
(``calibration_placement_*``, TASK-1077); allocation, stopping and statistics run here in pure Python
(``services.placement_design`` and ``services.vocabulary.knowledge_estimate``).

One round trip per answer: ``calibration_placement_answer`` grades the answer and, when the word is complete
and Python passed ``p_next_band``, builds the next meaning item in the same call. ``p_next_band`` is computed
from the tallies the PREVIOUS answer call returned, held in a small process-local cache. With several gunicorn
workers a request can land where the cache is cold: the call is then made with ``p_next_band = NULL`` (no new
word is built), the next band is computed from the tallies that come back, and the next item is built with
``calibration_placement_next_item`` — one extra round trip, only on a cache miss.
"""
from __future__ import annotations

import json
import logging
import random
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from config import Config
from services import placement_design as pd
from services.supabase_factory import get_supabase_admin
from services.vocabulary import knowledge_estimate as ke

logger = logging.getLogger(__name__)

MODE = 'placement'
SUPPORTED_LANGUAGE_IDS = (1, 2, 3)
RESULT_MAX_BYTES = 2048
DAILY_STARTS_PER_LANGUAGE = 3
FRAME_CHANGE_SHARE = 0.01
_CACHE_TTL_S = 3 * 3600
_CACHE_MAX = 2000


class PlacementError(Exception):
    """A client-visible failure: ``status`` 400 (bad request), 404 (not found / disabled) or 429."""

    def __init__(self, message: str, status: int = 400, code: Optional[str] = None):
        super().__init__(message)
        self.status = status
        self.code = code


# ---------------------------------------------------------------- feature flag

def enabled_languages() -> set[int]:
    raw = getattr(Config, 'PLACEMENT_ENABLED_LANGS', '') or ''
    out = set()
    for part in str(raw).replace(';', ',').split(','):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def require_enabled(language_id: int) -> None:
    if int(language_id) not in enabled_languages():
        raise PlacementError('Vocabulary placement is not available for this language', 404, 'NOT_FOUND')


# ---------------------------------------------------------------- tallies cache (process-local)

_cache: dict[str, tuple[float, dict]] = {}
_cache_lock = threading.Lock()


def _cache_get(session_id: str) -> Optional[dict]:
    with _cache_lock:
        hit = _cache.get(str(session_id))
        if not hit:
            return None
        ts, tallies = hit
        if time.monotonic() - ts > _CACHE_TTL_S:
            _cache.pop(str(session_id), None)
            return None
        return tallies


def _cache_put(session_id: str, tallies: Optional[dict]) -> None:
    if not tallies:
        return
    with _cache_lock:
        if len(_cache) >= _CACHE_MAX:
            oldest = sorted(_cache.items(), key=lambda kv: kv[1][0])[: _CACHE_MAX // 4]
            for k, _ in oldest:
                _cache.pop(k, None)
        _cache[str(session_id)] = (time.monotonic(), tallies)


def _cache_drop(session_id: str) -> None:
    with _cache_lock:
        _cache.pop(str(session_id), None)


# ---------------------------------------------------------------- randomness (seeded per session, stored nowhere)

def _session_rng(session_id: str, salt: str = '') -> random.Random:
    return random.Random(f'placement:{session_id}:{salt}')


def _warmup_order(session_id: str) -> list[int]:
    return pd.warmup_order(_session_rng(session_id, 'warmup'))


def _draws(session_id: str, response_id: int) -> dict:
    rng = _session_rng(session_id, f'answer:{response_id}')
    return {'u_probe': rng.random(), 'u_seed': rng.random()}


# ---------------------------------------------------------------- database access (thin; faked in tests)

def _rpc(name: str, params: dict):
    db = get_supabase_admin()
    try:
        resp = db.rpc(name, params).execute()
    except Exception as exc:                                    # PostgREST raises on SQL errors
        msg = f"{getattr(exc, 'code', '')} {exc}"
        logger.warning('%s failed: %s', name, msg[:300])
        if 'P0002' in msg:
            raise PlacementError('Placement session not found', 404, 'NOT_FOUND') from exc
        if '22023' in msg:
            raise PlacementError(_clean_sql_message(msg), 400, 'BAD_REQUEST') from exc
        raise
    return resp.data


def _clean_sql_message(msg: str) -> str:
    try:
        payload = json.loads(msg) if msg.strip().startswith('{') else None
        if isinstance(payload, dict) and payload.get('message'):
            return str(payload['message'])
    except ValueError:
        pass
    return 'Invalid placement request'


def frame_for(language_id: int, definition_language_id: int) -> list[int]:
    data = _rpc('knowledge_frame_bands', {}) or {}
    frame = data.get(f'{int(language_id)}:{int(definition_language_id)}')
    if not frame or len(frame) != pd.N_BANDS:
        raise PlacementError('No word pool for this language pair', 404, 'NOT_FOUND')
    return [int(x) for x in frame]


def _session_row(user_id: str, session_id: str) -> Optional[dict]:
    db = get_supabase_admin()
    rows = (db.table('calibration_sessions').select('*').eq('id', session_id).eq('user_id', user_id)
            .eq('mode', MODE).limit(1).execute().data or [])
    return rows[0] if rows else None


def _open_session(user_id: str, language_id: int, definition_language_id: int, since: datetime) -> Optional[dict]:
    db = get_supabase_admin()
    rows = (db.table('calibration_sessions').select('*').eq('user_id', user_id).eq('mode', MODE)
            .eq('word_language_id', int(language_id)).eq('definition_language_id', int(definition_language_id))
            .is_('ended_at', 'null').gte('started_at', since.isoformat())
            .order('started_at', desc=True).limit(1).execute().data or [])
    return rows[0] if rows else None


def _starts_today(user_id: str, language_id: int, now: datetime) -> int:
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    db = get_supabase_admin()
    rows = (db.table('calibration_sessions').select('id').eq('user_id', user_id).eq('mode', MODE)
            .eq('word_language_id', int(language_id)).gte('started_at', midnight.isoformat())
            .execute().data or [])
    return len(rows)


def _insert_session(user_id: str, language_id: int, definition_language_id: int) -> dict:
    db = get_supabase_admin()
    rows = db.table('calibration_sessions').insert({
        'user_id': user_id, 'word_language_id': int(language_id),
        'definition_language_id': int(definition_language_id), 'mode': MODE,
    }).execute().data or []
    if not rows:
        raise RuntimeError('could not open a placement session')
    return rows[0]


def _save_result(session_id: str, result: Optional[dict]) -> None:
    db = get_supabase_admin()
    db.table('calibration_sessions').update({'result': result}).eq('id', session_id).execute()


def _pending_item_row(session_id: str) -> Optional[dict]:
    db = get_supabase_admin()
    rows = (db.table('calibration_responses').select('id').eq('session_id', session_id)
            .is_('answered_at', 'null').order('id', desc=True).limit(1).execute().data or [])
    return rows[0] if rows else None


def _previous_result(user_id: str, language_id: int, definition_language_id: int, before_session: str) -> Optional[dict]:
    db = get_supabase_admin()
    rows = (db.table('calibration_sessions').select('id,ended_at,result').eq('user_id', user_id).eq('mode', MODE)
            .eq('word_language_id', int(language_id)).eq('definition_language_id', int(definition_language_id))
            .neq('id', before_session).not_.is_('result', 'null')
            .order('ended_at', desc=True).limit(1).execute().data or [])
    return rows[0] if rows else None


_KANA_ONLY = re.compile(r'^[ぁ-ゟァ-ヿー・]+$')


def reading_exempt(language_id: int, lemma: Optional[str]) -> bool:
    """en words and ja kana-only lemmas have no reading item (vocab-placement tech §2)."""
    if int(language_id) == pd.LANG_EN:
        return True
    if int(language_id) == pd.LANG_JA:
        return bool(lemma) and bool(_KANA_ONLY.match(lemma))
    return False


def _session_by_id(session_id: str) -> Optional[dict]:
    db = get_supabase_admin()
    rows = db.table('calibration_sessions').select('*').eq('id', session_id).limit(1).execute().data or []
    return rows[0] if rows else None


def _latest_result_row(user_id: str, language_id: int) -> Optional[dict]:
    db = get_supabase_admin()
    rows = (db.table('calibration_sessions').select('id,result,ended_at').eq('user_id', user_id).eq('mode', MODE)
            .eq('word_language_id', int(language_id)).not_.is_('result', 'null')
            .order('ended_at', desc=True).limit(1).execute().data or [])
    return rows[0] if rows else None


def _response_rows(session_id: str) -> list[dict]:
    db = get_supabase_admin()
    return (db.table('calibration_responses')
            .select('id,anchor_vocab_id,anchor_sense_id,item_kind,probe_kind,is_correct,chosen_position,'
                    'chosen_sense_id,answered_at,pair_response_id,option_roles,zipf_band')
            .eq('session_id', session_id).is_('probe_kind', 'null').not_.is_('answered_at', 'null')
            .order('id').execute().data or [])


def _word_outcomes(session_id: str, language_id: int) -> list[dict]:
    """Per-word outcomes of a session's scored items: meaning rows paired with their reading rows.

    A word whose meaning was right on a reading-ready lemma but whose reading item was never answered (the
    session ended in between; close deletes the pending row) is an incomplete pair and is left out."""
    rows = _response_rows(session_id)
    reading_of = {r['pair_response_id']: r for r in rows if r.get('item_kind') == 'reading' and r.get('pair_response_id')}
    lemmas = _lemmas(sorted({int(r['anchor_vocab_id']) for r in rows if r.get('item_kind') == 'meaning'}))
    words = []
    for r in rows:
        if r.get('item_kind') != 'meaning':
            continue
        if r.get('is_correct'):
            meaning = 'right'
        elif r.get('chosen_position') is None and r.get('chosen_sense_id') is None:
            meaning = 'idk'
        else:
            meaning = 'wrong'
        rd = reading_of.get(r['id'])
        reading = None
        if rd is not None:
            if rd.get('chosen_position') is None and rd.get('chosen_sense_id') is None:
                reading = 'idk'
            elif rd.get('option_roles'):
                reading = rd['option_roles'][int(rd['chosen_position'])]
            else:
                reading = 'right' if rd.get('is_correct') else 'wrong'
        lemma = lemmas.get(int(r['anchor_vocab_id']))
        ready = rd is not None or not reading_exempt(language_id, lemma)
        if meaning == 'right' and ready and rd is None:
            continue                                            # incomplete pair
        words.append(dict(response_id=r['id'], vocab_id=r['anchor_vocab_id'], sense_id=r['anchor_sense_id'],
                          band=r.get('zipf_band'), lemma=lemma, meaning=meaning, reading=reading,
                          reading_ready=ready))
    return words


def _lemmas(vocab_ids: list[int]) -> dict[int, str]:
    if not vocab_ids:
        return {}
    db = get_supabase_admin()
    rows = db.table('dim_vocabulary').select('id,lemma').in_('id', list(vocab_ids)).execute().data or []
    return {int(r['id']): r['lemma'] for r in rows}


# ---------------------------------------------------------------- evidence hook (TASK-1081)

def _default_evidence_writer(user_id: str, session: dict, words: list[dict]) -> Optional[dict]:
    from services import placement_evidence
    return placement_evidence.write(user_id, session, words)


evidence_writer: Callable[[str, dict, list[dict]], Optional[dict]] = _default_evidence_writer


# ---------------------------------------------------------------- tallies helpers

def _tallies_from_inputs(inputs: dict, language_id: int) -> dict:
    """Rebuild session tallies (m [n,c,w], mr, scored) from knowledge_calibration_inputs(p_session_id)."""
    bands = inputs.get('bands') or [[0, 0, 0]] * pd.N_BANDS
    m = [[int(n), int(c), int(n) - int(s) - int(c)] for n, s, c in bands]
    zh = pd.is_zh(language_id)
    pairs = inputs.get('pairs') or ([[0, 0, 0, 0]] if zh else [[0, 0, 0]]) * pd.N_BANDS
    gap = inputs.get('gap') or []
    reading_answered = 0
    for b in range(pd.N_BANDS):
        if not pd.has_reading(language_id) or not gap:
            continue
        g = gap[b]
        if zh:                                  # pc + kt + f + idk
            reading_answered += int(pairs[b][1]) + int(g[4]) + int(g[1]) + int(g[2])
        else:                                   # pc + reading wrong + reading idk (exempt words have no reading item)
            reading_answered += int(pairs[b][1]) + int(g[1]) + int(g[2])
    scored = sum(r[0] for r in m) + reading_answered
    return dict(m=m, mr=[list(map(int, p)) for p in pairs], scored=scored, active_ms=int(inputs.get('active_ms') or 0))


def _session_inputs(user_id: str, session: dict) -> dict:
    return _rpc('knowledge_calibration_inputs', {
        'p_user_id': user_id, 'p_language_id': int(session['word_language_id']),
        'p_definition_language_id': int(session['definition_language_id']), 'p_session_id': session['id'],
    }) or {}


def _progress(tallies: dict, language_id: int) -> dict:
    return {'scored': int(tallies.get('scored') or 0), 'cap': pd.cap_for(language_id),
            'minutes_left': pd.minutes_left(tallies, language_id)}


def _empty_tallies(language_id: int) -> dict:
    zh = pd.is_zh(language_id)
    return dict(m=[[0, 0, 0] for _ in range(pd.N_BANDS)],
                mr=[[0, 0, 0, 0] if zh else [0, 0, 0] for _ in range(pd.N_BANDS)],
                scored=0, active_ms=0, warmup_done=False)


# ---------------------------------------------------------------- public API

def start(user_id: str, language_id: int, definition_language_id: int, *, now: Optional[datetime] = None) -> dict:
    language_id, definition_language_id = int(language_id), int(definition_language_id)
    if language_id not in SUPPORTED_LANGUAGE_IDS or definition_language_id not in SUPPORTED_LANGUAGE_IDS:
        raise PlacementError('word_language_id and definition_language_id must be 1, 2 or 3')
    require_enabled(language_id)
    now = now or datetime.now(timezone.utc)
    close_stale_for(user_id)
    hours = pd.CONFIG['resume_hours']
    open_s = _open_session(user_id, language_id, definition_language_id, now - timedelta(hours=hours))
    if open_s:
        item = _resume_item(user_id, open_s)
        tallies = _cache_get(open_s['id']) or _tallies_from_inputs(_session_inputs(user_id, open_s), language_id)
        return {'session_id': str(open_s['id']), 'item': item, 'resumed': True,
                'progress': _progress(tallies, language_id), 'can_stop': pd.can_end_now(tallies)}
    if _starts_today(user_id, language_id, now) >= DAILY_STARTS_PER_LANGUAGE:
        raise PlacementError('You can start at most 3 placements per language per day', 429, 'RATE_LIMITED')
    frame_for(language_id, definition_language_id)               # 404 early for a pair with no pool
    session = _insert_session(user_id, language_id, definition_language_id)
    order = _warmup_order(session['id'])
    item = _rpc('calibration_placement_next_item', {
        'p_user_id': user_id, 'p_session_id': session['id'], 'p_band': order[0],
        'p_exclude_days': pd.CONFIG['exclude_days']})
    if not item or item.get('exhausted'):
        raise PlacementError('No words are ready for a placement in this language yet', 404, 'NOT_FOUND')
    tallies = _empty_tallies(language_id)
    _cache_put(session['id'], tallies)
    return {'session_id': str(session['id']), 'item': item, 'resumed': False,
            'progress': _progress(tallies, language_id), 'can_stop': False}


def _resume_item(user_id: str, session: dict) -> Optional[dict]:
    """Re-send the pending item: ``calibration_placement_next_item`` returns the session's pending unanswered
    item when one exists (it never builds a second pending row); otherwise it builds one in the next band."""
    tallies = _cache_get(session['id']) or _tallies_from_inputs(_session_inputs(user_id, session),
                                                               int(session['word_language_id']))
    frame = frame_for(int(session['word_language_id']), int(session['definition_language_id']))
    band = pd.next_band(tallies, frame, int(session['word_language_id']), _session_rng(session['id'], 'resume'),
                        order=_warmup_order(session['id'])) or pd.N_BANDS
    return _rpc('calibration_placement_next_item', {
        'p_user_id': user_id, 'p_session_id': session['id'], 'p_band': band,
        'p_exclude_days': pd.CONFIG['exclude_days']})


def answer(user_id: str, session_id: str, response_id: int, position: Optional[int],
           latency_ms: Optional[int] = None) -> dict:
    session = _session_row(user_id, session_id)
    if not session:
        raise PlacementError('Placement session not found', 404, 'NOT_FOUND')
    if session.get('ended_at'):
        raise PlacementError('This placement has ended', 400, 'BAD_REQUEST')
    lang = int(session['word_language_id'])
    require_enabled(lang)
    frame = frame_for(lang, int(session['definition_language_id']))
    prev = _cache_get(session_id)
    next_band = None
    if prev is not None and pd.may_start_new_word(prev, lang):
        next_band = pd.next_band(prev, frame, lang, _session_rng(session_id, f'band:{response_id}'),
                                 order=_warmup_order(session_id))
    out = _rpc('calibration_placement_answer', {
        'p_user_id': user_id, 'p_session_id': session_id, 'p_response_id': int(response_id),
        'p_position': position, 'p_latency_ms': latency_ms, 'p_next_band': next_band,
        'p_draws': _draws(session_id, int(response_id))}) or {}
    tallies = out.get('tallies') or {}
    _cache_put(session_id, tallies)
    reveal = out.get('reveal')
    next_item = out.get('next_item')
    exhausted = bool(out.get('exhausted'))
    result = None
    done = False
    if reveal is not None:                                      # the word is complete
        reason = pd.should_stop(tallies, frame, lang)
        if reason is None and next_item is None:
            if exhausted:
                reason = 'exhausted'
            elif pd.may_start_new_word(tallies, lang):
                band = pd.next_band(tallies, frame, lang, _session_rng(session_id, f'band2:{response_id}'),
                                    order=_warmup_order(session_id))
                next_item = _rpc('calibration_placement_next_item', {
                    'p_user_id': user_id, 'p_session_id': session_id, 'p_band': band,
                    'p_exclude_days': pd.CONFIG['exclude_days']}) if band else None
                if not next_item or next_item.get('exhausted'):
                    next_item, reason = None, 'exhausted'
            else:
                reason = 'cap' if int(tallies.get('scored') or 0) >= pd.cap_for(lang) else 'time'
        if reason is not None:
            result = finish(user_id, session, reason, tallies=tallies)
            next_item, done = None, True
    body = {'answer': out.get('answer'), 'reveal': reveal, 'next_item': next_item, 'done': done,
            'result': result, 'can_stop': (not done) and pd.can_end_now(tallies),
            'needed': pd.needed_for_result(tallies), 'progress': _progress(tallies, lang)}
    if result:
        body['word_lists'] = _lists_for(session_id, lang)
    return body


def end(user_id: str, session_id: str) -> dict:
    session = _session_row(user_id, session_id)
    if not session:
        raise PlacementError('Placement session not found', 404, 'NOT_FOUND')
    if session.get('ended_at'):
        return {'result': session.get('result')}
    lang = int(session['word_language_id'])
    tallies = _cache_get(session_id) or _tallies_from_inputs(_session_inputs(user_id, session), lang)
    if not pd.can_end_now(tallies):
        return {'not_enough': True, 'needed': pd.needed_for_result(tallies)}
    res = finish(user_id, session, 'learner', tallies=tallies)
    return {'result': res, 'word_lists': _lists_for(session_id, lang) if res else None}


def result(user_id: str, session_id: str) -> dict:
    session = _session_row(user_id, session_id)
    if not session:
        raise PlacementError('Placement session not found', 404, 'NOT_FOUND')
    out = {'result': session.get('result')}
    if session.get('result'):
        out['word_lists'] = _lists_for(session_id, int(session['word_language_id']))
    return out


def latest(user_id: str, language_id: int) -> dict:
    """Latest frozen result for the language; an unseen one (e.g. an abandoned session) is marked seen."""
    close_stale_for(user_id)
    row = _latest_result_row(user_id, language_id)
    if not row:
        return {'result': None, 'unseen': False}
    res = dict(row['result'])
    unseen = not res.get('seen')
    if unseen:
        res['seen'] = True
        _save_result(row['id'], res)
    return {'result': res, 'unseen': unseen, 'session_id': str(row['id']),
            'word_lists': _lists_for(row['id'], int(language_id))}


def close_stale_for(user_id: Optional[str]) -> list[str]:
    """Close open placements idle for 24 h as ``abandoned`` and finish each (result if eligible, evidence)."""
    ids = _rpc('calibration_placement_close_stale', {
        'p_user_id': user_id, 'p_older_than': f"{pd.CONFIG['resume_hours']} hours"}) or []
    done = []
    for sid in ids:
        row = _session_by_id(sid)
        if not row:
            continue
        try:
            finish(row['user_id'], row, 'abandoned', closed=True)
            done.append(str(sid))
        except Exception:                                       # one bad session never blocks the others
            logger.exception('placement finish failed for abandoned session %s', str(sid)[:8])
    return done


# ---------------------------------------------------------------- finish and the frozen result (§8)

def _lists_for(session_id: str, language_id: int) -> dict:
    """``word_lists`` for the result page: group → [{vocab_id, lemma}] (the page also accepts plain lemmas)."""
    return _word_lists(_word_outcomes(session_id, language_id), language_id)


def _word_lists(words: list[dict], language_id: int) -> dict:
    groups = pd.word_groups(words, language_id)
    lemma_of = {int(w['vocab_id']): w.get('lemma') for w in words if w.get('vocab_id') is not None}
    return {g: [{'vocab_id': v, 'lemma': lemma_of.get(int(v))} for v in ids]
            for g, ids in groups['vocab_ids'].items()}


def _stat(e: Optional[dict]) -> Optional[dict]:
    if not e or e.get('T') is None:
        return None
    return {'T': round(float(e['T']), 1), 'SD': round(float(e['SD']), 1)}


def finish(user_id: str, session: dict, reason: str, *, tallies: Optional[dict] = None, closed: bool = False) -> Optional[dict]:
    """Close the session, freeze its result (when eligible) and write the evidence. Idempotent on a closed
    session that already has a result."""
    if reason not in pd.STOP_REASONS:
        raise ValueError(f'unknown stop reason {reason!r}')
    sid = session['id']
    lang, dlang = int(session['word_language_id']), int(session['definition_language_id'])
    if not closed:
        final = _rpc('calibration_placement_close', {'p_user_id': user_id, 'p_session_id': sid, 'p_reason': reason}) or {}
        tallies = final.get('tallies') or final or tallies
    _cache_drop(sid)
    inputs_this = _session_inputs(user_id, session)
    if not tallies or 'm' not in tallies:
        tallies = _tallies_from_inputs(inputs_this, lang)
    frame = frame_for(lang, dlang)
    words = _word_outcomes(sid, lang)
    res = None
    if pd.eligible(tallies, reason):
        res = build_result(user_id, session, reason, tallies, inputs_this, frame, words)
        _save_result(sid, res)
    try:
        evidence_writer(user_id, session, words)
    except Exception:
        logger.exception('placement evidence write failed for session %s', str(sid)[:8])
    return res


def build_result(user_id: str, session: dict, reason: str, tallies: dict, inputs_this: dict,
                 frame: list[int], words: list[dict]) -> dict:
    sid = session['id']
    lang, dlang = int(session['word_language_id']), int(session['definition_language_id'])
    this = pd.estimates(inputs_this, frame, lang, min_per_band=ke.PLACEMENT_MIN_PER_BAND)
    combined_inputs = _rpc('knowledge_calibration_inputs', {
        'p_user_id': user_id, 'p_language_id': lang, 'p_definition_language_id': dlang}) or {}
    combined_min = ke.PLACEMENT_MIN_PER_BAND if reason in pd.COMPLETE_REASONS else ke.MIN_PER_BAND
    combined = None
    # Only same-instrument answers combine (PSY M5). For an abandoned FIRST placement the inputs, read
    # before its result is frozen, fall back to the legacy instrument: then combined = this (not shown).
    if combined_inputs.get('bands') and combined_inputs.get('instrument') == 'meaning_bare_v1':
        comb = pd.estimates(combined_inputs, frame, lang, min_per_band=combined_min)
        if comb['display'] != this['display']:
            combined = comb['display']
    groups = pd.word_groups(words, lang)['counts']
    n_meaning = sum(int(r[0]) for r in inputs_this.get('bands') or [])
    n_idk = sum(int(r[1]) for r in inputs_this.get('bands') or [])
    reading_items = max(0, int(tallies.get('scored') or 0) - n_meaning)
    prev_block = None
    prev = _previous_result(user_id, lang, dlang, sid)
    head_now = pd.headline(this, lang)
    if prev and prev.get('result'):
        pres = prev['result']
        if abs(int(pres.get('frame_n') or 0) - sum(frame)) <= FRAME_CHANGE_SHARE * sum(frame):
            pkey = 'mr' if pd.has_reading(lang) else 'm'
            prev_stat = (pres.get('stat') or {}).get(pkey)
            verdict = pd.retake_verdict(prev_stat, _stat(head_now))
            ended = prev.get('ended_at')
            prev_block = {'session_id': str(prev['id']),
                          'ended_at': ended.isoformat() if hasattr(ended, 'isoformat') else ended,
                          pkey: (pres.get('this') or {}).get(pkey), 'verdict': verdict}
    res = {
        'version': pd.CONFIG['version'], 'word_language_id': lang, 'definition_language_id': dlang,
        'instrument': 'meaning_bare_v1', 'stop_reason': reason,
        'ended_early': reason in ('learner', 'abandoned'),
        'fast': pd.is_fast(tallies.get('median_latency_ms'), n_meaning + reading_items),
        'skip_share': round(n_idk / n_meaning, 2) if n_meaning else None,
        'items': {'scored': int(tallies.get('scored') or 0), 'meaning': n_meaning, 'reading': reading_items,
                  'probes': int(tallies.get('probes') or 0)},
        'active_seconds': int(int(tallies.get('active_ms') or 0) / 1000),
        'words': groups, 'frame_n': sum(frame),
        'this': this['display'], 'combined': combined, 'previous': prev_block,
        'stat': {'m': _stat(this['m']), 'mr': _stat(this['mr'])}, 'seen': False,
    }
    size = len(json.dumps(res, separators=(',', ':')).encode())
    if size > RESULT_MAX_BYTES:                                  # never expected; keep the essentials
        logger.warning('placement result %s is %d bytes; dropping combined/previous', str(sid)[:8], size)
        res['combined'] = None
        res['previous'] = None
    return res


def run_nightly_close() -> dict:
    """Nightly job (web/scheduler.py, 04:30 UTC): close every user's placements idle for 24 h as
    ``abandoned`` and finish them. Skipped while the placement is enabled for no language, and when
    the placement SQL is not deployed yet."""
    if not enabled_languages():
        return {'skipped': True, 'reason': 'PLACEMENT_ENABLED_LANGS is empty'}
    try:
        closed = close_stale_for(None)
    except Exception as exc:                                    # e.g. the RPC does not exist yet
        logger.warning('placement nightly close failed: %s', str(exc)[:200])
        return {'skipped': True, 'reason': 'close_stale failed'}
    return {'closed': len(closed)}
