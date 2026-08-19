"""TASK-524 — the sentence-tier hard gate.

The eval failure this exists for: a C2-lexis sentence shipped as the example
for an A1 word. The gate is a deterministic frequency-band screen that runs
*before* the (paid) P1 sentence judge, so obvious tier misfits cost nothing
to reject.

Nothing here touches an LLM, Supabase, or a spaCy/fugashi model — wordfreq's
own tokeniser and frequency tables are the only inputs, which is the reason
the gate uses them.

Sections:
  - tier derivation from a lemma's own frequency
  - tokenisation, per language
  - the screen itself, including the coffee-corpus fixture in all 3 languages
  - pipeline wiring: index stability and repair accounting
"""

import pytest

from services.vocabulary_ladder import tier_gate
from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
from services.vocabulary_ladder.config import TIER_GATE_PROFILES
from services.vocabulary_ladder.tier_gate import (
    TierVerdict,
    morph_form_texts,
    screen_sentence,
    screen_sentences,
    tier_for_lemma,
    tier_for_zipf,
    tokenize,
)

LANG_ZH, LANG_EN, LANG_JA = 1, 2, 3


# ---------------------------------------------------------------------------
# The eval fixture — one A1/A2 word, one ordinary sentence, one C2 sentence
# ---------------------------------------------------------------------------

COFFEE_CORPUS = {
    LANG_EN: {
        'lemma': 'coffee',
        'ok': 'I drink coffee every morning before work.',
        'c2': ("The barista's meticulous extraction protocol yielded an "
               "exceptionally nuanced espresso with discernible bergamot "
               "undertones."),
    },
    LANG_ZH: {
        'lemma': '咖啡',
        'ok': '我每天早上都喝一杯咖啡。',
        'c2': '这家咖啡馆的萃取工艺极其考究，风味层次繁复而隽永。',
    },
    LANG_JA: {
        'lemma': 'コーヒー',
        'ok': '毎朝コーヒーを飲みます。',
        'c2': '当該焙煎所の抽出工程は極めて精緻で、繊細な芳香が顕著に感得される。',
    },
}


# ---------------------------------------------------------------------------
# Tier derivation
# ---------------------------------------------------------------------------

def test_tier_for_zipf_is_monotonic():
    """Rarer lemma → same or higher (harder) tier. Never the reverse."""
    tiers = [tier_for_zipf(z) for z in (7.0, 5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 1.0)]
    order = {f'T{i}': i for i in range(1, 7)}
    assert tiers == sorted(tiers, key=order.__getitem__)


def test_common_word_lands_in_a_low_tier():
    assert tier_for_lemma('coffee', LANG_EN) in ('T1', 'T2')
    assert tier_for_lemma('water', LANG_EN) in ('T1', 'T2')


def test_rare_word_lands_in_a_high_tier():
    assert tier_for_lemma('bergamot', LANG_EN) in ('T5', 'T6')


def test_unknown_lemma_falls_back_rather_than_guessing():
    assert tier_for_lemma('zzqqxlemma', LANG_EN) == 'T3'
    assert tier_for_lemma('', LANG_EN) == 'T3'


def test_unsupported_language_falls_back():
    assert tier_for_lemma('anything', 99) == 'T3'


# ---------------------------------------------------------------------------
# Tokenisation — per-language correctness (AC)
# ---------------------------------------------------------------------------

def test_english_tokenisation_splits_words_and_drops_punctuation():
    tokens = tokenize('I drink coffee every morning, before work.', LANG_EN)
    assert 'coffee' in tokens
    assert 'morning' in tokens
    assert not [t for t in tokens if t in {',', '.'}]


def test_chinese_tokenisation_segments_without_spaces():
    """No `\\b` anywhere: ZH has no word delimiters to split on."""
    tokens = tokenize('我每天早上都喝一杯咖啡。', LANG_ZH)
    assert '咖啡' in tokens
    assert '每天' in tokens
    assert '。' not in tokens
    assert len(tokens) > 1, 'the sentence must not come back as one blob'


