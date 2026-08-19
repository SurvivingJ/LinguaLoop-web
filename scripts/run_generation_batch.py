#!/usr/bin/env python3
"""
Ladder generation batch runner — the integration gate (TASK-515).

Runs the full pipeline (P1 mined+generated -> judges -> P2/P3 -> render, incl.
deterministic types and hant mirrors) over the top N senses per language, in
resumable chunks.

Usage::

    python -m scripts.run_generation_batch --language 1 --dry-run
    python -m scripts.run_generation_batch --language 1 --chunk 100
    python -m scripts.run_generation_batch --language 1 --top 1000 --ceiling 25.00
    python -m scripts.run_generation_batch --all-languages --chunk 100
    python -m scripts.run_generation_batch --language 1 --chunk 100 --workers 4

Three things this script exists to get right
--------------------------------------------

**Selection.** ``dim_vocabulary.frequency_rank`` holds a *Zipf score*, not a
rank — the observed range is 0.25 to 6.56 and higher means more common. Reading
it as a rank and sorting ascending would select the thousand *rarest* words in
the corpus, which is the exact opposite of the intent and would not be visible
in the output. Sorting is DESC, and :func:`select_senses` is the single place
that decides.

**Cost.** Three prompts plus judges, across a thousand senses, is real money.
Every chunk measures actual spend from ``llm_calls.cost_usd`` and projects the
remainder; exceeding ``--ceiling`` aborts the chunk rather than discovering the
overrun afterwards.

**Resumability.** A sense with valid assets is skipped, so re-running is cheap
and a crashed run resumes where it stopped. Failures are queued as ``regen``
with their reason rather than retried in-line — see ``queue_drain``.

Judges run fail-closed (``batch_mode``): a dead model slug aborts the batch
instead of rubber-stamping a thousand senses of unjudged content, which is what
TASK-510 was written to prevent.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger('generation_batch')

LANGUAGE_NAMES = {1: 'Chinese', 2: 'English', 3: 'Japanese'}

# Lemmas that are not words. The corpus contains bare digits ("1"), subscript
# characters ("₂"), and mis-segmented conjugation strings ("啄む ます た");
# every one would consume three LLM calls to produce an unusable asset.
_MAX_LEMMA_TOKENS = 3

# Languages written without inter-word spaces, where a space in a lemma is
# evidence of mis-segmentation rather than a legitimate phrase.
_SPACELESS_LANGUAGES = frozenset({1, 3})

# Below this share of attempted senses ending in a rendered set, the batch is
# producing noise and the run stops instead of buying more of it.
_MIN_VALID_RATE = 0.90


@dataclass
class ChunkReport:
    """What one chunk did, in the shape the batch report prints."""

    language_id: int
    attempted: int = 0
    succeeded: int = 0
    partial: int = 0
    failed: int = 0
    skipped: int = 0
    exercises_created: int = 0
    cost_usd: float = 0.0
    queued: int = 0
    aborted_reason: str | None = None
    skips_by_type: dict = field(default_factory=dict)
    judge_verdicts: dict = field(default_factory=dict)

    @property
    def valid_rate(self) -> float:
        """Share of attempted senses that ended with a rendered exercise set."""
        attempted = self.attempted - self.skipped
        if attempted <= 0:
            return 1.0
        return (self.succeeded + self.partial) / attempted


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def select_senses(db, language_id: int, top: int) -> list[dict]:
    """The batch's target list: highest-frequency senses first.

    Rules (TASK-515):
      * ``frequency_rank`` DESC — it is a Zipf score; see the module docstring.
      * ``sense_rank = 1`` first, so a word's primary sense is generated before
        its secondary ones. A learner meeting "bank" should get the money sense.
      * ``semantic_class = 'proper'`` excluded — proper nouns are not
        ladder-subscribed (definition flashcard only).
      * junk lemmas excluded — see :func:`_is_usable_lemma`.
    """
    rows: list[dict] = []
    page = 1000
    offset = 0
    # Over-fetch: the hygiene filter and the one-sense-per-lemma rule both
    # discard rows, and a short final list would silently generate fewer than
    # was asked for.
    want = top * 3

    while len(rows) < want:
        resp = (
            db.table('dim_word_senses')
            .select('id, sense_rank, definition,'
                    'dim_vocabulary!inner(id, lemma, language_id, '
                    'frequency_rank, semantic_class)')
            .eq('dim_vocabulary.language_id', language_id)
            .not_.is_('dim_vocabulary.frequency_rank', 'null')
            .order('frequency_rank', desc=True, foreign_table='dim_vocabulary')
            .range(offset, offset + page - 1)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < page:
            break
        offset += page

    candidates = []
    for row in rows:
        vocab = row.get('dim_vocabulary') or {}
        lemma = (vocab.get('lemma') or '').strip()
        if vocab.get('semantic_class') == 'proper':
            continue
        if not _is_usable_lemma(lemma, language_id):
            continue
        candidates.append({
            'sense_id': row['id'],
            'lemma': lemma,
            'sense_rank': row.get('sense_rank') or 99,
            'frequency': vocab.get('frequency_rank') or 0.0,
            'semantic_class': vocab.get('semantic_class'),
        })

    # Primary senses before secondary ones, then by frequency.
    candidates.sort(key=lambda c: (c['sense_rank'] != 1, -c['frequency']))

    # One sense per lemma at this stage: generating three senses of the same
    # word before touching the next word squanders the frequency ordering.
    seen_lemmas: set[str] = set()
    picked: list[dict] = []
    for candidate in candidates:
        if candidate['lemma'] in seen_lemmas:
            continue
        seen_lemmas.add(candidate['lemma'])
        picked.append(candidate)
        if len(picked) >= top:
            break
    return picked


def _is_usable_lemma(lemma: str, language_id: int) -> bool:
    """Reject corpus artefacts before they cost three LLM calls each.

    The space rule is language-dependent, and that matters. English phrases
    ("be on time") are legitimate multi-word lemmas. Chinese and Japanese are
    not written with inter-word spaces at all, so a space in a CJK lemma means
    the importer mis-segmented — "啄む ます た" is a verb and two of its own
    conjugation suffixes glued back together with spaces, not a word.
    """
    if not lemma:
        return False
    if lemma.isdigit() or lemma.isnumeric():
        return False
    if not any(char.isalpha() for char in lemma):
        return False
    if language_id in _SPACELESS_LANGUAGES:
        return not any(char.isspace() for char in lemma)
    return len(lemma.split()) <= _MAX_LEMMA_TOKENS


def _senses_with_valid_assets(db, sense_ids: list[int]) -> set[int]:
    """Which of these already have a valid P1 — the resume check."""
    done: set[int] = set()
    for start in range(0, len(sense_ids), 200):
        window = sense_ids[start:start + 200]
        try:
            resp = (
                db.table('word_assets')
                .select('sense_id')
                .in_('sense_id', window)
                .eq('asset_type', 'prompt1_core')
                .eq('is_valid', True)
                .execute()
            )
            done |= {row['sense_id'] for row in (resp.data or [])}
        except Exception as exc:
            logger.warning('resume check failed for a window: %s', exc)
    return done


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------

def spend_since(db, since_iso: str) -> float:
    """Actual USD spent since a timestamp, from ``llm_calls.cost_usd``.

    Measured rather than estimated: token pricing changes under us and a
    per-model estimate table would be wrong within a month.
    """
    try:
        resp = (
            db.table('llm_calls')
            .select('cost_usd')
            .gte('created_at', since_iso)
            .not_.is_('cost_usd', 'null')
            .execute()
        )
        return round(sum(float(r['cost_usd'] or 0) for r in (resp.data or [])), 4)
    except Exception as exc:
        logger.warning('cost query failed: %s', exc)
        return 0.0


def _judge_verdicts_since(db, since_iso: str) -> dict:
    """accept/flag/reject counts per judge, for the chunk report.

    Judge reject-rate is the number that says whether a chunk produced
    *content* or produced *noise*; at 60% reject the budget is being spent on
    output nobody will ever see.
    """
    out: dict[str, dict[str, int]] = {}
    try:
        resp = (
            db.table('llm_calls')
            .select('task_name, judge_verdict')
            .gte('created_at', since_iso)
            .not_.is_('judge_verdict', 'null')
            .execute()
        )
        for row in resp.data or []:
            bucket = out.setdefault(row['task_name'], {})
            verdict = row['judge_verdict']
            bucket[verdict] = bucket.get(verdict, 0) + 1
    except Exception as exc:
        logger.warning('judge verdict query failed: %s', exc)
    return out


# ---------------------------------------------------------------------------
# Chunk
# ---------------------------------------------------------------------------

@dataclass
class _SenseOutcome:
    """What one sense did, before it is folded into the ChunkReport.

    Workers build these; the main thread applies them. Keeping every counter
    mutation on one thread is why none of them needs a lock.
    """

    status: str = 'not_started'   # success|partial|failed|skipped|not_started
    exercises: int = 0
    queued: bool = False
    skips_by_type: dict = field(default_factory=dict)
    fatal: str | None = None      # judge outage — aborts the whole chunk


def _process_sense(db, language_id: int, sense: dict, pipeline, renderer) -> _SenseOutcome:
    """Generate, render and store one sense. Never raises.

    Runs on a worker thread, so it enters ``batch_mode()`` *itself*. That flag
    is deliberately thread-local — a batch must not flip the fail-open judge
    contract for a request thread in the same process — which means a worker
    cannot inherit it from whoever submitted the job. Setting it in the caller
    and generating in a pool thread would silently restore fail-open judging,
    the exact failure TASK-510 exists to prevent.
    """
    from services.exercise_generation.judges.base import JudgeUnavailable, batch_mode
    from services.vocabulary_ladder import queue_drain

    outcome = _SenseOutcome()
    sense_id = sense['sense_id']

    try:
        with batch_mode():
            result = pipeline.generate_for_sense(sense_id, language_id)
            status = result.get('status', 'failed')

            if status == 'skipped':
                outcome.status = 'skipped'
                return outcome
            if status == 'failed':
                outcome.status = 'failed'
                outcome.queued = queue_drain.enqueue(
                    db, sense_id, language_id, queue_drain.REASON_REGEN,
                    {'errors': (result.get('errors') or [])[:5],
                     'lemma': sense['lemma']},
                )
                return outcome

            rows = renderer.build_rows(sense_id, language_id)
            for skip in getattr(renderer, 'last_skips', []):
                outcome.skips_by_type[skip.type_code] = (
                    outcome.skips_by_type.get(skip.type_code, 0) + 1
                )

            if not rows:
                outcome.status = 'failed'
                outcome.queued = queue_drain.enqueue(
                    db, sense_id, language_id, queue_drain.REASON_REGEN,
                    {'error': 'render produced no rows', 'lemma': sense['lemma']},
                )
                return outcome

            # Replace only once the new set exists (non-destructive regen).
            (db.table('exercises').delete()
               .eq('word_sense_id', sense_id)
               .not_.is_('word_asset_id', 'null')
               .execute())
            db.table('exercises').insert(rows).execute()

            outcome.exercises = len(rows)
            outcome.status = 'success' if status == 'success' else 'partial'
            return outcome

    except JudgeUnavailable as exc:
        # Not this sense's failure — the judge layer is down, so nothing after
        # it can be trusted either. Left as 'not_started' so it is not counted
        # against the chunk, exactly as the sequential `break` used to.
        outcome.fatal = f'judge unavailable: {exc}'
        return outcome
    except Exception as exc:
        logger.error('sense %s (%s) failed: %s', sense_id, sense['lemma'], exc)
        outcome.status = 'failed'
        outcome.queued = queue_drain.enqueue(
            db, sense_id, language_id, queue_drain.REASON_REGEN,
            {'error': str(exc)[:500], 'lemma': sense['lemma']},
        )
        return outcome


def _apply_outcome(report: ChunkReport, outcome: _SenseOutcome) -> None:
    """Fold one sense's outcome into the running report. Main thread only."""
    if outcome.status == 'skipped':
        report.skipped += 1
    elif outcome.status == 'failed':
        report.failed += 1
    elif outcome.status == 'success':
        report.succeeded += 1
    elif outcome.status == 'partial':
        report.partial += 1

    report.exercises_created += outcome.exercises
    if outcome.queued:
        report.queued += 1
    for type_code, count in outcome.skips_by_type.items():
        report.skips_by_type[type_code] = (
            report.skips_by_type.get(type_code, 0) + count
        )


