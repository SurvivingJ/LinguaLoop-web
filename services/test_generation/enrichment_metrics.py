"""Vocabulary-enrichment throughput instrumentation (plan §2, T2.1).

Test generation runs at ~2.9 minutes per test. The reported cause was judging;
the measurement says otherwise — judges cost ~$0.001 per test against ~$0.015
of generation, about 6% of spend. The wall clock is **vocabulary enrichment**:
one LLM ``generate_sense()`` call per extracted word, fanned across 3 workers,
and enrichment volume scales brutally with tier:

    T1   22 senses/test        T4  107 senses/test
    T2   34 senses/test        T6  266 senses/test

A T6 test makes ~266 sense calls at 3-way concurrency. Raising concurrency is
not the lever: at 5x3 workers Supabase and Cloudflare began rejecting requests
outright, which is why ``config.py`` caps it.

Which lever *is* right depends on one number nobody had measured — the
``prefer_existing`` hit rate:

  * **high reuse** — most extracted words already have senses, so the calls are
    being avoided already and the remaining cost is elsewhere. The fix is
    pre-seeding a frequency-ranked shared sense bank (T2.4).
  * **low reuse** — most words are genuinely new, so the calls are real work.
    The fix is batching them, one call per N words (T2.2), and capping how many
    are enriched inline at all (T2.3).

This module reports that number per test; ``summarise_batch`` aggregates it
across a run.

MEASURED, live corpus, 2026-08-31 — 298 tests, 23,368 enrichment decisions:

    senses linked (distinct)        11,994
    total link events               23,368
    already existed at first link      914   (imported, e.g. CC-CEDICT)
    generated at link time          11,080
    ------------------------------------------------
    prefer_existing hit rate         52.6%

That lands in the middle band: reuse is real (half the decisions cost no LLM
call) but ~37 genuinely new senses per test still dominate the wall clock. So
the answer is not "pre-seeding instead of batching" — it is that
``split_inline_enrichment`` below (T2.3) helps regardless, which is why it
shipped, while T2.2 (one call per N words) stays open and should be re-measured
after T2.4 pre-seeding moves the hit rate.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


def hit_rate(created: int, reused: int) -> Optional[float]:
    """Fraction of enrichment decisions that avoided an LLM call.

    None when nothing was attempted — an undefined rate, not zero. Reporting a
    no-vocabulary test as "0% reuse" would drag a batch average towards the
    wrong conclusion.
    """
    total = created + reused
    if total <= 0:
        return None
    return reused / total


def log_enrichment_hit_rate(
    created: int,
    reused: int,
    words_attempted: int,
    seconds: Optional[float],
    test_id: Any,
    language_code: str,
) -> Optional[float]:
    """Log one test's enrichment cost profile. Returns the hit rate."""
    rate = hit_rate(created, reused)
    per_call = (
        seconds / created if seconds is not None and created > 0 else None
    )
    logger.info(
        'enrichment (test %s, %s): %d word(s) attempted, %d new + %d reused '
        '= %s reuse, %s in vocab_senses_llm%s',
        test_id, language_code, words_attempted, created, reused,
        'n/a' if rate is None else f'{rate:.0%}',
        'unmeasured' if seconds is None else f'{seconds:.1f}s',
        '' if per_call is None else f' ({per_call:.1f}s per new sense)',
    )
    return rate


