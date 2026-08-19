"""
Model-slug health probe — catch delisted model slugs before they cause an outage.

Why this exists
---------------
Two total generation outages (audit finding G8) had the same root cause: a
model slug configured in ``prompt_templates`` was delisted by OpenRouter, every
call against it 404'd, and — because judges fail open — the pipeline kept
running and shipped unjudged content until someone noticed by hand. See memory
``prompt-template-model-slug-rot``: the model lives in the DB, not in code, so
a delisting is invisible to code review.

This module probes every distinct *active* model slug against the provider's
``/models`` listing and reports the ones that no longer resolve. It is the
detection half of TASK-510; the prevention half is
``judges.base.batch_mode()``, which makes a batch abort rather than fall open.

Two entry points
----------------
``check_model_slugs()``     — pure probe, returns a report dict. Safe to call
                              from a request (memoised for ``_CACHE_TTL_SECONDS``).
``run_slug_health_check()`` — nightly cron wrapper: advisory-locked, refreshes
                              the cache, logs an ERROR naming the offending
                              prompt_templates rows.

Only ``provider='openrouter'`` rows are probed. Ollama slugs are served from a
local daemon whose model list is environment-specific, so a "missing" ollama
slug on the web host is not evidence of rot; those rows are reported under
``skipped`` instead of ``dead``.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Report cache — a dashboard poll must not hit OpenRouter on every page load.
_CACHE_TTL_SECONDS = 900          # 15 min
_cache: dict | None = None
_cache_at: float = 0.0

# Advisory-lock key 1298417772 = 0x4D64486C = ASCII 'MdHl' (Model Health).
# Distinct from the IRT job's key and the Study-Plan pacer's 1467840848.
_LOCK_RPC   = 'pg_try_advisory_lock_for_model_health'
_UNLOCK_RPC = 'pg_advisory_unlock_for_model_health'

_PROBEABLE_PROVIDERS = frozenset({'openrouter'})


# ---------------------------------------------------------------------------
# Probe
# ---------------------------------------------------------------------------

def check_model_slugs(db=None, *, force: bool = False) -> dict:
    """Probe every active prompt_templates model slug against its provider.

    Returns a report::

        {'checked_at':  '2026-08-08T04:10:00+00:00',
         'ok':           bool,     # False iff dead slugs were found
         'probed':       int,      # distinct openrouter slugs checked
         'dead':        [{'model': 'qwen/qwen-max',
                          'provider': 'openrouter',
                          'rows': [{'task_name': ..., 'language_id': 1,
                                    'version': 4}, ...]}, ...],
         'skipped':     [{'model': ..., 'provider': 'ollama', 'rows': [...]}],
         'error':        str | None}   # probe itself failed (network/auth)

    Never raises: a probe failure is reported as ``error`` with ``ok`` left
    True, so a flaky network cannot manufacture a false "everything is dead"
    banner on the dashboard.
    """
    global _cache, _cache_at

    if not force and _cache is not None and (time.time() - _cache_at) < _CACHE_TTL_SECONDS:
        return _cache

    report = {
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'ok': True,
        'probed': 0,
        'dead': [],
        'skipped': [],
        'error': None,
    }

    try:
        rows = _active_template_rows(db)
    except Exception as exc:
        logger.warning("model_health: could not read prompt_templates: %s", exc)
        report['error'] = f'prompt_templates unreadable: {exc}'
        _cache, _cache_at = report, time.time()
        return report

    by_slug: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        model = (row.get('model') or '').strip()
        provider = (row.get('provider') or '').strip() or 'openrouter'
        if not model:
            continue
        by_slug.setdefault((provider, model), []).append({
            'task_name': row.get('task_name'),
            'language_id': row.get('language_id'),
            'version': row.get('version'),
        })

    probeable = {k: v for k, v in by_slug.items() if k[0] in _PROBEABLE_PROVIDERS}
    report['skipped'] = [
        {'model': model, 'provider': provider, 'rows': rows_}
        for (provider, model), rows_ in sorted(by_slug.items())
        if provider not in _PROBEABLE_PROVIDERS
    ]

    if not probeable:
        _cache, _cache_at = report, time.time()
        return report

    try:
        live = _live_model_ids('openrouter')
    except Exception as exc:
        # Probe failure is not evidence of dead slugs. Report it, claim nothing.
        logger.warning("model_health: provider model listing failed: %s", exc)
        report['error'] = f'provider /models unreachable: {exc}'
        _cache, _cache_at = report, time.time()
        return report

    report['probed'] = len(probeable)
    for (provider, model), rows_ in sorted(probeable.items()):
        if not _slug_is_live(model, live):
            report['dead'].append({'model': model, 'provider': provider, 'rows': rows_})

    report['ok'] = not report['dead']
    _cache, _cache_at = report, time.time()
    return report


def _active_template_rows(db=None) -> list[dict]:
    """All active prompt_templates rows carrying a model slug."""
    if db is None:
        from services.supabase_factory import get_supabase_admin, get_supabase
        db = get_supabase_admin() or get_supabase()
    if db is None:
        raise RuntimeError('no Supabase client available')

    resp = (
        db.table('prompt_templates')
        .select('task_name, language_id, version, model, provider')
        .eq('is_active', True)
        .execute()
    )
    return resp.data or []


def _live_model_ids(provider: str) -> set[str]:
    """Fetch the provider's advertised model ids via the OpenAI-compatible API."""
    from services.llm_service import get_client

    client = get_client(provider)
    listing = client.models.list()
    ids: set[str] = set()
    for item in getattr(listing, 'data', None) or []:
        model_id = getattr(item, 'id', None)
        if model_id:
            ids.add(str(model_id))
    if not ids:
        raise RuntimeError('provider returned an empty model list')
    return ids


