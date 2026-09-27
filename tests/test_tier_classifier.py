"""services.tier_classifier + the jev-backed TierFitJudge (ADR-029).

The probability -> tier -> difficulty mapping, the native-language prompts,
and the no-fallback failure behaviour. No network.
"""

import re
from types import SimpleNamespace

import pytest

from services import tier_classifier as tc
from services.categorical_maps import DIFFICULTY_TO_TIER, TIER_DISPLAY_NAMES
from services.jev_client import JevError
from services.tier_classifier import (
    TIER_ID_TO_DIFFICULTY, TierAssessment, assessment_from_answers,
    build_passage_request, build_topic_request, classify_passage,
    classify_topic, difficulty_for_tier, tier_from_score,
)
from services.topic_generation.agents.tier_fit_judge import TierFitJudge

LATIN = re.compile(r'[A-Za-z]')
CJK = re.compile(r'[぀-ヿ一-鿿]')


def score_answer(score, probs=None, confidence=0.8):
    return {'tier': {
        'type': 'score', 'score': score, 'confidence': confidence,
        'probabilities': probs or {}, 'legend': {},
    }}


# ── probability -> tier ─────────────────────────────────────────────────────

@pytest.mark.parametrize('score,tier', [
    (0.0, 1), (0.49, 1), (0.5, 2), (1.0, 2), (1.49, 2), (1.5, 3),
    (2.99, 4), (3.5, 5), (4.49, 5), (4.5, 6), (5.0, 6),
])
def test_default_table_rounds_half_up_to_a_tier(score, tier):
    assert tier_from_score(score) == tier
    assert tier_from_score(score, 'en') == tier   # en measured: no table beat this


@pytest.mark.parametrize('score', [-0.4, 5.4])
def test_out_of_range_scores_are_clamped(score):
    assert tier_from_score(score) in (1, 6)


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), None, True])
def test_unusable_score_is_an_error_not_a_default(bad):
    with pytest.raises(JevError):
        tier_from_score(bad)
    with pytest.raises(JevError):
        tier_from_score(bad, 'ja')


# ── per-language calibration (ADR-029 recalibration) ─────────────────────────

@pytest.mark.parametrize('score,tier', [
    (0.0, 1), (0.94, 1), (0.95, 2), (2.64, 2), (2.65, 3), (3.24, 3),
    (3.25, 4), (4.19, 4), (4.2, 5), (4.39, 5), (4.4, 6), (5.0, 6),
])
def test_ja_uses_its_fitted_thresholds(score, tier):
    assert tier_from_score(score, 'ja') == tier


def test_every_table_is_five_ascending_cuts_inside_the_scale():
    for lang, cuts in {**tc.SCORE_THRESHOLDS, 'default': tc.DEFAULT_THRESHOLDS}.items():
        assert len(cuts) == tc.N_TIERS - 1, lang
        assert list(cuts) == sorted(set(cuts)), lang
        assert 0 <= cuts[0] and cuts[-1] <= tc.N_TIERS - 1, lang


def test_every_calibrated_language_has_a_label_and_the_rest_are_default():
    assert set(tc.CALIBRATION_LABELS) == set(tc.SCORE_THRESHOLDS)
    assert tc.calibration_for('ja') == 'ja-2026-09-27'
    assert tc.calibration_for('zh') == 'zh-2026-09-27'
    assert tc.calibration_for('en') == tc.calibration_for(None) == 'default'
    assert tc.thresholds_for('en') == tc.DEFAULT_THRESHOLDS   # measured: no gain


@pytest.mark.parametrize('lang,n_items,min_hits,min_gain', [
    ('ja', 59, 55, 12),   # 57 fitted; 38 under round-half-up
    ('zh', 60, 51, 6),    # 53 fitted; 44 under round-half-up
])
def test_calibration_still_matches_the_blind_gold_set(lang, n_items, min_hits, min_gain):
    """Passages labelled blind by two readers (tests/fixtures). Editing a table
    must not silently lose the fit that justified it."""
    import json
    import os
    path = os.path.join(os.path.dirname(__file__), 'fixtures',
                        f'{lang}_tier_calibration_gold.json')
    with open(path, encoding='utf-8') as fh:
        gold = json.load(fh)
    assert len(gold) == n_items

    def hits(code):
        return sum(tier_from_score(g['score'], code) in g['gold'] for g in gold)

    assert hits(lang) >= min_hits
    assert hits(lang) >= hits(None) + min_gain


