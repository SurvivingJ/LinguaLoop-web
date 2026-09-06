"""Guards on the per-language Prompt-1 validation profiles.

The bug these exist to prevent: the ja profile was registered but declared
``pos_set=DEFAULT_POS_SET`` (the merged EN+ZH set), so a Japanese word could be
tagged with a *Simplified Chinese* POS label and pass validation. It did — the
ja P1 prompt left key "1" unenumerated, qwen emitted 名词, and the gate waved it
through. A profile that silently accepts another language's tagset is
indistinguishable from no profile at all, which is why the first test below
asserts every registered language declares its own set.
"""

import os

import pytest

from services.vocabulary_ladder.config import (
    DEFAULT_POS_SET,
    LANGUAGE_VALIDATION_PROFILES,
    SEMANTIC_CLASSES,
    _POS_EN,
    _POS_JA,
    _POS_ZH,
    get_validation_profile,
)

LANG_CODE = {1: 'zh', 2: 'en', 3: 'ja'}


@pytest.mark.parametrize('language_id', sorted(LANGUAGE_VALIDATION_PROFILES))
def test_registered_profile_declares_its_own_pos_set(language_id):
    """A registered language must not fall back to the merged default set.

    DEFAULT_POS_SET is the deliberate landing place for an *unconfigured*
    language onboarding. A configured one sitting on it is the ja bug.
    """
    profile = LANGUAGE_VALIDATION_PROFILES[language_id]
    assert profile.pos_set is not DEFAULT_POS_SET, (
        f"{LANG_CODE.get(language_id, language_id)} declares the merged "
        f"EN+ZH default POS set, so it accepts other languages' tagsets"
    )
    assert profile.pos_set, "pos_set must be non-empty"


@pytest.mark.parametrize('language_id', sorted(LANGUAGE_VALIDATION_PROFILES))
def test_semantic_class_set_is_the_ratified_enum(language_id):
    """semantic_class is language-neutral and CHECK-constrained in the DB."""
    assert LANGUAGE_VALIDATION_PROFILES[language_id].semantic_class_set == SEMANTIC_CLASSES


def test_ja_and_zh_pos_sets_are_disjoint():
    """The exact confusion that shipped: 名词 (zh) accepted for a ja word.

    Japanese and Simplified Chinese POS labels are visually close and
    semantically parallel, so an overlap here is not a harmless union — it is
    the gate failing to tell the two languages apart.
    """
    overlap = _POS_JA & _POS_ZH
    assert not overlap, f"ja and zh POS sets overlap: {sorted(overlap)}"


def test_ja_pos_set_is_japanese_script():
    """No Simplified-only forms; UniDic's 形状詞 present."""
    for token in ('名词', '动词', '形容词'):
        assert token not in _POS_JA, f"Simplified form {token} leaked into _POS_JA"
    for token in ('名詞', '動詞', '形容詞', '形状詞'):
        assert token in _POS_JA, f"expected UniDic token {token} in _POS_JA"


def test_en_pos_set_is_unchanged_by_this_fix():
    """en/zh were out of scope — this pins them so the fix stayed narrow."""
    assert 'noun' in _POS_EN and '名词' in _POS_ZH


def test_unconfigured_language_still_gets_the_permissive_default():
    """Onboarding a new language must not require touching the validator."""
    profile = get_validation_profile(99)
    assert profile.pos_set is DEFAULT_POS_SET


@pytest.mark.skipif(
    not os.environ.get('SUPABASE_URL'),
    reason='needs Supabase credentials; the prompt row is the source of truth',
)
def test_ja_p1_prompt_enumerates_exactly_the_profile_pos_set():
    """The prompt and the gate must agree, or ja generation fails outright.

    Nothing else couples them: the prompt lives in prompt_templates and the
    enum lives in code, and the failure mode when they drift is a 100% P1
    rejection rate for the language — loud, but only once someone runs a batch.
    """
    from services.prompt_service import get_template_text
    from services.supabase_factory import SupabaseFactory, get_supabase_admin

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()

    template = get_template_text(get_supabase_admin(), 'vocab_prompt1_core', 3)

    missing = [tok for tok in _POS_JA if tok not in template]
    assert not missing, (
        f"ja P1 prompt does not offer POS token(s) {sorted(missing)} that the "
        f"validator accepts — apply migrations/ja_p1_pos_enum_unidic.sql"
    )
    assert '品詞（文字列）' not in template, (
        'ja P1 prompt still has the unenumerated 品詞（文字列） schema line — '
        'apply migrations/ja_p1_pos_enum_unidic.sql'
    )
