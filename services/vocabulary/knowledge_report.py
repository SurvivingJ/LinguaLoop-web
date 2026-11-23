"""Knowledge Report ("My vocabulary"): summary service, entitlement seam and demand logging.

wiki/features/knowledge-report.tech.md. The statistics live in ``knowledge_estimate`` (pure, ADR-051);
this module does the I/O around them:

* the entitlement seam and the shared 402 gate (ADR-055, §6.4, TASK-1038);
* ``knowledge_pro_intent`` demand logging (§6.4);
* the per-process cache of ``knowledge_frame_bands()`` (§9);
* ``summary()``: snapshot anchors → ``knowledge_report_summary`` (one round trip) → frame →
  estimator and rules → the §6.3 payload (TASK-1039);
* ``prestudy_suggestion()``: next-step rule 2 (§2.13, TASK-1041).

Every RPC receives ``p_user_id`` from the caller (the route passes ``g.current_user_id``), never a
request value. Logs name users by the first 8 characters of their id.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Sequence

from config import Config
from services import request_cache
from services.optional_rpc import call_bundle
from services.vocabulary import knowledge_estimate as ke

logger = logging.getLogger(__name__)

ENTITLEMENT_KEY = 'bkt_report_detail'
PRO_MESSAGE = 'The word-by-word view is part of Pro.'
SUMMARY_RPC = 'knowledge_report_summary'
FRAME_RPC = 'knowledge_frame_bands'
SNAPSHOT_TABLE = 'user_knowledge_snapshots'

FRAME_TTL_S = 3600
SNAPSHOT_LOOKBACK_DAYS = 97          # covers the 90-day anchor window [today − 97, today − 90]
SNAPSHOT_COLUMNS = ('snapshot_date, method_version, rated_known_words, cal_definition_language_id, '
                    'cal_bands, frame_bands, cal_first_answer_at, cal_last_answer_at')
GROWTH_WINDOWS = (30, 90)
FEW_TRACKED_WORDS = 50               # E2
STALE_DAYS = 30                      # E3

# Skills card order (§2.11 display names); unknown families follow, by name.
FAMILY_ORDER = ('form_recognition', 'meaning_recall', 'form_production', 'semantic_discrimination',
                'collocation', 'fluency')

# /words request parameters that make a request a "filter" action (§6.2, §6.4).
WORDS_FILTER_PARAMS = ('states', 'checked_several', 'missed_recent', 'idle_days', 'bands',
                       'in_word_list', 'list', 'level')
_BOOLEAN_FILTER_PARAMS = ('checked_several', 'missed_recent', 'in_word_list')


def short_id(user_id: Any) -> str:
    return str(user_id or '')[:8]


# ---------------------------------------------------------------- entitlement seam (ADR-055)

def _billing_entitlements():
    """Billing TASK-980's module, or None until it exists."""
    try:
        from services.billing import entitlements  # type: ignore[import-not-found]
    except ImportError:
        return None
    return entitlements


_stub_warned = False


def _stub_tier_level(db, user_id: str) -> int:
    """1 when the learner's tier has ``can_access_analytics`` (every live tier except free), else 0.
    A failed read is level 0: the stub can never deny, so 0 only changes the preview note."""
    try:
        rows = (db.table('users').select('dim_subscription_tiers(can_access_analytics)')
                .eq('id', user_id).limit(1).execute().data) or []
    except Exception as exc:
        logger.warning('knowledge_tier_read_failed user=%s (%s)', short_id(user_id), exc)
        return 0
    tier = (rows[0].get('dim_subscription_tiers') if rows else None) or {}
    if isinstance(tier, list):                      # PostgREST embeds can arrive as a one-row list
        tier = tier[0] if tier else {}
    return 1 if tier.get('can_access_analytics') else 0


