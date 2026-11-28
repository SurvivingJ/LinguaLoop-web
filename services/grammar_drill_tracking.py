"""Grammar-drill progress tracking (TASK-1259, ADR-066).

Daily summaries per learner and topic plus one current-state row per topic, so
that improvement over time can be read back and progress follows the learner
across devices. No per-answer and no per-item rows: database space is the
constraint (owner stop line 480 MB).

The tables and the function live in migrations/grammar_drill_tracking.sql.
Until that file is applied every call raises ``TrackingUnavailable``; the routes
answer 503 and the page carries on with its local progress.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from services.day_boundary import review_today
from services.drill_service import ZH_LANGUAGE_ID
from services.pagination import fetch_all

logger = logging.getLogger(__name__)

LANGUAGE_ID = ZH_LANGUAGE_ID
MANIFEST_PATH = (Path(__file__).resolve().parent.parent
                 / 'static' / 'data' / 'grammar' / 'zh' / 'manifest.json')

RPC_NAME = 'record_grammar_drill_round'
DAILY_TABLE = 'grammar_drill_daily'
STATE_TABLE = 'grammar_drill_state'

MODES = ('round', 'mixed', 'endless', 'sync')
MAX_TOPICS = 10
MAX_ANSWERS = 500            # per topic per call
MAX_MS = 30000               # cap on one recall time
MAX_STAGE = 4
MAX_STATE_BYTES = 1500       # JSON text; the table's CHECK allows 4096 stored bytes
MAX_SEQ = 10_000_000
DEFAULT_DAYS = 180
MAX_DAYS = 365
#: A queued round may be sent late; it still counts for the day it was played
#: when that is at most this long ago.
MAX_BACKDATE = timedelta(days=7)
CLOCK_SKEW = timedelta(minutes=5)

_RESULTS_RE = re.compile(r'^(-?[1-9]\d{0,5}(,-?[1-9]\d{0,5}){0,29})?$')
_STATE_KEYS = frozenset({'u', 'r', 'q', 'e', 'l'})
_TOPIC_KEYS = frozenset({'topic', 'answers', 'correct', 'timed', 'ms_sum', 'stage',
                         'instant', 'sub_misses', 'state'})

_MISSING_RECHECK_SECONDS = 600
_missing_until = 0.0
_manifest_cache: Optional[tuple[float, dict[str, frozenset[str]]]] = None


class ValidationError(ValueError):
    """The request body is not acceptable; the message is safe for the client."""


class TrackingUnavailable(RuntimeError):
    """The tracking tables or function are not in the database (yet)."""


# --------------------------------------------------------------------------- manifest
def topic_subs() -> dict[str, frozenset[str]]:
    """topic slug -> its sub-point keys, from the built manifest (cached; the
    file is re-read when its modification time changes)."""
    global _manifest_cache
    mtime = MANIFEST_PATH.stat().st_mtime
    if _manifest_cache is None or _manifest_cache[0] != mtime:
        with MANIFEST_PATH.open(encoding='utf-8') as fh:
            manifest = json.load(fh)
        topics = {
            str(t['slug']): frozenset(str(s['key']) for s in t.get('subs') or [])
            for t in manifest.get('topics') or []
        }
        _manifest_cache = (mtime, topics)
    return _manifest_cache[1]


# ------------------------------------------------------------------------- validation
def _int(value: Any, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{name} must be an integer")
    if value < low or value > high:
        raise ValidationError(f"{name} must be between {low} and {high}")
    return value


def _state(value: Any, now: datetime) -> Optional[dict]:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) - _STATE_KEYS:
        raise ValidationError("state has unknown fields")
    if set(value) != _STATE_KEYS:
        raise ValidationError("state must have u, r, q, e and l")
    results = value['r']
    if (not isinstance(results, list) or len(results) != MAX_STAGE
            or not all(isinstance(r, str) and _RESULTS_RE.match(r) for r in results)):
        raise ValidationError("state.r must be four result strings")
    endless = value['e']
    if not isinstance(endless, list) or len(endless) != 3:
        raise ValidationError("state.e must be three integers")
    clean = {
        'u': _int(value['u'], 'state.u', 1, MAX_STAGE),
        'r': list(results),
        'q': _int(value['q'], 'state.q', 0, MAX_SEQ),
        'e': [_int(n, 'state.e', 0, MAX_SEQ) for n in endless],
        'l': _int(value['l'], 'state.l', 0, int((now + timedelta(days=1)).timestamp())),
    }
    if clean['e'][1] > clean['e'][0]:
        raise ValidationError("state.e correct exceeds answers")
    if len(json.dumps(clean, separators=(',', ':'))) > MAX_STATE_BYTES:
        raise ValidationError("state is too large")
    return clean


def _topic(entry: Any, mode: str, subs_by_topic: dict[str, frozenset[str]],
           now: datetime) -> dict:
    if not isinstance(entry, dict) or set(entry) - _TOPIC_KEYS:
        raise ValidationError("topic entry has unknown fields")
    slug = entry.get('topic')
    if not isinstance(slug, str) or slug not in subs_by_topic:
        raise ValidationError("unknown topic")
    low = 0 if mode == 'sync' else 1
    high = 0 if mode == 'sync' else MAX_ANSWERS
    answers = _int(entry.get('answers', 0), 'answers', low, high)
    correct = _int(entry.get('correct', 0), 'correct', 0, answers)
    timed = _int(entry.get('timed', 0), 'timed', 0, answers)
    ms_sum = _int(entry.get('ms_sum', 0), 'ms_sum', 0, timed * MAX_MS)
    stage = _int(entry.get('stage', 1), 'stage', 1, MAX_STAGE)
    instant = entry.get('instant', False)
    if not isinstance(instant, bool):
        raise ValidationError("instant must be true or false")
    if instant and stage < MAX_STAGE:
        raise ValidationError("instant needs the last stage")

    misses = entry.get('sub_misses') or {}
    if not isinstance(misses, dict):
        raise ValidationError("sub_misses must be an object")
    known = subs_by_topic[slug]
    clean_misses = {}
    for key, count in misses.items():
        if key not in known:
            raise ValidationError("unknown sub-point")
        clean_misses[key] = _int(count, 'sub_misses', 1, answers)
    if sum(clean_misses.values()) > answers - correct:
        raise ValidationError("sub_misses exceed the missed answers")

    state = _state(entry.get('state'), now)
    if mode == 'sync' and state is None:
        raise ValidationError("a sync entry needs a state")
    return {
        'topic': slug, 'answers': answers, 'correct': correct, 'timed': timed,
        'ms_sum': ms_sum, 'stage': stage, 'instant': instant,
        'sub_misses': clean_misses, 'state': state,
    }


def validate_round(body: dict, now: Optional[datetime] = None) -> dict:
    """The cleaned round: {language_id, round_key, mode, practice_day, topics}.

    Raises ``ValidationError``. Nothing from the body is passed on unchecked.
    """
    now = now or datetime.now(timezone.utc)
    if body.get('language_id') != LANGUAGE_ID or isinstance(body.get('language_id'), bool):
        raise ValidationError("Grammar drills are Chinese-only")
    raw_key = body.get('round_key')
    try:
        round_key = str(uuid.UUID(raw_key)) if isinstance(raw_key, str) else ''
    except ValueError:
        round_key = ''
    if not round_key:
        raise ValidationError("round_key must be a UUID")
    mode = body.get('mode')
    if mode not in MODES:
        raise ValidationError("mode must be round, mixed, endless or sync")

    topics = body.get('topics')
    if not isinstance(topics, list) or not 1 <= len(topics) <= MAX_TOPICS:
        raise ValidationError(f"topics must list 1 to {MAX_TOPICS} topics")
    subs_by_topic = topic_subs()
    clean = [_topic(entry, mode, subs_by_topic, now) for entry in topics]
    if len({t['topic'] for t in clean}) != len(clean):
        raise ValidationError("a topic may appear once")

    return {
        'language_id': LANGUAGE_ID,
        'round_key': round_key,
        'mode': mode,
        'practice_day': practice_day(body.get('played_at'), now),
        'topics': clean,
    }


def practice_day(played_at: Any, now: Optional[datetime] = None) -> date:
    """The review day (services.day_boundary, Australia/Sydney) a round counts
    for: the day it was played when the client says so and that is plausible
    (not in the future, at most MAX_BACKDATE ago), else today."""
    now = now or datetime.now(timezone.utc)
    if isinstance(played_at, int) and not isinstance(played_at, bool):
        try:
            played = datetime.fromtimestamp(played_at, timezone.utc)
        except (OverflowError, OSError, ValueError):
            played = None
        if played and now - MAX_BACKDATE <= played <= now + CLOCK_SKEW:
            return review_today(min(played, now))
    return review_today(now)


# ---------------------------------------------------------------------------- storage
def _is_missing_object(exc: BaseException) -> bool:
    text = str(exc)
    code = getattr(exc, 'code', None)
    return (code in ('PGRST202', 'PGRST205', '42P01', '42883')
            or any(marker in text for marker in (
                'PGRST202', 'PGRST205', '42P01', '42883',
                'Could not find the function', 'Could not find the table')))


def _check_available() -> None:
    if _missing_until > time.monotonic():
        raise TrackingUnavailable("grammar drill tracking is not deployed")


def _unavailable(exc: BaseException) -> TrackingUnavailable:
    global _missing_until
    _missing_until = time.monotonic() + _MISSING_RECHECK_SECONDS
    logger.warning(
        "Grammar drill tracking objects are missing (apply "
        "migrations/grammar_drill_tracking.sql); not retrying for %ss: %s",
        _MISSING_RECHECK_SECONDS, exc)
    return TrackingUnavailable("grammar drill tracking is not deployed")


def reset() -> None:
    """Forget the remembered-missing state and the manifest cache (tests)."""
    global _missing_until, _manifest_cache
    _missing_until = 0.0
    _manifest_cache = None


def record_round(db, user_id: str, round_: dict) -> dict:
    """Write one validated round. Returns {recorded, replayed}."""
    _check_available()
    params = {
        'p_user_id': user_id,
        'p_language_id': round_['language_id'],
        'p_round_key': round_['round_key'],
        'p_practice_day': round_['practice_day'].isoformat(),
        'p_topics': round_['topics'],
    }
    try:
        data = db.rpc(RPC_NAME, params).execute().data
    except Exception as exc:
        if _is_missing_object(exc):
            raise _unavailable(exc) from exc
        raise
    if isinstance(data, list) and len(data) == 1:
        data = data[0]
    if not isinstance(data, dict) or not data.get('success'):
        raise RuntimeError(f"{RPC_NAME} failed: {data!r}")
    return {'recorded': int(data.get('recorded') or 0),
            'replayed': int(data.get('replayed') or 0)}


def load_progress(db, user_id: str, days: int = DEFAULT_DAYS,
                  now: Optional[datetime] = None) -> dict:
    """{today, states: {topic: state}, daily: [...]} for one learner."""
    _check_available()
    days = max(1, min(int(days or DEFAULT_DAYS), MAX_DAYS))
    today = review_today(now)
    since = (today - timedelta(days=days - 1)).isoformat()
    try:
        state_rows = (
            db.table(STATE_TABLE).select('topic,state')
            .eq('user_id', user_id).eq('language_id', LANGUAGE_ID)
            .execute().data or []
        )
        daily_rows = fetch_all(lambda: (
            db.table(DAILY_TABLE)
            .select('topic,practice_day,answers,correct,timed,ms_sum,stage,instant,sub_misses')
            .eq('user_id', user_id).eq('language_id', LANGUAGE_ID)
            .gte('practice_day', since)
            .order('practice_day').order('topic')
        ))
    except Exception as exc:
        if _is_missing_object(exc):
            raise _unavailable(exc) from exc
        raise
    return {
        'today': today.isoformat(),
        'days': days,
        'states': {r['topic']: r.get('state') or {} for r in state_rows},
        'daily': [{
            'topic': r['topic'],
            'day': str(r['practice_day'])[:10],
            'answers': r.get('answers') or 0,
            'correct': r.get('correct') or 0,
            'timed': r.get('timed') or 0,
            'ms_sum': r.get('ms_sum') or 0,
            'stage': r.get('stage') or 1,
            'instant': bool(r.get('instant')),
            'sub_misses': r.get('sub_misses') or {},
        } for r in daily_rows],
    }
