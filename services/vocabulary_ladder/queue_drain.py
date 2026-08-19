"""
Generation-queue drain + coverage check (TASK-517).

Two halves of one contract:

**The check.** After every batch, ask ``v_sense_family_coverage`` which
generated senses are missing a cognitive family they are supposed to teach,
and enqueue each as ``coverage_gap``. A sense with no ``form_production``
exercise is not "mostly done" — the session builder routes silently around the
hole, so the family goes untaught and nothing complains.

**The drain.** Work the queue oldest-first, re-running generation for each
sense and verifying the gap actually closed.

Why a queue rather than retrying in place
-----------------------------------------
A gap has causes with wildly different fixes: a missing pronunciation needs a
backfill, a judge rejection needs regeneration, an absent classifier entry
needs dictionary curation and will *never* resolve by retrying. Retrying
inside the batch loop would burn the batch's budget on senses that cannot
succeed. Queued rows carry their reason, can be inspected before a drain runs,
and transition to ``failed`` with a detail blob when they do not resolve — so
the permanently-impossible ones become visible instead of looping forever.

Statuses: ``pending`` -> ``running`` -> ``done`` | ``failed``.
Reasons: ``regen`` | ``coverage_gap`` | ``subscribe_topup``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from services.supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)

REASON_REGEN = 'regen'
REASON_COVERAGE_GAP = 'coverage_gap'
REASON_SUBSCRIBE_TOPUP = 'subscribe_topup'

STATUS_PENDING = 'pending'
STATUS_RUNNING = 'running'
STATUS_DONE = 'done'
STATUS_FAILED = 'failed'


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Coverage check
# ---------------------------------------------------------------------------

def coverage_gaps(db=None, language_id: int | None = None,
                  sense_ids: list[int] | None = None) -> list[dict]:
    """Senses missing at least one required family.

    Returns the view rows unchanged: ``{sense_id, language_id,
    missing_families, missing_count, required_count}``.
    """
    db = db or get_supabase_admin()
    try:
        query = db.table('v_sense_family_coverage').select('*').gt('missing_count', 0)
        if language_id is not None:
            query = query.eq('language_id', language_id)
        if sense_ids:
            query = query.in_('sense_id', sense_ids)
        return query.execute().data or []
    except Exception as exc:
        logger.error('coverage query failed: %s', exc)
        return []


def enqueue_coverage_gaps(db=None, language_id: int | None = None,
                          sense_ids: list[int] | None = None) -> dict:
    """Queue every uncovered sense. Idempotent.

    A sense already sitting in the queue as pending/running is not re-added —
    a nightly check would otherwise pile up one row per night for a gap that
    cannot be closed (a noun with no classifier entry, say).
    """
    db = db or get_supabase_admin()
    gaps = coverage_gaps(db, language_id, sense_ids)
    if not gaps:
        return {'gaps': 0, 'enqueued': 0, 'already_queued': 0}

    open_ids = _open_queue_sense_ids(db, [g['sense_id'] for g in gaps])
    rows = [
        {
            'sense_id': gap['sense_id'],
            'language_id': gap['language_id'],
            'reason': REASON_COVERAGE_GAP,
            'status': STATUS_PENDING,
            'detail': {
                'missing_families': gap.get('missing_families'),
                'missing_count': gap.get('missing_count'),
                'required_count': gap.get('required_count'),
            },
        }
        for gap in gaps if gap['sense_id'] not in open_ids
    ]
    if rows:
        try:
            db.table('generation_queue').insert(rows).execute()
        except Exception as exc:
            logger.error('failed to enqueue coverage gaps: %s', exc)
            return {'gaps': len(gaps), 'enqueued': 0, 'error': str(exc)}

    logger.info('coverage: %d gaps, %d enqueued, %d already queued',
                len(gaps), len(rows), len(gaps) - len(rows))
    return {
        'gaps': len(gaps),
        'enqueued': len(rows),
        'already_queued': len(gaps) - len(rows),
    }


def enqueue(db, sense_id: int, language_id: int, reason: str,
            detail: dict | None = None) -> bool:
    """Queue one sense.

    Used by the subscription top-up path (a learner subscribed to a sense with
    no assets) and by the batch runner when a sense fails outright.
    """
    db = db or get_supabase_admin()
    if _open_queue_sense_ids(db, [sense_id]):
        return False
    try:
        db.table('generation_queue').insert({
            'sense_id': sense_id,
            'language_id': language_id,
            'reason': reason,
            'status': STATUS_PENDING,
            'detail': detail or {},
        }).execute()
        return True
    except Exception as exc:
        logger.warning('enqueue failed for sense %s: %s', sense_id, exc)
        return False


def _open_queue_sense_ids(db, sense_ids: list[int]) -> set[int]:
    if not sense_ids:
        return set()
    try:
        resp = (
            db.table('generation_queue')
            .select('sense_id')
            .in_('sense_id', sense_ids)
            .in_('status', [STATUS_PENDING, STATUS_RUNNING])
            .execute()
        )
        return {row['sense_id'] for row in (resp.data or [])}
    except Exception as exc:
        logger.warning('queue lookup failed: %s', exc)
        return set()


# ---------------------------------------------------------------------------
# Drain
# ---------------------------------------------------------------------------

def drain(
    db=None,
    limit: int = 50,
    language_id: int | None = None,
    should_stop=None,
    dry_run: bool = False,
) -> dict:
    """Work pending queue rows oldest-first.

    ``should_stop`` is a zero-arg predicate checked between rows, so an admin
    stop button or a cron time budget can halt mid-drain without leaving a row
    stuck in ``running``.
    """
    db = db or get_supabase_admin()
    rows = _claim_batch(db, limit, language_id)
    if not rows:
        return {'processed': 0, 'done': 0, 'failed': 0, 'stopped': False}

    counts = {'processed': 0, 'done': 0, 'failed': 0, 'stopped': False}
    for row in rows:
        if should_stop is not None and should_stop():
            _release(db, row['id'])
            counts['stopped'] = True
            break
        counts['processed'] += 1
        if dry_run:
            logger.info('[dry-run] would regenerate sense %s (%s)',
                        row['sense_id'], row['reason'])
            _release(db, row['id'])
            continue
        ok, detail = _regenerate(db, row)
        _finish(db, row['id'], ok, detail)
        counts['done' if ok else 'failed'] += 1

    logger.info('drain: %s', counts)
    return counts


def _claim_batch(db, limit: int, language_id: int | None) -> list[dict]:
    """Take the oldest pending rows and mark them running.

    Not atomic — supabase-py has no ``SELECT ... FOR UPDATE SKIP LOCKED``. The
    drain is single-writer by construction (one admin trigger, one nightly
    cron behind an advisory lock), so the race this leaves open is not
    reachable in practice; the ``running`` mark exists to make a *crashed*
    drain visible, not to arbitrate concurrency.
    """
    try:
        query = (
            db.table('generation_queue')
            .select('id, sense_id, language_id, reason, detail')
            .eq('status', STATUS_PENDING)
            .order('requested_at', desc=False)
            .limit(limit)
        )
        if language_id is not None:
            query = query.eq('language_id', language_id)
        rows = query.execute().data or []
    except Exception as exc:
        logger.error('failed to claim queue batch: %s', exc)
        return []

    for row in rows:
        try:
            db.table('generation_queue').update(
                {'status': STATUS_RUNNING}).eq('id', row['id']).execute()
        except Exception as exc:
            logger.warning('could not mark row %s running: %s', row['id'], exc)
    return rows


def _release(db, row_id: int) -> None:
    """Put a claimed row back so a later drain picks it up."""
    try:
        db.table('generation_queue').update(
            {'status': STATUS_PENDING}).eq('id', row_id).execute()
    except Exception as exc:
        logger.warning('could not release row %s: %s', row_id, exc)


def _finish(db, row_id: int, ok: bool, detail: dict) -> None:
    try:
        db.table('generation_queue').update({
            'status': STATUS_DONE if ok else STATUS_FAILED,
            'completed_at': _now(),
            'detail': detail,
        }).eq('id', row_id).execute()
    except Exception as exc:
        logger.warning('could not finish row %s: %s', row_id, exc)


def _regenerate(db, row: dict) -> tuple[bool, dict]:
    """Re-run generation for one queued sense.

    Non-destructive ordering: the old exercises are deleted only *after* the
    new render has produced rows, so a failed regeneration leaves the learner
    with the content they had rather than with nothing.
    """
    from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
    from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer

    sense_id = row['sense_id']
    language_id = row['language_id']
    detail = dict(row.get('detail') or {})

    try:
        pipeline = VocabAssetPipeline(db)
        result = pipeline.generate_for_sense(sense_id, language_id, force=True)
        detail['pipeline_status'] = result.get('status')
        if result.get('errors'):
            detail['pipeline_errors'] = result['errors'][:5]
        if result.get('status') == 'failed':
            return False, detail

        renderer = LadderExerciseRenderer(db)
        new_rows = renderer.build_rows(sense_id, language_id)
        detail['skips'] = [
            {'type': s.type_code, 'reason': s.reason}
            for s in getattr(renderer, 'last_skips', [])
        ][:20]
        if not new_rows:
            detail['error'] = 'render produced no rows'
            return False, detail

        (db.table('exercises').delete()
           .eq('word_sense_id', sense_id)
           .not_.is_('word_asset_id', 'null')
           .execute())
        db.table('exercises').insert(new_rows).execute()
        detail['rendered'] = len(new_rows)

        # Did the regeneration actually close the gap? A drain reporting
        # success while the family is still missing is worse than one
        # reporting failure, because it stops anyone looking.
        remaining = coverage_gaps(db, sense_ids=[sense_id])
        if remaining:
            detail['still_missing'] = remaining[0].get('missing_families')
            return False, detail
        return True, detail

    except Exception as exc:
        logger.error('regeneration failed for sense %s: %s', sense_id, exc)
        detail['error'] = str(exc)[:500]
        return False, detail


# ---------------------------------------------------------------------------
# Nightly entry point
# ---------------------------------------------------------------------------

_LOCK_RPC = 'pg_try_advisory_lock_for_queue_drain'
_UNLOCK_RPC = 'pg_advisory_unlock_for_queue_drain'

# A regeneration is an LLM call per sense, so an unbounded nightly drain is an
# unbounded nightly bill. This cap is the ceiling on one night's spend; what it
# does not reach stays pending and is picked up tomorrow, still oldest-first.
DEFAULT_NIGHTLY_LIMIT = 50


def _try_lock(db) -> bool:
    """Best-effort cross-worker mutex; proceeds if the RPC isn't deployed yet.

    Mirrors services/model_health._try_lock so a missing migration degrades to
    "runs anyway" rather than "silently never runs".
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
        logger.warning('queue_drain: advisory lock unavailable, proceeding: %s', exc)
        return True


def _release_lock(db) -> None:
    if db is None:
        return
    try:
        db.rpc(_UNLOCK_RPC, {}).execute()
    except Exception:
        pass


def run_nightly_drain(db=None, limit: int = DEFAULT_NIGHTLY_LIMIT,
                      should_stop=None) -> dict:
    """Enqueue fresh coverage gaps, then drain the queue. Advisory-locked.

    Ordering is deliberate: the coverage sweep runs *first*, so a gap that
    appeared during the day is drained the same night instead of waiting a
    further 24 hours for the next sweep.

    The lock is what makes ``_claim_batch``'s non-atomic read-then-write safe —
    see the migration header. A worker that does not get the lock returns
    ``skipped`` rather than waiting, because the holder is already doing the
    identical work.
    """
    db = db or get_supabase_admin()

    if not _try_lock(db):
        logger.info('queue_drain: another worker holds the lock, skipping')
        return {'skipped': True, 'reason': 'lock_held'}

    try:
        coverage = enqueue_coverage_gaps(db)
        drained = drain(db, limit=limit, should_stop=should_stop)
        summary = {'skipped': False, 'coverage': coverage, 'drain': drained}
        logger.info('nightly queue drain: %s', summary)
        return summary
    finally:
        _release_lock(db)
