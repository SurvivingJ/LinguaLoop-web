# tests/test_bundle_flags.py
"""VOCAB_LADDER_BUNDLE_MODE flag reader (services/vocabulary_ladder/bundle/flags.py)."""

import pytest

from services.vocabulary_ladder.bundle import flags


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(flags.ENV_VAR, raising=False)
    yield


def test_default_is_off():
    assert flags.bundle_mode() == 'off'
    assert flags.bundle_enabled() is False
    assert flags.bundle_authoritative() is False


def test_shadow_mode(monkeypatch):
    monkeypatch.setenv(flags.ENV_VAR, 'shadow')
    assert flags.bundle_mode() == 'shadow'
    assert flags.bundle_enabled() is True
    assert flags.bundle_authoritative() is False


def test_on_mode(monkeypatch):
    monkeypatch.setenv(flags.ENV_VAR, 'on')
    assert flags.bundle_mode() == 'on'
    assert flags.bundle_enabled() is True
    assert flags.bundle_authoritative() is True


def test_case_and_whitespace_insensitive(monkeypatch):
    monkeypatch.setenv(flags.ENV_VAR, '  ON  ')
    assert flags.bundle_mode() == 'on'


def test_unrecognised_value_falls_back_to_off(monkeypatch):
    monkeypatch.setenv(flags.ENV_VAR, 'yolo')
    assert flags.bundle_mode() == 'off'
    assert flags.bundle_enabled() is False


def test_reads_fresh_each_call_not_cached(monkeypatch):
    monkeypatch.setenv(flags.ENV_VAR, 'off')
    assert flags.bundle_mode() == 'off'
    monkeypatch.setenv(flags.ENV_VAR, 'on')
    assert flags.bundle_mode() == 'on'