def test_assessment_records_which_table_made_the_tier():
    a = assessment_from_answers(score_answer(3.5), model='m', language_code='ja')
    assert a.tier == 4 and a.calibration == 'ja-2026-09-27'      # 3.5 >= 3.25
    b = assessment_from_answers(score_answer(3.5), model='m', language_code='en')
    assert b.tier == 5 and b.calibration == 'default'
    # the raw score is what is kept, so either tier can be re-derived
    assert a.score == b.score == pytest.approx(3.5)


def test_assessment_carries_probabilities_and_confidence():
    a = assessment_from_answers(
        score_answer(1.6, {'1': 0.3, '2': 0.7}, 0.72),
        model='typesafe/jev-1.13-x', cost_usd=0.00005,
    )
    assert a.tier == 3 and a.code == 'T3'
    assert a.score == pytest.approx(1.6) and a.expected_tier == pytest.approx(2.6)
    assert a.confidence == pytest.approx(0.72)
    assert a.probabilities == {1: 0.0, 2: 0.3, 3: 0.7, 4: 0.0, 5: 0.0, 6: 0.0}
    assert a.model == 'typesafe/jev-1.13-x' and a.cost_usd == 0.00005


def test_assessment_tolerates_missing_confidence():
    answers = score_answer(0.1)
    del answers['tier']['confidence']
    assert assessment_from_answers(answers, model='m').confidence is None


@pytest.mark.parametrize('answers', [
    {}, {'tier': {'type': 'choice', 'choice': 'T2'}},
    {'tier': {'type': 'score'}}, {'tier': {'type': 'score', 'score': 'high'}},
    None,
])
def test_malformed_answers_raise(answers):
    with pytest.raises(JevError):
        assessment_from_answers(answers, model='m')


# ── tier -> difficulty ──────────────────────────────────────────────────────

def test_difficulty_is_the_bottom_of_each_tier_band():
    assert TIER_ID_TO_DIFFICULTY == {1: 1, 2: 3, 3: 5, 4: 6, 5: 7, 6: 8}
    assert difficulty_for_tier(4) == 6


def test_difficulty_round_trips_through_the_tier_map():
    for tier_id, difficulty in TIER_ID_TO_DIFFICULTY.items():
        assert DIFFICULTY_TO_TIER[difficulty] == f'T{tier_id}'


def test_d4_is_t2_everywhere():
    """The two-numberings regression: d4 is T2, so T2's difficulty (3) and
    d4 both land in T2 and never in T3."""
    assert DIFFICULTY_TO_TIER[4] == 'T2'
    assert difficulty_for_tier(2) in (3, 4)


# ── prompts ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize('lang,key', [('zh', '文章'), ('ja', '文章')])
def test_cjk_prompts_are_entirely_in_the_content_language(lang, key):
    state, questions = build_passage_request(lang, '本文')
    q = questions['tier']
    assert list(state) == [key]
    assert q['type'] == 'score'
    assert not LATIN.search(q['instructions'])
    assert len(q['criteria']) == 6
    for text in q['criteria']:
        assert not LATIN.search(text), text
        assert '：' in text


def test_english_prompt_is_entirely_english():
    state, questions = build_passage_request('en', 'A red ball.')
    q = questions['tier']
    assert list(state) == ['passage']
    assert not CJK.search(q['instructions'])
    assert not any(CJK.search(c) for c in q['criteria'])
    assert q['criteria'][0].startswith('The Toddler (Age 4-5): ')


@pytest.mark.parametrize('lang', ['zh', 'en', 'ja'])
def test_criteria_are_ordered_t1_to_t6_with_native_display_names(lang):
    lang_id = tc.LANG_IDS[lang]
    _, questions = build_passage_request(lang, 'x')
    for i, text in enumerate(questions['tier']['criteria']):
        assert text.startswith(TIER_DISPLAY_NAMES[f'T{i + 1}'][lang_id])


def test_topic_prompt_is_english_whatever_the_study_language():
    state, questions = build_topic_request('Rivers', 'delta, tributary')
    assert state == {'topic': 'Rivers', 'distinctive vocabulary': 'delta, tributary'}
    assert not any(CJK.search(c) for c in questions['tier']['criteria'])
    assert 'distinctive vocabulary' in questions['tier']['instructions']
    assert 'distinctive vocabulary' not in build_topic_request('Rivers')[0]


def test_unsupported_language_is_rejected():
    with pytest.raises(ValueError):
        build_passage_request('fr', 'bonjour')