def test_japanese_tokenisation_segments_mixed_scripts():
    tokens = tokenize('毎朝コーヒーを飲みます。', LANG_JA)
    assert 'コーヒー' in tokens              # katakana
    assert 'を' in tokens                    # hiragana particle
    assert '。' not in tokens


def test_tokenise_is_safe_on_empty_and_unsupported_input():
    assert tokenize('', LANG_EN) == []
    assert tokenize('hello', 99) == []


# ---------------------------------------------------------------------------
# The screen — the headline AC
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('language_id', [LANG_EN, LANG_ZH, LANG_JA])
def test_c2_sentence_is_rejected_for_an_a1_sense(language_id):
    """AC: 'the coffee-corpus C2 example is rejected for an A1 sense'."""
    case = COFFEE_CORPUS[language_id]
    tier = tier_for_lemma(case['lemma'], language_id)

    verdict = screen_sentence(
        case['c2'], language_id, tier, target_word=case['lemma'],
    )

    assert verdict.passed is False, verdict
    assert verdict.reason, 'a rejection must say why — it feeds the repair prompt'
    assert verdict.out_of_band, 'rejection must name the offending words'


@pytest.mark.parametrize('language_id', [LANG_EN, LANG_ZH, LANG_JA])
def test_ordinary_sentence_passes_for_the_same_sense(language_id):
    """The other half of the AC: the gate must not simply reject everything."""
    case = COFFEE_CORPUS[language_id]
    tier = tier_for_lemma(case['lemma'], language_id)

    verdict = screen_sentence(
        case['ok'], language_id, tier, target_word=case['lemma'],
    )

    assert verdict.passed is True, verdict.reason


def test_a_single_very_rare_word_rejects_on_its_own():
    """The hard floor: budget-based tolerance must not let 'bergamot' through."""
    verdict = screen_sentence(
        'I like bergamot.', LANG_EN, 'T1', target_word='like',
    )

    assert verdict.passed is False
    assert any(w == 'bergamot' for w, _ in verdict.too_rare)
    assert 'far above tier' in verdict.reason


def test_one_slightly_advanced_word_is_within_budget():
    """A T1 sentence gets a small allowance — otherwise nothing survives."""
    verdict = screen_sentence(
        'The cafe attracted commuters every morning.', LANG_EN, 'T1',
        target_word='cafe',
    )

    assert verdict.passed is True
    assert verdict.out_of_band, 'the advanced word should still be recorded'


def test_the_target_word_never_counts_against_its_own_sentence():
    """A rare sense being taught cannot be the reason its example is rejected."""
    sentence = 'The bergamot grew slowly in the warm garden.'

    without = screen_sentence(sentence, LANG_EN, 'T1')
    with_target = screen_sentence(sentence, LANG_EN, 'T1', target_word='bergamot')

    assert without.passed is False
    assert with_target.passed is True


def test_morphological_forms_are_exempt_too():
    forms = morph_form_texts({'morphological_forms': [
        {'form': 'bergamots', 'label': 'plural'},
    ]})
    verdict = screen_sentence(
        'She counted the bergamots in the warm garden.', LANG_EN, 'T1',
        target_word='bergamot', exempt=forms,
    )

    assert verdict.passed is True


def test_morph_form_texts_handles_both_shapes_and_junk():
    assert morph_form_texts({'morphological_forms': ['ran', 'runs']}) == ['ran', 'runs']
    assert morph_form_texts({'morphological_forms': [{'form': 'ran'}]}) == ['ran']
    assert morph_form_texts({'morphological_forms': [{}, None]}) == []
    assert morph_form_texts({}) == []
    assert morph_form_texts(None) == []


def test_t6_is_ungated():
    """At the top tier there is no such thing as lexis that is too hard."""
    case = COFFEE_CORPUS[LANG_EN]
    assert screen_sentence(case['c2'], LANG_EN, 'T6').passed is True


