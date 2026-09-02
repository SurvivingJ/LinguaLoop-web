"""Tests for enrichment instrumentation and the inline cap (plan §2, T2.1/T2.3).

The reported cause of the 2.9 min/test wall clock was judging. It is not:
judges cost ~$0.001/test against ~$0.015 of generation. The cost is vocabulary
enrichment — one LLM call per extracted word — and enrichment volume scales
brutally with tier (live, 2026-08-31: T1 avg 19 senses/test, T6 avg 177,
max 382).

Concurrency is not the lever (5x3 workers made Supabase and Cloudflare reject
requests outright). Doing less of it synchronously is.
"""

import pytest

from services.test_generation.enrichment_metrics import (
    HIGH_REUSE,
    LOW_REUSE,
    format_summary,
    hit_rate,
    split_inline_enrichment,
    summarise_batch,
)


def _items(*lemmas):
    return [{'lemma': lemma} for lemma in lemmas]


# ----------------------------------------------------------------------
# T2.1 — the hit rate
# ----------------------------------------------------------------------

def test_hit_rate_is_the_share_of_calls_avoided():
    assert hit_rate(created=1, reused=3) == pytest.approx(0.75)


def test_hit_rate_is_undefined_not_zero_when_nothing_was_attempted():
    """A no-vocabulary test reported as '0% reuse' would drag a batch average
    towards the wrong conclusion."""
    assert hit_rate(0, 0) is None


def test_the_live_measurement_lands_in_the_mixed_band():
    """298 tests, 11,080 senses generated at link time, 12,288 avoided."""
    summary = summarise_batch([
        {'senses_created': 11080, 'senses_reused': 12288,
         'words_attempted': 23368},
    ])
    assert summary['hit_rate'] == pytest.approx(0.526, abs=0.002)
    assert LOW_REUSE < summary['hit_rate'] < HIGH_REUSE
    assert 'T2.3' in summary['verdict']


def test_high_reuse_points_at_pre_seeding():
    summary = summarise_batch([{'senses_created': 5, 'senses_reused': 95}])
    assert 'T2.4' in summary['verdict']


def test_low_reuse_points_at_batching():
    summary = summarise_batch([{'senses_created': 95, 'senses_reused': 5}])
    assert 'T2.2' in summary['verdict']


def test_an_empty_batch_concludes_nothing():
    summary = summarise_batch([])
    assert summary['hit_rate'] is None
    assert 'nothing to conclude' in summary['verdict']


def test_summary_tolerates_missing_and_null_outcomes():
    summary = summarise_batch([None, {}, {'senses_created': 2}])
    assert summary['senses_created'] == 2
    assert summary['senses_reused'] == 0


def test_format_summary_renders_without_a_rate():
    text = format_summary(summarise_batch([]))
    assert 'n/a' in text


# ----------------------------------------------------------------------
# T2.3 — the inline cap
# ----------------------------------------------------------------------

def test_a_cap_of_zero_disables_the_split():
    """Pre-TASK-744 behaviour: enrich everything inline."""
    items = _items(*[f'w{i}' for i in range(200)])
    inline, deferred = split_inline_enrichment(items, 'en', 0)
    assert len(inline) == 200
    assert deferred == []


def test_a_test_under_the_cap_is_untouched():
    """T1 averages 19 senses and maxes at 43, so the default cap of 80 must
    never touch it."""
    items = _items(*[f'w{i}' for i in range(43)])
    inline, deferred = split_inline_enrichment(items, 'en', 80)
    assert len(inline) == 43
    assert deferred == []
    assert inline == items, 'an under-cap split must not even reorder'


def test_a_test_over_the_cap_is_split_exactly():
    """T6 averages 177 and maxes at 382 — this is the tier the cap is for."""
    items = _items(*[f'w{i}' for i in range(382)])
    inline, deferred = split_inline_enrichment(items, 'en', 80)
    assert len(inline) == 80
    assert len(deferred) == 302
    assert len(inline) + len(deferred) == len(items)


def test_nothing_is_lost_in_the_split():
    items = _items(*[f'w{i}' for i in range(150)])
    inline, deferred = split_inline_enrichment(items, 'en', 80)
    assert {i['lemma'] for i in inline + deferred} == {i['lemma'] for i in items}


def test_frequent_words_are_enriched_and_rare_ones_deferred():
    """Frequency is right on both counts: the frequent words are what the
    learner most needs linked, and they are the ones most likely to already
    have a sense — so deferring them would save no LLM call anyway."""
    items = _items('the', 'quixotic', 'and', 'perspicacious', 'of')
    inline, deferred = split_inline_enrichment(items, 'en', 3)
    assert {i['lemma'] for i in inline} == {'the', 'and', 'of'}
    assert {i['lemma'] for i in deferred} == {'quixotic', 'perspicacious'}


def test_unknown_words_sort_last():
    """Unknown to wordfreq is a strong signal of a rare or proper-noun token."""
    items = _items('the', 'zzqxjv', 'and')
    inline, deferred = split_inline_enrichment(items, 'en', 2)
    assert 'zzqxjv' in {i['lemma'] for i in deferred}


def test_the_split_is_deterministic():
    items = _items('the', 'quixotic', 'and', 'perspicacious', 'of', 'a')
    first = split_inline_enrichment(items, 'en', 3)
    for _ in range(3):
        assert split_inline_enrichment(items, 'en', 3) == first


def test_zipf_swallows_a_broken_lookup(monkeypatch):
    """A wordfreq failure must not decide whether a word gets enriched — it
    costs the ordering, and the word then sorts with the unknowns."""
    import services.vocabulary.frequency_service as fs
    from services.test_generation.enrichment_metrics import _zipf

    monkeypatch.setattr(
        fs, 'compute_zipf_for_vocab_item',
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError('wordfreq exploded')),
    )
    assert _zipf({'lemma': 'the'}, 'en') == 0.0


def test_the_split_still_produces_the_right_sizes_with_no_frequency_data(
    monkeypatch,
):
    import services.vocabulary.frequency_service as fs

    monkeypatch.setattr(fs, 'compute_zipf_for_vocab_item', lambda *a, **k: None)
    items = _items(*[f'w{i}' for i in range(10)])
    inline, deferred = split_inline_enrichment(items, 'en', 4)
    assert len(inline) == 4
    assert len(deferred) == 6


def test_zipf_returns_zero_rather_than_raising_on_a_bad_item():
    from services.test_generation.enrichment_metrics import _zipf
    assert _zipf({}, 'en') == 0.0
