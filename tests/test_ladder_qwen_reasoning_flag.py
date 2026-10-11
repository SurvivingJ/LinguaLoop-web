"""ADR-028 Phase-2 attribution flag (2026-10-03) — `LADDER_QWEN_REASONING`.

Phase 2's blind pairwise quality review (bundle mode vs. phase1) failed
non-inferiority in every language, but Phase 2 changed two things vs. Phase 1
at once: bundle mode AND qwen reasoning actually being off
(`services.llm_service._use_enabled_false_reasoning_param`, landed
2026-09-28, after Phase 1's own eval was measured). `LADDER_QWEN_REASONING`
lets a clean attribution eval hold qwen's reasoning state fixed while bundle
mode is varied independently:

  * `on` (rollback value since TASK-857; default is now `budget`): restores the exact qwen reasoning-call-shape Phase 1's
    published numbers were measured under (see
    `test_provider_routing_and_reasoning.py` for the payload-shape tests) AND
    the reasoning-safe (pre-2026-10-03) `max_tokens` caps in every qwen
    generation/judge call site this task touched -- reasoning tokens count
    toward `max_tokens`, so the ADR-028-cost-work right-sized caps (derived
    from reasoning-OFF measurements) would truncate a genuinely-reasoning
    call.
  * `off`: the current (2026-10-03) cost-fix behaviour -- right-sized caps
    throughout, matching what Phase 2 actually ran under.

This file is the "caps" half of the contract; the payload-shape half lives in
test_provider_routing_and_reasoning.py. Every module tested here runs on a
qwen model (per wiki/evaluations/exercise-gen-phase2-2026-10.md §7's
worst-case-$ table): bundle generator/judge (all/both supported languages),
prompt1/2/3 core-ladder generators (TASK-813 moved these to qwen for every
language), and the particle judge (qwen, ja-only -- the one per-level judge
NOT on gemini). The other five per-level judges (cloze, collocation,
l1_distractor, relation, sentence_validity) are gemini-based and therefore
intentionally untouched by this flag -- gemini doesn't reason, so there is no
reasoning-safe cap to restore for them (see test_judge_max_tokens_caps.py).

DB-free and network-free throughout: only the module-level cap-selection
helpers are exercised, not a real `call_llm`.
"""

import pytest

from services.vocabulary_ladder.asset_generators import prompt1_core as p1mod
from services.vocabulary_ladder.asset_generators import prompt2_exercises as p2mod
from services.vocabulary_ladder.asset_generators import prompt3_transforms as p3mod
from services.vocabulary_ladder.bundle import generator as bundle_gen_mod
from services.vocabulary_ladder.bundle import judge as bundle_judge_mod
from services.exercise_generation.judges import particle as particle_mod


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv('LADDER_QWEN_REASONING', raising=False)


# ---------------------------------------------------------------------------
# prompt1_core.py
# ---------------------------------------------------------------------------

def test_p1_core_caps_default_to_reasoning_safe_values():
    assert p1mod._max_tokens_primary() == 8192
    assert p1mod._max_tokens_repair() == 8192
    assert p1mod._max_tokens_sentence_repair() == 4096


def test_p1_core_caps_switch_to_rightsized_when_off(monkeypatch):
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'off')
    assert p1mod._max_tokens_primary() == 4000
    assert p1mod._max_tokens_repair() == 4000
    assert p1mod._max_tokens_sentence_repair() == 500


@pytest.mark.parametrize('mode', ['low', 'budget'])
def test_p1_core_caps_stay_reasoning_safe_for_low_and_budget(monkeypatch, mode):
    monkeypatch.setenv('LADDER_QWEN_REASONING', mode)
    assert p1mod._max_tokens_primary() == 8192
    assert p1mod._max_tokens_repair() == 8192
    assert p1mod._max_tokens_sentence_repair() == 4096


# ---------------------------------------------------------------------------
# prompt2_exercises.py
# ---------------------------------------------------------------------------

def test_p2_exercises_cap_default_to_reasoning_safe_value():
    assert p2mod._max_tokens() == 8192


def test_p2_exercises_cap_switches_to_rightsized_when_off(monkeypatch):
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'off')
    assert p2mod._max_tokens() == 2000


@pytest.mark.parametrize('mode', ['low', 'budget'])
def test_p2_exercises_cap_stays_reasoning_safe_for_low_and_budget(monkeypatch, mode):
    monkeypatch.setenv('LADDER_QWEN_REASONING', mode)
    assert p2mod._max_tokens() == 8192