def _slug_is_live(model: str, live: set[str]) -> bool:
    """Match a configured slug against the provider's advertised ids.

    OpenRouter accepts routing suffixes its listing does not echo back
    (``:free``, ``:nitro``, ``:floor``, and ``@preset/...``). Strip those before
    comparing so a live model carrying a routing hint isn't reported as dead.
    """
    if model in live:
        return True
    base = model.split('@', 1)[0].split(':', 1)[0]
    return base in live


# ---------------------------------------------------------------------------
# Nightly cron entry point
# ---------------------------------------------------------------------------

def run_slug_health_check() -> dict:
    """Advisory-locked nightly probe. Logs an ERROR naming any dead rows.

    Returns the report, or ``{'skipped': 'lock'}`` when another worker holds
    the lock, so the caller can log a one-line summary.
    """
    from services.supabase_factory import get_supabase_admin
    db = get_supabase_admin()

    if not _try_lock(db):
        logger.info("model_health: another worker holds the slug-health lock; skipping.")
        return {'skipped': 'lock'}

    try:
        report = check_model_slugs(db, force=True)
    finally:
        _release_lock(db)

    if report.get('error'):
        logger.warning("model_health: probe incomplete — %s", report['error'])
    for entry in report.get('dead', []):
        rows = ', '.join(
            f"{r['task_name']}/lang={r['language_id']}/v{r['version']}"
            for r in entry['rows']
        )
        logger.error(
            "DEAD MODEL SLUG %r (%s) — %d active prompt_templates row(s) will "
            "404 on every call: %s",
            entry['model'], entry['provider'], len(entry['rows']), rows,
        )
    return report


def _try_lock(db) -> bool:
    """Best-effort cross-worker mutex; proceeds if the RPC isn't deployed yet.

    Mirrors services/irt/calibrator._try_advisory_lock so a missing migration
    degrades to "runs anyway" rather than "silently never runs".
    """
    if db is None:
        return True
    try:
        resp = db.rpc(_LOCK_RPC, {}).execute()
        data = resp.data
        if isinstance(data, list):
            data = data[0] if data else False
        return bool(data)
    except Exception as exc:
        logger.warning("model_health: advisory lock unavailable, proceeding: %s", exc)
        return True


def _release_lock(db) -> None:
    if db is None:
        return
    try:
        db.rpc(_UNLOCK_RPC, {}).execute()
    except Exception:
        pass


def reset_cache() -> None:
    """Drop the memoised report (tests, and the manual admin trigger)."""
    global _cache, _cache_at
    _cache, _cache_at = None, 0.0