def report_detail_level(db, user_id: str) -> tuple[int, bool]:
    """``(level, enforced)`` for ``bkt_report_detail`` (tech §6.4).

    With billing's module (TASK-980): its limit and ``Config.ENTITLEMENTS_ENFORCED``. Until then the
    stub reads the tier once per request (``request_cache.memo``) and always reports
    ``enforced = False``, so it can never deny."""
    global _stub_warned
    entitlements = _billing_entitlements()
    if entitlements is not None:
        level = int(entitlements.limit(ENTITLEMENT_KEY) or 0)
        return (1 if level >= 1 else 0), bool(Config.ENTITLEMENTS_ENFORCED)
    level = request_cache.memo(('kr_tier', user_id), lambda: _stub_tier_level(db, user_id))
    if Config.ENTITLEMENTS_ENFORCED and not _stub_warned:
        _stub_warned = True
        logger.warning('knowledge_entitlement_stub_enforce_ignored: ENTITLEMENTS_ENFORCED is on but '
                       'billing entitlements are not installed; the report stub never denies')
    return level, False


def detail_payload(level: int, enforced: bool) -> dict:
    return {'level': int(level), 'enforced': bool(enforced), 'preview': level == 0 and not enforced}


def entitlement_gate(db, user_id: str, endpoint: str):
    """Gate for a Pro route: None to serve, or the 402 response (tech §6.4).

    level 1 → serve; level 0, not enforced → serve and log ``entitlement_shadow_deny``;
    level 0, enforced → 402 ``PLAN_REQUIRED``. Needs a Flask app context (it builds a response)."""
    level, enforced = report_detail_level(db, user_id)
    if level >= 1:
        return None
    if not enforced:
        logger.info('entitlement_shadow_deny key=%s route=%s user=%s',
                    ENTITLEMENT_KEY, endpoint, short_id(user_id))
        return None
    from utils.responses import payment_required
    return payment_required('PLAN_REQUIRED', PRO_MESSAGE, entitlement=ENTITLEMENT_KEY,
                            required=1, current=int(level))


# ---------------------------------------------------------------- demand log (§6.4, P14)

def _param(args: Mapping, name: str) -> str:
    value = args.get(name) if args is not None else None
    return '' if value is None else str(value).strip()


def pro_intent_action(endpoint: str, args: Mapping) -> Optional[str]:
    """The explicit Pro action a request represents, or None (never for the page's automatic first
    ``/words`` call). A ``/words`` request with a cursor is "load more" whatever its filters (they
    were counted when first applied); else search, filter, then a non-default sort."""
    if endpoint == 'knowledge.words':
        if _param(args, 'cursor'):
            return 'load_more'
        if _param(args, 'q'):
            return 'search'
        for name in WORDS_FILTER_PARAMS:
            value = _param(args, name)
            if value and not (name in _BOOLEAN_FILTER_PARAMS and value == '0'):
                return 'filter'
        sort = _param(args, 'sort')
        if sort and sort != 'useful':
            return 'sort'
        return None
    if endpoint == 'knowledge.word_detail':
        return 'word_sheet'
    if endpoint == 'knowledge.list_words':
        return 'lists_tab'
    if endpoint == 'knowledge.export':
        if _param(args, 'cursor'):
            return None                                   # first chunk only
        fmt = _param(args, 'format')
        return {'csv': 'export_csv', 'anki': 'export_anki'}.get(fmt)
    return None


def log_pro_intent(action: Optional[str], user_id: str) -> None:
    if action:
        logger.info('knowledge_pro_intent action=%s user=%s', action, short_id(user_id))


# ---------------------------------------------------------------- frame cache (§9)

_frame_lock = threading.Lock()
_frame_cache: dict = {'at': None, 'value': None}
_clock = time.monotonic


def reset_frame_cache() -> None:
    with _frame_lock:
        _frame_cache['at'] = None
        _frame_cache['value'] = None


def _clean_frame(raw: Mapping) -> dict[str, list[int]]:
    out = {}
    for key, bands in (raw or {}).items():
        if isinstance(bands, (list, tuple)) and len(bands) == ke.N_BANDS:
            out[str(key)] = [int(b or 0) for b in bands]
    return out


