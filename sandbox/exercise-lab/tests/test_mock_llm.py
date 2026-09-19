"""Proves the mock LLM's three modes behave as documented: synthetic is
deterministic and instant, replay requires a pre-recorded fixture, and -
the hard rule this whole module exists to enforce - live mode refuses to
run unless BOTH the constructor flag and the environment variable are set."""
import pytest

from lab.mock_llm import BudgetExceededError, LiveCallDisabledError, MockLLMClient


def test_synthetic_mode_is_deterministic_given_the_same_prompt():
    c1 = MockLLMClient(mode="synthetic", synthetic_latency_ms=0)
    c2 = MockLLMClient(mode="synthetic", synthetic_latency_ms=0)
    r1 = c1.complete("generate exercises for 猫")
    r2 = c2.complete("generate exercises for 猫")
    assert r1.text == r2.text
    assert r1.mode == "synthetic"
    assert not r1.cache_hit


def test_live_mode_raises_with_no_opt_in_at_all():
    client = MockLLMClient(mode="live")
    with pytest.raises(LiveCallDisabledError):
        client.complete("anything")


def test_live_mode_raises_with_constructor_flag_but_no_env_var(monkeypatch):
    monkeypatch.delenv("EXERCISE_LAB_ALLOW_LIVE_LLM", raising=False)
    client = MockLLMClient(mode="live", allow_live=True)
    with pytest.raises(LiveCallDisabledError):
        client.complete("anything")


def test_live_mode_raises_with_env_var_but_no_constructor_flag(monkeypatch):
    monkeypatch.setenv("EXERCISE_LAB_ALLOW_LIVE_LLM", "1")
    client = MockLLMClient(mode="live", allow_live=False)
    with pytest.raises(LiveCallDisabledError):
        client.complete("anything")


def test_live_mode_with_both_opt_ins_is_still_an_unimplemented_stub(monkeypatch):
    """Even with double opt-in, live mode must not silently succeed - a
    later agent has to deliberately implement the real call."""
    monkeypatch.setenv("EXERCISE_LAB_ALLOW_LIVE_LLM", "1")
    client = MockLLMClient(mode="live", allow_live=True)
    with pytest.raises(NotImplementedError):
        client.complete("anything")


def test_replay_mode_requires_a_recorded_fixture(tmp_path):
    client = MockLLMClient(mode="replay", cache_path=tmp_path / "cache.json")
    with pytest.raises(KeyError):
        client.complete("a prompt with no fixture")


def test_replay_mode_returns_the_recorded_fixture(tmp_path):
    client = MockLLMClient(mode="replay", cache_path=tmp_path / "cache.json")
    client.record_fixture("hello", "recorded response text")
    response = client.complete("hello")
    assert response.text == "recorded response text"
    assert response.cache_hit


def test_budget_ceiling_hard_stops_before_overspend():
    client = MockLLMClient(mode="synthetic", synthetic_latency_ms=0, usd_ceiling=1e-7)
    with pytest.raises(BudgetExceededError):
        client.complete("a" * 2000)
    assert client.spent_usd() == 0.0  # the over-budget call must not be counted as spent
