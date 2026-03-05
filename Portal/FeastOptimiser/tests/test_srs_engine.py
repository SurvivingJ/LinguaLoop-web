"""Tests for the SM-2 spaced repetition engine."""

import tempfile
import pytest
from models.csv_store import CSVStore
from services.srs_engine import (
    record_practice, calculate_mastery_percentage,
    calculate_retention_rate, get_effective_skill_level
)


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield CSVStore(tmpdir)


def test_first_practice_creates_card(store):
    result = record_practice(store, 'stir_frying', 4)
    assert result['next_review_days'] == 1
    assert result['mastery_percentage'] > 0


def test_quality_5_increases_interval(store):
    record_practice(store, 'stir_frying', 5)
    r2 = record_practice(store, 'stir_frying', 5)
    assert r2['next_review_days'] == 6  # Second rep = 6 days


def test_quality_below_3_resets(store):
    # Build up some reps
    record_practice(store, 'stir_frying', 5)
    record_practice(store, 'stir_frying', 5)
    record_practice(store, 'stir_frying', 5)
    # Now fail
    result = record_practice(store, 'stir_frying', 2)
    assert result['next_review_days'] == 1  # Reset to 1


def test_ef_minimum_1_3(store):
    # Repeated low scores should not push EF below 1.3
    for _ in range(10):
        record_practice(store, 'stir_frying', 0)
    result = record_practice(store, 'stir_frying', 0)
    assert result['new_easiness'] >= 1.3


def test_interval_capped_at_60(store):
    # Build up many perfect reps
    for _ in range(20):
        record_practice(store, 'stir_frying', 5)
    result = record_practice(store, 'stir_frying', 5)
    assert result['next_review_days'] <= 60


def test_mastery_zero_for_unknown(store):
    assert calculate_mastery_percentage(store, 'unknown_technique') == 0.0


def test_mastery_increases_with_practice(store):
    record_practice(store, 'stir_frying', 5)
    m1 = calculate_mastery_percentage(store, 'stir_frying')
    record_practice(store, 'stir_frying', 5)
    m2 = calculate_mastery_percentage(store, 'stir_frying')
    assert m2 > m1


def test_retention_zero_for_unknown(store):
    assert calculate_retention_rate(store, 'unknown_technique') == 0.0


def test_retention_high_after_practice(store):
    record_practice(store, 'stir_frying', 5)
    retention = calculate_retention_rate(store, 'stir_frying')
    assert retention > 90  # Just practiced, should be near 100%


def test_skill_level_novice_by_default(store):
    skill = get_effective_skill_level(store, 'stir_frying')
    assert skill['base_level'] == 'novice'
