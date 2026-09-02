"""Tests for realised-vs-requested question mix reporting (plan §1, T1.3).

`question_type_distributions_by_tier` was created 2026-08-29; all 307 live
tests predate it, so no test had ever run through the tier-keyed loader. The
legacy T6 content — supporting_detail at 0, author_purpose at twice its
intended rate — is what a silently-wrong distribution looks like, and is the
reason "the loader reads correct" was not accepted as evidence.
"""

import logging

import pytest

from services.test_generation.question_mix import (
    compare_question_mix,
    report_question_mix,
)

T6_MIX = [
    'supporting_detail', 'inference', 'inference',
    'vocabulary_context', 'author_purpose',
]


def test_an_exact_match_reports_no_divergence():
    report = compare_question_mix(T6_MIX, list(T6_MIX))
    assert report.matches
    assert report.missing == {}
    assert report.short == {}
    assert report.unrequested == {}


def test_order_does_not_matter():
    report = compare_question_mix(T6_MIX, list(reversed(T6_MIX)))
    assert report.matches


def test_a_type_that_produced_nothing_is_reported_missing():
    """The legacy T6 failure: supporting_detail requested, zero produced."""
    realised = [t for t in T6_MIX if t != 'supporting_detail']
    report = compare_question_mix(T6_MIX, realised)
    assert report.missing == {'supporting_detail': 1}
    assert not report.matches


def test_partial_loss_is_short_not_missing():
    """The survival floor deliberately tolerates losing one question, so a
    type that produced some-but-not-all is expected, not a defect."""
    realised = [t for t in T6_MIX if t != 'inference'] + ['inference']
    report = compare_question_mix(T6_MIX, realised)
    assert report.short == {'inference': 1}
    assert report.missing == {}


def test_an_unrequested_type_is_flagged():
    """The generator producing a type the tier table never named is a real
    bug, not a tolerable shortfall."""
    report = compare_question_mix(T6_MIX, T6_MIX + ['literal_detail'])
    assert report.unrequested == {'literal_detail': 1}
    assert not report.matches


def test_the_legacy_t6_skew_is_caught():
    """author_purpose at twice its rate AND supporting_detail at zero."""
    realised = [
        'author_purpose', 'author_purpose', 'inference', 'inference',
        'vocabulary_context',
    ]
    report = compare_question_mix(T6_MIX, realised)
    assert report.missing == {'supporting_detail': 1}
    assert report.realised['author_purpose'] == 2
    assert report.requested['author_purpose'] == 1


def test_untyped_questions_are_ignored_not_counted_as_unrequested():
    report = compare_question_mix(T6_MIX, T6_MIX + [None, ''])
    assert report.matches


def test_an_empty_realised_mix_reports_everything_missing():
    report = compare_question_mix(T6_MIX, [])
    assert set(report.missing) == set(T6_MIX)


# ----------------------------------------------------------------------
# Logging behaviour — this is the whole point of the task
# ----------------------------------------------------------------------

def _log(caplog, level, requested, realised):
    with caplog.at_level(level, logger='services.test_generation.question_mix'):
        report = report_question_mix(requested, realised, 6, 'ja')
    return report, ' | '.join(r.getMessage() for r in caplog.records)


def test_a_matching_mix_logs_at_info_not_warning(caplog):
    report, text = _log(caplog, logging.INFO, T6_MIX, list(T6_MIX))
    assert report.matches
    assert 'matches tier 6' in text
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_a_missing_type_warns(caplog):
    realised = [t for t in T6_MIX if t != 'supporting_detail']
    _, text = _log(caplog, logging.WARNING, T6_MIX, realised)
    assert 'SHORT' in text
    assert 'supporting_detail' in text


def test_an_unrequested_type_warns(caplog):
    _, text = _log(caplog, logging.WARNING, T6_MIX, T6_MIX + ['literal_detail'])
    assert 'DIVERGED' in text
    assert 'literal_detail' in text


def test_a_tolerated_partial_loss_does_not_warn(caplog):
    """A T1 test shipping 3 of 5 is the survival floor working as designed;
    warning on it would train everyone to ignore the warning."""
    realised = [t for t in T6_MIX if t != 'inference'] + ['inference']
    _log(caplog, logging.INFO, T6_MIX, realised)
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_the_log_carries_both_mixes_for_diagnosis(caplog):
    realised = [t for t in T6_MIX if t != 'supporting_detail']
    _, text = _log(caplog, logging.WARNING, T6_MIX, realised)
    assert 'requested=' in text and 'realised=' in text