def run_chunk(
    db,
    language_id: int,
    senses: list[dict],
    ceiling_usd: float | None,
    dry_run: bool,
    should_stop=None,
    workers: int = 1,
) -> ChunkReport:
    """Generate + render one chunk of senses.

    ``workers`` puts that many senses in flight at once. Wall clock, not money,
    is what makes a full fill a multi-week job: a sense needs well over a dozen
    LLM calls plus judges and measures ~5.5 minutes, so the 9,075-sense pool is
    ~35 days run serially and ~9 at ``--workers 4`` — for the same $305. Senses
    are independent (no shared state between them, and the queue-drain advisory
    lock already covers cross-process safety), so concurrency here buys time
    without changing output.

    **Mind the multiplier.** Each sense already fans its P2/P3/split/typed
    generators across an 8-wide pool of its own, so ``workers=N`` means up to
    N x 8 concurrent provider calls. Check that against the OpenRouter rate
    limit before raising it; 4 is 32.

    ``workers=1`` is the default and reproduces the old sequential behaviour,
    with one difference worth knowing: generation now happens on a pool thread
    rather than the caller's, which is why ``batch_mode()`` moved into
    :func:`_process_sense`.
    """
    from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
    from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer

    report = ChunkReport(language_id=language_id, attempted=len(senses))
    started = datetime.now(timezone.utc).isoformat()

    if dry_run:
        logger.info('[dry-run] %d senses for %s: %s%s',
                    len(senses), LANGUAGE_NAMES.get(language_id, language_id),
                    ', '.join(s['lemma'] for s in senses[:12]),
                    ' ...' if len(senses) > 12 else '')
        report.skipped = len(senses)
        return report

    workers = max(1, int(workers or 1))
    abort = threading.Event()
    stop_requested = threading.Event()

    # LadderExerciseRenderer records per-call state in `last_skips`, so two
    # senses sharing one instance would race over the deterministic-skip tally
    # and mis-attribute skips. One renderer per worker thread — not per sense,
    # so its lazy ZH script-converter is still built once per thread rather
    # than once per word.
    local = threading.local()

    def _worker(sense: dict) -> _SenseOutcome:
        if abort.is_set():
            return _SenseOutcome()          # queued but never started
        if should_stop is not None and should_stop():
            stop_requested.set()
            abort.set()
            return _SenseOutcome()
        if getattr(local, 'pipeline', None) is None:
            local.pipeline = VocabAssetPipeline(db)
            local.renderer = LadderExerciseRenderer(db)
        return _process_sense(db, language_id, sense, local.pipeline, local.renderer)

    completed = 0
    pool = ThreadPoolExecutor(max_workers=workers)
    try:
        futures = [pool.submit(_worker, sense) for sense in senses]
        for future in as_completed(futures):
            outcome = future.result()

            if outcome.fatal:
                if not report.aborted_reason:
                    report.aborted_reason = outcome.fatal
                    logger.error(report.aborted_reason)
                abort.set()
                continue
            if outcome.status == 'not_started':
                continue

            _apply_outcome(report, outcome)
            completed += 1

            # Budget guardrail, checked every 10 completed senses — often
            # enough to stop a runaway, rarely enough not to add a query per
            # sense. With workers > 1 the in-flight senses' spend is already
            # counted while their completions are not, so the projection reads
            # slightly high and aborts slightly early. For a ceiling that is
            # the safe direction.
            if ceiling_usd and completed % 10 == 0:
                spent = spend_since(db, started)
                projected = spent / completed * len(senses)
                report.cost_usd = spent
                if projected > ceiling_usd:
                    report.aborted_reason = (
                        f'projected chunk cost ${projected:.2f} exceeds ceiling '
                        f'${ceiling_usd:.2f} (spent ${spent:.2f} over {completed} senses)'
                    )
                    logger.error(report.aborted_reason)
                    abort.set()
    finally:
        # An abort, a stop or a Ctrl-C must not leave the executor quietly
        # working through the rest of the queue on the way out.
        abort.set()
        pool.shutdown(wait=True, cancel_futures=True)

    if stop_requested.is_set() and not report.aborted_reason:
        report.aborted_reason = 'stop requested'

    report.cost_usd = spend_since(db, started)
    report.judge_verdicts = _judge_verdicts_since(db, started)
    return report


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_language(db, language_id: int, top: int, chunk_size: int,
                 max_chunks: int, ceiling: float | None,
                 dry_run: bool, workers: int = 1) -> list[ChunkReport]:
    from services.vocabulary_ladder import queue_drain

    name = LANGUAGE_NAMES.get(language_id, language_id)
    targets = select_senses(db, language_id, top)
    logger.info('%s: %d senses selected (top %d)', name, len(targets), top)
    if not targets:
        return []

    already = _senses_with_valid_assets(db, [t['sense_id'] for t in targets])
    pending = [t for t in targets if t['sense_id'] not in already]
    logger.info('%s: %d already generated, %d to do', name, len(already), len(pending))

    reports: list[ChunkReport] = []
    for chunk_index in range(max_chunks):
        chunk = pending[chunk_index * chunk_size:(chunk_index + 1) * chunk_size]
        if not chunk:
            break
        logger.info('--- %s chunk %d: %d senses (%d in flight) ---',
                    name, chunk_index + 1, len(chunk), max(1, int(workers or 1)))
        report = run_chunk(db, language_id, chunk, ceiling, dry_run,
                           workers=workers)
        reports.append(report)
        _print_report(report)
        if report.aborted_reason:
            break
        if report.valid_rate < _MIN_VALID_RATE and report.attempted >= 20:
            logger.error(
                'chunk valid-rate %.0f%% is below the %.0f%% bar — stopping the '
                'run rather than generating more of the same',
                report.valid_rate * 100, _MIN_VALID_RATE * 100,
            )
            break

    if not dry_run:
        logger.info('coverage check: %s',
                    queue_drain.enqueue_coverage_gaps(db, language_id=language_id))
    return reports