def summarise_batch(outcomes: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate per-test enrichment outcomes into a batch verdict.

    ``outcomes`` are the per-test dicts written to ``tests.vocab_sense_stats``,
    so this works equally on a live run and on rows read back afterwards.

    The ``verdict`` field names which lever the measurement points at, in the
    plan's own terms. It is a reading of the data, not a decision — but it is
    the reading T2.2/T2.3 were waiting on, so it is stated rather than left for
    someone to recompute.
    """
    created = reused = attempted = tests = 0
    for outcome in outcomes:
        if not outcome:
            continue
        tests += 1
        created += int(outcome.get('senses_created') or 0)
        reused += int(outcome.get('senses_reused') or 0)
        attempted += int(outcome.get('words_attempted') or 0)

    rate = hit_rate(created, reused)
    return {
        'tests': tests,
        'words_attempted': attempted,
        'senses_created': created,
        'senses_reused': reused,
        'hit_rate': rate,
        'new_senses_per_test': (created / tests) if tests else None,
        'verdict': _verdict(rate, created, tests),
    }


# Above this share of reuse, the LLM calls are already mostly being avoided.
HIGH_REUSE = 0.70
# Below this, most extracted words are genuinely new work.
LOW_REUSE = 0.40


def _verdict(rate: Optional[float], created: int, tests: int) -> str:
    if rate is None or tests == 0:
        return 'no enrichment measured — nothing to conclude'
    per_test = created / tests
    if rate >= HIGH_REUSE:
        return (
            f'{rate:.0%} reuse: most words are already seeded, so batching '
            f'(T2.2) buys little. Pre-seed a frequency-ranked shared sense '
            f'bank (T2.4) to push the remaining {per_test:.0f} new senses per '
            f'test down.'
        )
    if rate <= LOW_REUSE:
        return (
            f'{rate:.0%} reuse: {per_test:.0f} genuinely new senses per test. '
            f'The calls are real work — batch them (T2.2) and cap inline '
            f'enrichment (T2.3).'
        )
    return (
        f'{rate:.0%} reuse: mixed. {per_test:.0f} new senses per test still '
        f'dominates the wall clock, so T2.3 (cap inline enrichment, push the '
        f'tail to backfill) helps regardless; measure again after T2.4.'
    )


def split_inline_enrichment(
    vocab_items: Sequence[Dict[str, Any]],
    language_code: str,
    cap: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split extracted vocabulary into (enrich now, defer to backfill) — T2.3.

    Ranked by Zipf frequency, most frequent first. Frequency is the right key
    on both counts: the most frequent words are the ones a learner most needs
    linked to the passage, and they are also the ones most likely to already
    have a sense (so deferring them would save no LLM call anyway). A word with
    no frequency data sorts last — unknown to ``wordfreq`` is a strong signal of
    a rare or proper-noun-ish token.

    ``cap <= 0`` disables the split entirely and everything is enriched inline,
    which is the pre-TASK-744 behaviour.

    Ordering is stable within equal frequency, so the same extraction splits the
    same way twice.
    """
    items = list(vocab_items)
    if cap <= 0 or len(items) <= cap:
        return items, []

    ranked = sorted(
        items,
        key=lambda item: -_zipf(item, language_code),
    )
    return ranked[:cap], ranked[cap:]


def _zipf(item: Dict[str, Any], language_code: str) -> float:
    """Zipf score for ranking; 0.0 when unknown or unavailable."""
    try:
        from services.vocabulary.frequency_service import (
            compute_zipf_for_vocab_item,
        )
        return float(compute_zipf_for_vocab_item(item, language_code) or 0.0)
    except Exception:
        # A frequency lookup failure must not decide whether a word is
        # enriched — it degrades the ranking, and an unranked word simply
        # sorts with the rest of the unknowns.
        return 0.0


def format_summary(summary: Dict[str, Any]) -> str:
    """One human-readable block for a batch report."""
    rate = summary.get('hit_rate')
    per_test = summary.get('new_senses_per_test')
    return (
        'Enrichment (T2.1):\n'
        f"  tests measured      : {summary['tests']}\n"
        f"  words attempted     : {summary['words_attempted']}\n"
        f"  senses created (LLM): {summary['senses_created']}\n"
        f"  senses reused       : {summary['senses_reused']}\n"
        f"  prefer_existing hit : "
        f"{'n/a' if rate is None else f'{rate:.1%}'}\n"
        f"  new senses per test : "
        f"{'n/a' if per_test is None else f'{per_test:.1f}'}\n"
        f"  verdict             : {summary['verdict']}"
    )