def test_unrecognised_tier_falls_back_instead_of_rejecting_everything():
    verdict = screen_sentence('I drink coffee.', LANG_EN, 'NOT_A_TIER')
    assert verdict.passed is True


def test_gate_fails_open_on_input_it_cannot_judge():
    assert screen_sentence('', LANG_EN, 'T1').passed is True
    assert screen_sentence('Hello there.', 99, 'T1').passed is True
    assert screen_sentence('12345 67', LANG_EN, 'T1').passed is True


def test_unknown_token_budget_rejects_a_wall_of_nonsense():
    verdict = screen_sentence(
        'Qxzv frplt mwgnk bshtr vldqp zkmft.', LANG_EN, 'T1',
    )

    assert verdict.passed is False
    assert len(verdict.unknown) >= 4


def test_every_profile_is_internally_consistent():
    """Guards the threshold table against an edit that inverts a floor."""
    for tier, prof in TIER_GATE_PROFILES.items():
        assert prof['hard_floor'] <= prof['soft_floor'], tier
        assert prof['max_out_of_band'] >= 0, tier
        assert prof['max_unknown'] >= 0, tier


# ---------------------------------------------------------------------------
# screen_sentences — index alignment
# ---------------------------------------------------------------------------

def test_screen_sentences_preserves_length_and_order():
    case = COFFEE_CORPUS[LANG_EN]
    sentences = [
        {'text': case['ok'], 'target_word': 'coffee'},
        {'text': case['c2'], 'target_word': 'coffee'},
        {'text': 'I bought coffee at the shop.', 'target_word': 'coffee'},
    ]

    verdicts = screen_sentences(sentences, LANG_EN, 'T2')

    assert len(verdicts) == 3
    assert [v.passed for v in verdicts] == [True, False, True]


def test_screen_sentences_accepts_bare_strings():
    verdicts = screen_sentences(
        ['I drink coffee.', COFFEE_CORPUS[LANG_EN]['c2']], LANG_EN, 'T2',
    )
    assert [v.passed for v in verdicts] == [True, False]


# Everything here except the target itself is high-frequency, so the only
# thing that can decide pass/fail is whether the target got exempted.
_TARGET_ONLY_RARE = 'The bergamot was very good.'


def test_screen_sentences_prefers_the_per_sentence_target():
    sentences = [{'text': _TARGET_ONLY_RARE, 'target_word': 'bergamot'}]

    assert screen_sentences(sentences, LANG_EN, 'T1', target_word='other')[0].passed
    # ...and the same sentence fails when nothing exempts it, so the assertion
    # above is really testing the exemption rather than an easy sentence.
    assert not screen_sentences([_TARGET_ONLY_RARE], LANG_EN, 'T1')[0].passed


def test_screen_sentences_reads_the_legacy_target_key():
    sentences = [{'text': _TARGET_ONLY_RARE, 'target_substring': 'bergamot'}]
    assert screen_sentences(sentences, LANG_EN, 'T1')[0].passed


def test_screen_sentences_handles_empty_input():
    assert screen_sentences([], LANG_EN, 'T1') == []
    assert screen_sentences(None, LANG_EN, 'T1') == []


# ---------------------------------------------------------------------------
# Pipeline wiring
# ---------------------------------------------------------------------------

class _StubP1Gen:
    """Stands in for CoreAssetGenerator.repair_sentences."""

    def __init__(self, replacements=None):
        self.replacements = replacements or {}
        self.calls: list[tuple[list[int], dict]] = []

    def repair_sentences(self, core_asset, bad_indices, reasons, sense_id):
        self.calls.append((list(bad_indices), dict(reasons)))
        return {i: self.replacements[i] for i in bad_indices
                if i in self.replacements} or None


def _pipeline():
    return VocabAssetPipeline.__new__(VocabAssetPipeline)