def frame_bands(db) -> Optional[dict[str, list[int]]]:
    """``knowledge_frame_bands()`` as ``{"<L>:<D>": [N_1..N_7]}``, cached per process for 3,600 s.
    None when the RPC is missing or fails (not cached, so the next request retries)."""
    now = _clock()
    with _frame_lock:
        at, value = _frame_cache['at'], _frame_cache['value']
        if value is not None and at is not None and now - at < FRAME_TTL_S:
            return value
    raw = call_bundle(db, FRAME_RPC, {})
    if raw is None:
        return None
    value = _clean_frame(raw)
    with _frame_lock:
        _frame_cache['at'] = now
        _frame_cache['value'] = value
    return value


def frame_for(frames: Mapping[str, Sequence[int]], language_id: int,
              definition_language_id: Optional[int]) -> Optional[list[int]]:
    """The frame of (L, D). Without a D (no check answers yet) the group sizes use (L, English),
    else the lowest D the pool has for L; None when the pool has nothing for L."""
    if definition_language_id is not None:
        bands = frames.get(f'{language_id}:{definition_language_id}')
        return list(bands) if bands is not None else None
    candidates = sorted((int(k.split(':')[1]), v) for k, v in frames.items()
                        if k.split(':')[0] == str(language_id))
    preferred = [v for d, v in candidates if d == 2]
    if preferred:
        return list(preferred[0])
    return list(candidates[0][1]) if candidates else None


# ---------------------------------------------------------------- small helpers

