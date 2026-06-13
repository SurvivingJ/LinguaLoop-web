"""Invariant tests for the dim_exercise_capabilities routing matrix (TASK-504).

These run fully offline against the in-code CAPABILITY_MATRIX mirror in
services.vocabulary_ladder.config (which must stay in sync with
migrations/dim_exercise_capabilities.sql). The load-bearing invariant is the §4
inventory contract: every (language_id, semantic_class) the ladder subscribes
must have >=1 enabled exercise type per required cognitive family — otherwise the
practice serving machine targets a family it cannot fill (the eval's "bean"
failure and the 小熊 incident).
"""

import pytest

from services.vocabulary_ladder.config import (
    CAPABILITY_MATRIX,
    EXERCISE_TYPE_FAMILY,
    SEMANTIC_CLASSES,
    compute_active_levels,
    enabled_capabilities,
    required_families,
)

# language_id convention: 1 = Chinese, 2 = English, 3 = Japanese
LANGUAGES = (1, 2, 3)
GENERATORS = {'deterministic', 'llm', 'hybrid'}


# ---------------------------------------------------------------------------
# Structural integrity of the matrix
# ---------------------------------------------------------------------------

def test_every_row_is_well_formed():
    seen = set()
    for cap in CAPABILITY_MATRIX:
        key = (cap['language_id'], cap['type_code'])
        assert key not in seen, f"duplicate (language, type): {key}"
        seen.add(key)
        assert cap['language_id'] in LANGUAGES
        assert cap['type_code'] in EXERCISE_TYPE_FAMILY, \
            f"{cap['type_code']} missing from EXERCISE_TYPE_FAMILY"
        assert cap['generator'] in GENERATORS
        assert isinstance(cap['pos_classes'], list) and cap['pos_classes']
        assert cap['ladder_level'] is None or 1 <= cap['ladder_level'] <= 9


def test_judge_key_null_iff_deterministic():
    """The §6.2 contract: judge_key is NULL only for deterministic generators
    (every LLM/hybrid-authored item must be judge-gated)."""
    for cap in CAPABILITY_MATRIX:
        if cap['generator'] == 'deterministic':
            assert cap['judge_key'] is None, \
                f"deterministic {cap['type_code']} should have no judge_key"
        else:
            assert cap['judge_key'] is not None, \
                f"{cap['generator']} {cap['type_code']} must have a judge_key"


def test_capability_families_consistent_with_dim_types():
    """A type's family is a property of the type, not the (lang, type) row, so it
    is identical across languages (mirror of dim_exercise_types)."""
    for cap in CAPABILITY_MATRIX:
        assert cap['type_code'] in EXERCISE_TYPE_FAMILY


# ---------------------------------------------------------------------------
# The §4 inventory contract — the core invariant
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("language_id", LANGUAGES)
@pytest.mark.parametrize("semantic_class", sorted(SEMANTIC_CLASSES))
def test_every_required_family_has_an_enabled_type(language_id, semantic_class):
    """For every (language, semantic_class), each required family (derived from
    the word's active ladder levels) is served by >=1 enabled exercise type
    whose pos_classes cover that class."""
    req = required_families(language_id, semantic_class)
    caps = enabled_capabilities(language_id, semantic_class)
    covered = {EXERCISE_TYPE_FAMILY[c['type_code']] for c in caps}
    missing = req - covered
    assert not missing, (
        f"language {language_id} / {semantic_class}: required families {sorted(missing)} "
        f"have no enabled type (active_levels={compute_active_levels(semantic_class, language_id)})"
    )


def test_proper_is_not_ladder_subscribed():
    """`proper` nouns are definition-flashcard only — no ladder levels, hence no
    required families to satisfy."""
    for lang in LANGUAGES:
        assert compute_active_levels('proper', lang) == []
        assert required_families(lang, 'proper') == set()


def test_function_words_have_no_productive_or_collocation_families():
    for lang in LANGUAGES:
        fams = required_families(lang, 'function')
        assert 'form_production' not in fams
        assert 'collocation' not in fams
        assert fams == {'form_recognition', 'meaning_recall', 'semantic_discrimination'}


# ---------------------------------------------------------------------------
# TASK-504 verification target: ZH concrete noun plan
# ---------------------------------------------------------------------------

def test_zh_concrete_has_classifier_match_l4_and_no_morphology_slot():
    """Verification (TASK-504): a ZH concrete-noun plan contains classifier_match
    at L4 and no morphology_slot (ZH is analytic — morphology_slot disabled)."""
    caps = enabled_capabilities(1, 'concrete')
    by_type = {c['type_code']: c for c in caps}

    assert 'classifier_match' in by_type, "ZH concrete must offer classifier_match"
    assert by_type['classifier_match']['ladder_level'] == 4
    assert by_type['classifier_match']['generator'] == 'deterministic'

    assert 'morphology_slot' not in by_type, \
        "morphology_slot must not be enabled for ZH (analytic language)"

    # L4 is still present in the active level set (via classifier_match / cloze_typed)
    assert 4 in compute_active_levels('concrete', 1)


def test_l4_type_differs_by_language_for_concrete():
    """L4 is form_production everywhere, but the *type* filling it is
    language-specific: ZH=classifier, JA=particle/counter, EN=morphology."""
    zh = {c['type_code'] for c in enabled_capabilities(1, 'concrete')}
    en = {c['type_code'] for c in enabled_capabilities(2, 'concrete')}
    ja = {c['type_code'] for c in enabled_capabilities(3, 'concrete')}

    assert 'classifier_match' in zh and 'morphology_slot' not in zh
    assert 'morphology_slot' in en and 'classifier_match' not in en
    assert {'particle_selection', 'counter_match'} <= ja