def _core(texts):
    return {
        'definition': 'a hot drink',
        'morphological_forms': [],
        'sentences': [{'text': t, 'target_word': 'coffee',
                       'source': 'generated', 'complexity_tier': 'T2'}
                      for t in texts],
    }


def test_pipeline_gate_repairs_an_off_tier_sentence_in_place():
    case = COFFEE_CORPUS[LANG_EN]
    core = _core([case['ok'], case['c2'], 'I bought coffee at the shop.'])
    p1 = _StubP1Gen({1: 'She made coffee for everyone.'})

    warnings, stats = _pipeline()._tier_gate_sentences(core, LANG_EN, p1, 7)

    assert stats['rejected'] == 1
    assert stats['repaired'] == 1
    assert stats['still_failing'] == 0
    assert warnings == []
    assert core['sentences'][1]['text'] == 'She made coffee for everyone.'
    assert len(core['sentences']) == 3, 'count and order must be untouched'


def test_pipeline_gate_reports_a_repair_that_is_still_off_tier():
    """A repair landing another C2 sentence must not be counted as a success."""
    case = COFFEE_CORPUS[LANG_EN]
    core = _core([case['ok'], case['c2']])
    p1 = _StubP1Gen({1: 'The sommelier extolled its ineffable bergamot bouquet.'})

    warnings, stats = _pipeline()._tier_gate_sentences(core, LANG_EN, p1, 7)

    assert stats['repaired'] == 0
    assert stats['still_failing'] == 1
    assert warnings and 'sentence[1]' in warnings[0]


def test_pipeline_gate_is_silent_when_everything_is_in_band():
    core = _core(['I drink coffee.', 'She likes coffee too.'])
    p1 = _StubP1Gen()

    warnings, stats = _pipeline()._tier_gate_sentences(core, LANG_EN, p1, 7)

    assert warnings == []
    assert stats['rejected'] == 0
    assert p1.calls == [], 'no repair spend when nothing is wrong'


def test_pipeline_gate_passes_a_usable_reason_to_the_repair_prompt():
    case = COFFEE_CORPUS[LANG_EN]
    core = _core([case['ok'], case['c2']])
    p1 = _StubP1Gen()

    _pipeline()._tier_gate_sentences(core, LANG_EN, p1, 7)

    (indices, reasons), = p1.calls
    assert indices == [1]
    assert 'lexically too advanced' in reasons[1]


def test_pipeline_gate_survives_a_failed_repair_call():
    case = COFFEE_CORPUS[LANG_EN]
    core = _core([case['c2']])
    p1 = _StubP1Gen()                     # returns None

    warnings, stats = _pipeline()._tier_gate_sentences(core, LANG_EN, p1, 7)

    assert stats['still_failing'] == 1
    assert core['sentences'][0]['text'] == case['c2'], 'left as-is, not blanked'
    assert warnings


def test_pipeline_gate_is_a_no_op_without_sentences():
    warnings, stats = _pipeline()._tier_gate_sentences({}, LANG_EN, _StubP1Gen(), 7)

    assert warnings == []
    assert stats['screened'] == 0
    assert stats['tier'] is None


def test_pipeline_gate_records_the_tier_it_used():
    core = _core(['I drink coffee.'])
    _, stats = _pipeline()._tier_gate_sentences(core, LANG_EN, _StubP1Gen(), 7)

    assert stats['tier'] in TIER_GATE_PROFILES


def test_verdict_is_immutable():
    """Verdicts get stashed in warnings/report structures; keep them frozen."""
    v = TierVerdict(passed=True, tier='T1')
    with pytest.raises(Exception):
        v.passed = False


def test_module_exposes_a_stable_surface():
    """The batch report (TASK-517) imports these by name."""
    for name in ('screen_sentence', 'screen_sentences', 'tier_for_lemma',
                 'tier_for_zipf', 'tokenize', 'morph_form_texts', 'TierVerdict'):
        assert hasattr(tier_gate, name), name