def test_overlong_passage_is_truncated_not_dropped(caplog):
    state, _ = build_passage_request('en', 'a' * (tc.MAX_PASSAGE_CHARS + 500))
    assert len(state['passage']) == tc.MAX_PASSAGE_CHARS
    assert 'truncated' in caplog.text


# ── classify_* wiring ───────────────────────────────────────────────────────

def test_classify_passage_calls_jev_and_maps_the_score(monkeypatch):
    seen = {}

    def fake_decide(state, questions, **kw):
        seen.update(state=state, questions=questions, **kw)
        return SimpleNamespace(
            answers=score_answer(3.4, {'3': 0.6, '4': 0.4}),
            model='typesafe/jev-1.13-x', cost_usd=0.00006,
        )

    monkeypatch.setattr(tc.jev_client, 'call_jev', fake_decide)
    a = classify_passage('今日は天気がいいです。', 'ja')
    assert a.tier == 4 and a.cost_usd == 0.00006
    assert seen['task_name'] == 'jev_tier_passage'
    assert seen['language_code'] == 'ja'
    assert seen['summarize'](score_answer(3.4)) == ('T4', 0.8)
    assert a.calibration == 'ja-2026-09-27'


def test_classify_topic_logs_under_its_own_task_name(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        tc.jev_client, 'call_jev',
        lambda s, q, **kw: seen.update(kw) or SimpleNamespace(
            answers=score_answer(0.0), model='m', cost_usd=None),
    )
    assert classify_topic('A red ball').tier == 1
    assert seen['task_name'] == 'jev_tier_topic'


def test_jev_failure_propagates_from_classify(monkeypatch):
    def boom(*a, **kw):
        raise JevError('gave up', status=503)

    monkeypatch.setattr(tc.jev_client, 'call_jev', boom)
    with pytest.raises(JevError):
        classify_passage('hello', 'en')
    with pytest.raises(JevError):
        classify_topic('hello')


@pytest.mark.parametrize('empty', ['', '   \n'])
def test_empty_input_is_rejected_before_any_call(monkeypatch, empty):
    monkeypatch.setattr(tc.jev_client, 'call_jev', lambda *a, **k: 1 / 0)
    with pytest.raises(ValueError):
        classify_passage(empty, 'en')
    with pytest.raises(ValueError):
        classify_topic(empty)


# ── TierFitJudge ────────────────────────────────────────────────────────────

def _assessment(tier, conf=0.9):
    return TierAssessment(
        tier=tier, expected_tier=float(tier), score=tier - 1.0,
        confidence=conf, probabilities={t: 0.0 for t in range(1, 7)},
        model='m', cost_usd=None,
    )


def test_topic_fits_when_assessed_at_or_below_its_tier():
    judge = TierFitJudge(classify=lambda c, v: _assessment(2))
    assert judge.judge('Bees', ['hive'], tier=2).fits
    assert judge.judge('Bees', ['hive'], tier=5).fits


def test_topic_is_rejected_when_assessed_harder_than_its_tier():
    judge = TierFitJudge(classify=lambda c, v: _assessment(4))
    verdict = judge.judge('Bees', ['hive'], tier=2)
    assert not verdict.fits
    assert 'T4' in verdict.reason and 'T2' in verdict.reason
    assert verdict.assessment.tier == 4


def test_judge_flattens_the_vocabulary_blob():
    seen = []
    judge = TierFitJudge(classify=lambda c, v: seen.append((c, v)) or _assessment(1))
    judge.judge('Bees', {'en': ['hive', 'honey'], 'note': 'x'}, tier=1)
    judge.judge('Bees', None, tier=1)
    assert seen == [('Bees', 'hive, honey, x'), ('Bees', '')]


def test_jev_failure_does_not_fail_open():
    """The old judge returned fits=True (unjudged) on any error."""
    def boom(c, v):
        raise JevError('down', status=503)

    with pytest.raises(JevError):
        TierFitJudge(classify=boom).judge('Bees', ['hive'], tier=3)


def test_unknown_tier_is_rejected():
    judge = TierFitJudge(classify=lambda c, v: _assessment(1))
    for bad in (0, 7):
        with pytest.raises(ValueError):
            judge.judge('Bees', ['hive'], tier=bad)


def test_the_old_chat_model_tier_path_is_gone():
    import services.topic_generation.agents.tier_fit_judge as mod
    assert not hasattr(mod, 'TIER_READERS')
    assert not hasattr(TierFitJudge, 'best_tier')
    src = open(mod.__file__, encoding='utf-8').read()
    assert 'call_llm' not in src