def _num(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _date(value: Any) -> Optional[date]:
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date() if value.tzinfo else value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _iso_date(value: Any) -> Optional[str]:
    d = _date(value)
    return d.isoformat() if d else None


def _bands(raw: Any) -> list[list[int]]:
    """``[[n, s, c] × 7]``; anything malformed counts as no answers."""
    if isinstance(raw, (list, tuple)) and len(raw) == ke.N_BANDS:
        rows = []
        for row in raw:
            if not isinstance(row, (list, tuple)) or len(row) < 3:
                return [[0, 0, 0] for _ in range(ke.N_BANDS)]
            rows.append([_num(row[0]), _num(row[1]), _num(row[2])])
        return rows
    return [[0, 0, 0] for _ in range(ke.N_BANDS)]


def _seven(raw: Any) -> list[int]:
    if isinstance(raw, (list, tuple)) and len(raw) == ke.N_BANDS:
        return [_num(x) for x in raw]
    return [0] * ke.N_BANDS


def _frame_usable(frame: Optional[Sequence[int]], bands: Sequence[Sequence[int]]) -> bool:
    """A frame band of size 0 with answers in it would divide by zero (stale pool vs answers)."""
    if not frame or len(frame) != ke.N_BANDS:
        return False
    return all(N > 0 or row[0] == 0 for N, row in zip(frame, bands))


def _first(cal: Mapping, *names: str) -> Any:
    """``knowledge_report_summary`` names the dates ``first_answer_at`` / ``last_answer_at``
    (report §6.1); placement's ``knowledge_calibration_inputs`` names them ``first_at`` /
    ``last_at`` (vocab-placement §14). Accept either."""
    for name in names:
        if cal.get(name) is not None:
            return cal.get(name)
    return None


# ---------------------------------------------------------------- snapshots (§2.10, ADR-053)

def _read_snapshots(db, user_id: str, language_id: int, today: date) -> list[dict]:
    cut = today - timedelta(days=SNAPSHOT_LOOKBACK_DAYS)
    rows = (db.table(SNAPSHOT_TABLE).select(SNAPSHOT_COLUMNS)
            .eq('user_id', user_id).eq('language_id', language_id)
            .gte('snapshot_date', cut.isoformat())
            .order('snapshot_date').limit(100).execute().data) or []
    dates = [d for d in (_date(r.get('snapshot_date')) for r in rows) if d]
    has_exact_anchor = all(
        any(today - timedelta(days=w + ke.ANCHOR_SLACK_DAYS) <= d <= today - timedelta(days=w)
            for d in dates)
        for w in GROWTH_WINDOWS)
    if not has_exact_anchor:
        # A window without a snapshot in [today − D − 7, today − D] falls back to the learner's
        # earliest snapshot ("since {date}"), which may be older than the rows read above.
        earliest = (db.table(SNAPSHOT_TABLE).select(SNAPSHOT_COLUMNS)
                    .eq('user_id', user_id).eq('language_id', language_id)
                    .order('snapshot_date').limit(1).execute().data) or []
        known = {str(r.get('snapshot_date'))[:10] for r in rows}
        rows = [r for r in earliest if str(r.get('snapshot_date'))[:10] not in known] + list(rows)
    return rows


def load_snapshots(db, user_id: str, language_id: int, today: date) -> list[dict]:
    """The snapshot rows growth needs, memoised per request. A missing table (foundation migration
    not applied yet) or a failed read is "no history": growth shows its first-trend date."""
    def load():
        try:
            return _read_snapshots(db, user_id, language_id, today)
        except Exception as exc:
            logger.info('knowledge snapshots unreadable user=%s lang=%s (%s)',
                        short_id(user_id), language_id, exc)
            return []
    return request_cache.memo(('kr_snapshots', user_id, int(language_id), today.isoformat()), load)


# ---------------------------------------------------------------- exam lists seam (TASK-1049)

def list_coverage(db, user_id: str, language_id: int, summary_rpc: Mapping) -> tuple[list, bool]:
    """``(lists, lists_unavailable)`` for the summary (tech §6.3).

    Until the word-list store exists (TASK-1049: ``services/vocabulary/word_lists.py`` and
    ``knowledge_list_buckets``) there is no list file for any language, which is state E4:
    ``([], False)``. TASK-1049 replaces this body; its contract is that a Storage or bucket failure
    returns ``([], True)`` and never raises."""
    return [], False


# ---------------------------------------------------------------- summary (§6.3)

def _estimate_block(est: dict, *, d_star: Optional[int], cal: Mapping, universe: Optional[int],
                    rated_known_in_frame: Optional[int]) -> dict:
    shown = bool(est.get('shown'))
    kind = est.get('kind') or 'none'
    hi_raw = est.get('hi')
    disagreement = bool(shown and rated_known_in_frame is not None and hi_raw is not None
                        and rated_known_in_frame > hi_raw)
    return {
        'shown': shown,
        'kind': kind,
        'lo': est.get('lo_disp') if kind == 'range' else None,
        'hi': est.get('hi_disp') if shown else None,
        'label': est.get('label') if shown else None,
        'rel': round(est['rel'], 3) if shown and est.get('rel') is not None else None,
        'universe_words': universe,
        'definition_language_id': d_star,
        'answers': _num(cal.get('answers')),
        'first_answer_at': _iso_date(_first(cal, 'first_answer_at', 'first_at')),
        'last_answer_at': _iso_date(_first(cal, 'last_answer_at', 'last_at')),
        'reason': est.get('reason'),
        'have': est.get('have'),
        'answers_needed': est.get('answers_needed'),
        'disagreement': disagreement,
        'rated_known_in_frame': rated_known_in_frame,
        'tick': est.get('tick') if shown else None,
    }


def _groups_block(bands: list, frame: Optional[list], headline_eligible: bool,
                  measured: Sequence[Mapping]) -> list[dict]:
    by_band: dict[int, Mapping] = {}
    for row in measured or []:
        by_band[_num(row.get('band'), -1)] = row

    def counts(members: Sequence[int]) -> tuple[int, int]:
        return (sum(_num((by_band.get(b) or {}).get('tracked_words')) for b in members),
                sum(_num((by_band.get(b) or {}).get('rated_known_words')) for b in members))

    out = []
    if frame:
        for g in ke.group_shares(bands, frame, headline_eligible=headline_eligible):
            tracked, rated = counts(g['bands'])
            out.append({'group': g['group'], 'bands': g['bands'], 'universe': g['universe'],
                        'answers': g['answers'], 'shown': g['shown'], 'share_lo': g['share_lo'],
                        'share_hi': g['share_hi'], 'tracked': tracked, 'rated_known': rated})
    else:
        for name, members in ke.GROUPS:
            tracked, rated = counts(members)
            out.append({'group': name, 'bands': list(members), 'universe': None, 'answers': 0,
                        'shown': False, 'share_lo': None, 'share_hi': None, 'tracked': tracked,
                        'rated_known': rated})
    tracked, rated = counts((0,))
    if tracked:
        out.append({'group': 'none', 'bands': [0], 'universe': None, 'answers': 0, 'shown': False,
                    'share_lo': None, 'share_hi': None, 'tracked': tracked, 'rated_known': rated})
    return out


def _skills_block(families: Sequence[Mapping]) -> dict:
    usable = [f for f in families or [] if f.get('family') and _num(f.get('n')) > 0]
    result = ke.family_summary(usable)
    order = {name: i for i, name in enumerate(FAMILY_ORDER)}
    rows = sorted(result['families'], key=lambda r: (order.get(r['family'], len(order)), r['family']))
    for r in rows:
        if r['lo'] is not None:
            r['lo'] = round(r['lo'], 3)
            r['hi'] = round(r['hi'], 3)
    return {'families': rows, 'sentence': result['sentence']}


def _growth_block(rpc: Mapping, snapshots: list, today: date, frame_now: Optional[list],
                  since_rows: Mapping[int, Mapping]) -> dict:
    """§2.10. ``since_rows``: ``{30|90: since entry}`` already filtered to comparable anchors."""
    activity = rpc.get('activity') or {}
    now = {'rated_known_words': _num(rpc.get('rated_known_words')),
           'idle60': _num(rpc.get('idle60_meanings'))}
    for days in GROWTH_WINDOWS:
        a = activity.get(f'd{days}') or {}
        now[f'd{days}'] = {'practised': _num(a.get('practised_meanings')),
                           'direct_checks': _num(a.get('direct_outcomes')),
                           'met_in_texts': _num(a.get('met_in_texts'))}
    since_bands = {days: _bands(row.get('bands')) for days, row in since_rows.items()}
    out = ke.growth(now, snapshots, today, frame_now or [0] * ke.N_BANDS, since_bands)
    for days in GROWTH_WINDOWS:
        entry = out[f'd{days}']
        if frame_now is None:
            entry['pool_changed'] = None                  # no frame today: nothing to compare
        change = entry.get('estimate_change')
        if change is None:
            continue
        anchor = ke.select_anchor(snapshots, today, days)['anchor'] or {}
        row = since_rows.get(days) or {}
        change['then'].update(first_answer_at=_iso_date(anchor.get('cal_first_answer_at')),
                              last_answer_at=_iso_date(anchor.get('cal_last_answer_at')))
        change['now'].update(first_answer_at=_iso_date(_first(row, 'first_answer_at', 'first_at')),
                             last_answer_at=_iso_date(_first(row, 'last_answer_at', 'last_at')))
    return out


def _since_requests(snapshots: list, today: date) -> dict[int, str]:
    """``{30|90: the anchor's cal_last_answer_at}``: the answers after it are disjoint from the
    anchor's own (§2.10, S6), so ``knowledge_report_summary`` counts them via ``p_cal_since``."""
    out = {}
    for days in GROWTH_WINDOWS:
        sel = ke.select_anchor(snapshots, today, days)
        anchor = sel['anchor']
        if anchor is None or sel['suppressed'] or not anchor.get('cal_last_answer_at') \
                or anchor.get('cal_definition_language_id') is None:
            continue
        out[days] = str(anchor['cal_last_answer_at'])
    return out


def _comparable_since(snapshots: list, today: date, since_by_days: Mapping[int, str],
                      since_list: list, since_payload: Sequence, d_star: Optional[int],
                      frame: Optional[list]) -> dict[int, Mapping]:
    """The ``since`` entries (one per ``p_cal_since`` element, in order) whose anchor used today's
    definition language D* (never pooled) and whose bands fit today's frame."""
    out: dict[int, Mapping] = {}
    if d_star is None or frame is None:
        return out
    for days, ts in since_by_days.items():
        idx = since_list.index(ts)
        if idx >= len(since_payload) or not isinstance(since_payload[idx], Mapping):
            continue
        anchor = ke.select_anchor(snapshots, today, days)['anchor'] or {}
        if _num(anchor.get('cal_definition_language_id'), -1) != d_star:
            continue
        then_bands = ke.snapshot_bands(anchor)
        row = since_payload[idx]
        if then_bands is None or not _frame_usable(frame, then_bands) \
                or not _frame_usable(frame, _bands(row.get('bands'))):
            continue
        out[days] = row
    return out


def summary(db, user_id: str, language_id: int, *, now: Optional[datetime] = None) -> Optional[dict]:
    """The §6.3 payload (without ``status``), or None when the summary RPC or the frame is not
    available (the route answers 503)."""
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(timezone.utc).date()

    snapshots = load_snapshots(db, user_id, language_id, today)
    since_by_days = _since_requests(snapshots, today)
    since_list: list[str] = []
    for days in GROWTH_WINDOWS:
        ts = since_by_days.get(days)
        if ts is not None and ts not in since_list:
            since_list.append(ts)

    rpc = call_bundle(db, SUMMARY_RPC, {'p_user_id': user_id, 'p_language_id': int(language_id),
                                        'p_cal_since': since_list})
    if rpc is None:
        return None
    frames = frame_bands(db)
    if frames is None:
        return None

    cal = rpc.get('calibration') or {}
    d_raw = cal.get('definition_language_id')
    d_star = _num(d_raw) if d_raw is not None else None
    bands = _bands(cal.get('bands'))
    alltime_n = _seven(cal.get('alltime_n'))
    frame = frame_for(frames, language_id, d_star)
    usable = _frame_usable(frame, bands)
    if not usable and (frame is not None or d_star is not None):
        logger.warning('knowledge_frame_mismatch user=%s lang=%s d=%s', short_id(user_id),
                       language_id, d_star)
    est_bands = bands if usable else [[0, 0, 0] for _ in range(ke.N_BANDS)]
    est_frame = frame if usable else [1] * ke.N_BANDS
    est = ke.estimate_range(est_bands, est_frame, alltime_n if usable else None)

    tracked = rpc.get('tracked') or {}
    tracked_rows = _num(tracked.get('rows', tracked.get('meanings')))
    nothing_yet = tracked_rows == 0 and d_star is None and sum(alltime_n) == 0
    state = ke.estimate_state(est, nothing_yet=nothing_yet)

    rated_in_frame = cal.get('rated_known_in_frame')
    rated_in_frame = _num(rated_in_frame) if rated_in_frame is not None else None
    universe = int(sum(frame)) if frame else None
    estimate = _estimate_block(est, d_star=d_star, cal=cal, universe=universe,
                               rated_known_in_frame=rated_in_frame)

    # since[i] answers p_cal_since[i] (WITH ORDINALITY); keep only comparisons on today's D*.
    since_rows = _comparable_since(snapshots, today, since_by_days, since_list,
                                   cal.get('since') or [], d_star, frame)
    growth = _growth_block(rpc, snapshots, today, frame, since_rows)

    last_seen = _date(rpc.get('last_seen_at'))
    days_since_evidence = (today - last_seen).days if last_seen else None
    last_answer = _date(_first(cal, 'last_answer_at', 'last_at'))
    missed = rpc.get('missed_recent') or {}
    steps = ke.next_steps({
        'state': state,
        'estimate': est,
        'prestudy': None,                     # rule 2 comes from /prestudy-suggestion (TASK-1041)
        'days_since_evidence': days_since_evidence,
        'idle60': _num(rpc.get('idle60_meanings')),
        'missed_recently': _num(missed.get('meanings')),
        'last_check_answer_days': (today - last_answer).days if last_answer else None,
        'reviews_deep_link': True,            # TASK-1043: /session?mode=practice&extra=reviews
    })

    level, enforced = report_detail_level(db, user_id)
    lists, lists_unavailable = list_coverage(db, user_id, language_id, rpc)
    watch = rpc.get('watchlist') or {}
    tracked_words = _num(tracked.get('words'))
    lang = Config.LANGUAGES.get(int(language_id)) or {}

    return {
        'language_id': int(language_id),
        'language': {'id': int(language_id), 'code': lang.get('code'), 'name': lang.get('display')},
        'as_of': rpc.get('as_of'),
        'method_version': ke.METHOD_VERSION,
        'detail': detail_payload(level, enforced),
        'state': state,
        'stale_days': (days_since_evidence if tracked_words > 0 and days_since_evidence is not None
                       and days_since_evidence >= STALE_DAYS else None),
        'few_tracked': 0 < tracked_words < FEW_TRACKED_WORDS,
        'estimate': estimate,
        'rated_known_words': _num(rpc.get('rated_known_words')),
        'tracked_words': tracked_words,
        'groups': _groups_block(est_bands, frame, bool(est.get('shown')), rpc.get('groups') or []),
        'lists': lists,
        'lists_unavailable': bool(lists_unavailable),
        'watchlist': dict(watch) if _num(watch.get('items')) > 0 else None,
        'growth': growth,
        'skills': _skills_block(rpc.get('families') or []),
        'missed_recent': {'meanings': _num(missed.get('meanings')),
                          'flagged': _num(missed.get('flagged'))},
        'next_steps': steps,
        'pro_teaser': {
            'tracked_meanings': _num(tracked.get('meanings')) or None,
            'missed_recent': _num(missed.get('meanings')) or None,
            'missing_next_level': None,       # TASK-1050 (needs list files)
            'next_level': None,
        },
    }


# ---------------------------------------------------------------- prestudy next step (§2.13 rule 2)

def _prestudy_allowance_left() -> bool:
    """Once billing TASK-980 exists: a ``prestudy_per_week`` use remains (no limit = unlimited).
    Until then there is no prestudy quota anywhere (F16), so always True."""
    entitlements = _billing_entitlements()
    if entitlements is None:
        return True
    try:
        cap = entitlements.limit('prestudy_per_week')
        if cap is None:
            return True
        used = entitlements.usage_this_week('prestudy_per_week') or 0
        return int(used) < int(cap)
    except Exception as exc:
        logger.info('prestudy allowance unreadable (%s); suggesting anyway', exc)
        return True


def prestudy_suggestion(db, user_id: str, language_id: int) -> Optional[dict]:
    """The top recommended reading/listening test when more than a quarter of its key words are new
    to the learner (``services/prestudy.py`` ``AUTO_THRESHOLD``), else None. Never raises: an RPC
    error is logged at info level and gives None."""
    from services import prestudy
    try:
        rows = db.rpc('get_recommended_tests', {'p_user_id': user_id,
                                                'p_language_id': int(language_id)}).execute().data or []
    except Exception as exc:
        logger.info('knowledge prestudy suggestion: get_recommended_tests failed (%s)', exc)
        return None
    top = next((r for r in rows if isinstance(r, Mapping)
                and r.get('test_type') in prestudy.PRESTUDY_TEST_TYPES and r.get('test_id')), None)
    if top is None:
        return None
    test_id = str(top['test_id'])
    try:
        plans = prestudy.plan_for_tests(db, user_id, int(language_id),
                                        [{'id': test_id, 'test_type': top['test_type']}])
    except Exception as exc:
        logger.info('knowledge prestudy suggestion: plan_for_tests failed (%s)', exc)
        return None
    plan = (plans or {}).get(test_id)
    if not plan or float(plan.get('unknown_share') or 0) <= prestudy.AUTO_THRESHOLD:
        return None
    if not _prestudy_allowance_left():
        return None
    return {'test_id': test_id, 'slug': top.get('slug'), 'title': top.get('title'),
            'test_type': top['test_type'], 'unknown': _num(plan.get('unknown')),
            'n': _num(plan.get('n')), 'unknown_share': float(plan['unknown_share'])}