# ---------------------------------------------------------------------------
# prompt3_transforms.py
# ---------------------------------------------------------------------------

def test_p3_transforms_cap_default_to_reasoning_safe_value():
    assert p3mod._max_tokens() == 8192


def test_p3_transforms_cap_switches_to_rightsized_when_off(monkeypatch):
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'off')
    assert p3mod._max_tokens() == 1000


@pytest.mark.parametrize('mode', ['low', 'budget'])
def test_p3_transforms_cap_stays_reasoning_safe_for_low_and_budget(monkeypatch, mode):
    monkeypatch.setenv('LADDER_QWEN_REASONING', mode)
    assert p3mod._max_tokens() == 8192


# ---------------------------------------------------------------------------
# bundle/generator.py (per-language caps)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('language_id,expected', [(1, 40000), (2, 44000), (3, 34000)])
def test_bundle_generator_caps_default_to_reasoning_safe_values(language_id, expected):
    assert bundle_gen_mod._max_tokens_for_language(language_id) == expected


def test_bundle_generator_cap_default_on_falls_back_for_unknown_language():
    assert bundle_gen_mod._max_tokens_for_language(999) == 40000


@pytest.mark.parametrize('language_id,expected', [(1, 9000), (2, 9500), (3, 7000)])
def test_bundle_generator_caps_switch_to_rightsized_when_off(monkeypatch, language_id, expected):
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'off')
    assert bundle_gen_mod._max_tokens_for_language(language_id) == expected


def test_bundle_generator_cap_off_falls_back_for_unknown_language(monkeypatch):
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'off')
    assert bundle_gen_mod._max_tokens_for_language(999) == 9500


@pytest.mark.parametrize('mode', ['low', 'budget'])
@pytest.mark.parametrize('language_id,expected', [(1, 40000), (2, 44000), (3, 34000)])
def test_bundle_generator_caps_stay_reasoning_safe_for_low_and_budget(monkeypatch, mode, language_id, expected):
    monkeypatch.setenv('LADDER_QWEN_REASONING', mode)
    assert bundle_gen_mod._max_tokens_for_language(language_id) == expected


# ---------------------------------------------------------------------------
# bundle/judge.py
# ---------------------------------------------------------------------------

def test_bundle_judge_cap_default_to_reasoning_safe_value():
    assert bundle_judge_mod._max_tokens() == 16000


def test_bundle_judge_cap_switches_to_rightsized_when_off(monkeypatch):
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'off')
    assert bundle_judge_mod._max_tokens() == 4500


@pytest.mark.parametrize('mode', ['low', 'budget'])
def test_bundle_judge_cap_stays_reasoning_safe_for_low_and_budget(monkeypatch, mode):
    monkeypatch.setenv('LADDER_QWEN_REASONING', mode)
    assert bundle_judge_mod._max_tokens() == 16000


# ---------------------------------------------------------------------------
# judges/particle.py (qwen, ja-only -- the one per-level judge this flag
# touches; the other five are gemini and unaffected, see module docstring)
# ---------------------------------------------------------------------------

def test_particle_judge_cap_default_to_reasoning_safe_value():
    assert particle_mod._max_tokens() == 9000


def test_particle_judge_cap_switches_to_rightsized_when_off(monkeypatch):
    monkeypatch.setenv('LADDER_QWEN_REASONING', 'off')
    assert particle_mod._max_tokens() == 200


@pytest.mark.parametrize('mode', ['low', 'budget'])
def test_particle_judge_cap_stays_reasoning_safe_for_low_and_budget(monkeypatch, mode):
    monkeypatch.setenv('LADDER_QWEN_REASONING', mode)
    assert particle_mod._max_tokens() == 9000


# ---------------------------------------------------------------------------
# The other five per-level judges are gemini-based and must NOT expose a
# flag-gated cap function -- they have nothing to restore (gemini doesn't
# reason), and giving them one would risk someone wiring the flag to a
# model that was never part of this finding.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('module_path', [
    'services.exercise_generation.judges.cloze',
    'services.exercise_generation.judges.collocation',
    'services.exercise_generation.judges.l1_distractor',
    'services.exercise_generation.judges.relation',
    'services.exercise_generation.judges.sentence_validity',
])
def test_gemini_judges_have_no_reasoning_gated_cap_helper(module_path):
    import importlib
    module = importlib.import_module(module_path)
    assert not hasattr(module, '_max_tokens'), (
        f'{module_path} is gemini-based (does not reason) and should not '
        f'gain a LADDER_QWEN_REASONING-gated cap function'
    )