def _print_report(report: ChunkReport) -> None:
    logger.info(
        'chunk report | attempted=%d success=%d partial=%d failed=%d skipped=%d '
        'exercises=%d cost=$%.4f queued=%d valid_rate=%.0f%%',
        report.attempted, report.succeeded, report.partial, report.failed,
        report.skipped, report.exercises_created, report.cost_usd,
        report.queued, report.valid_rate * 100,
    )
    if report.skips_by_type:
        logger.info('  deterministic skips: %s',
                    json.dumps(report.skips_by_type, ensure_ascii=False))
    for task, verdicts in (report.judge_verdicts or {}).items():
        total = sum(verdicts.values()) or 1
        logger.info('  %s: %d calls, %.0f%% reject', task, total,
                    verdicts.get('reject', 0) / total * 100)
    if report.aborted_reason:
        logger.error('  ABORTED: %s', report.aborted_reason)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Ladder generation batch runner (TASK-515)')
    parser.add_argument('--language', type=int, choices=[1, 2, 3])
    parser.add_argument('--all-languages', action='store_true')
    parser.add_argument('--top', type=int, default=1000,
                        help='senses per language to target (default 1000)')
    parser.add_argument('--chunk', type=int, default=100,
                        help='senses per chunk (default 100 — one night)')
    parser.add_argument('--max-chunks', type=int, default=1,
                        help='chunks to run this invocation (default 1)')
    parser.add_argument('--ceiling', type=float, default=None,
                        help='abort a chunk if its projected cost exceeds this USD')
    parser.add_argument('--workers', type=int, default=1,
                        help='senses in flight at once (default 1 — serial). '
                             'Each sense already fans out 8 ways internally, so '
                             'N here means up to N*8 concurrent provider calls; '
                             'check the OpenRouter rate limit before raising it.')
    parser.add_argument('--dry-run', action='store_true',
                        help='print the selection without generating')
    parser.add_argument('--json', action='store_true',
                        help='emit the reports as JSON on stdout')
    args = parser.parse_args()

    if not args.language and not args.all_languages:
        parser.error('pass --language or --all-languages')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        stream=sys.stdout,
    )
    for noisy in ('httpx', 'httpcore', 'openai', 'urllib3'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    languages = [1, 2, 3] if args.all_languages else [args.language]
    all_reports: list[ChunkReport] = []
    for language_id in languages:
        all_reports.extend(run_language(
            db, language_id, args.top, args.chunk, args.max_chunks,
            args.ceiling, args.dry_run, workers=args.workers,
        ))

    logger.info('=' * 60)
    logger.info('run complete: %d chunks, %d exercises, $%.4f',
                len(all_reports),
                sum(r.exercises_created for r in all_reports),
                sum(r.cost_usd for r in all_reports))

    if args.json:
        print(json.dumps([asdict(r) for r in all_reports],
                         ensure_ascii=False, indent=2))

    if any(r.aborted_reason for r in all_reports):
        sys.exit(2)


if __name__ == '__main__':
    main()
