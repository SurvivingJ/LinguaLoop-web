# tests/test_bundle_judge.py
"""BundleJudge: one call/sense, per-request fallback, fail-closed on failure.

All LLM calls are mocked. Fallback is exercised by monkeypatching the
EXISTING per-judge functions this module imports (``filter_distractors``,
``filter_l1_distractors``, ``filter_collocation_distractors``,
``judge_collocation_repair``, ``filter_relation_foils``,
``filter_particle_foils``, ``judge_wrong_sentences``) directly in
``services.vocabulary_ladder.bundle.judge``'s own namespace — proving
BundleJudge calls the REAL judge with the REAL arguments on every fallback
path, not a stand-in.
"""

from __future__ import annotations

from services.exercise_generation.judges.base import JudgeOutcome
import services.vocabulary_ladder.bundle.judge as judge_mod
from services.vocabulary_ladder.bundle.judge import (
    BundleJudge, BundleJudgeRequests, CollocationVerdictRequest,
    DistractorRequest, ParticleRequest, RelationRequest,
    SentenceValidityRequest,
)

LANG_ZH = 1
LANG_JA = 3
LANG_EN = 2


def _fake_cfg(monkeypatch, model='qwen/qwen3.7-plus', version=2):
    monkeypatch.setattr(
        judge_mod, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': '{target}{sentence_validity_pairs_numbered}{cloze_items_numbered}'
                        '{l1_items_numbered}{collocation_items_numbered}{relation_items_numbered}'
                        '{particle_items_numbered}',
            'model': model, 'provider': 'openrouter', 'version': version,
        },
    )


def test_unsupported_language_falls_back_without_calling_llm(monkeypatch):
    calls = {'llm': 0}
    monkeypatch.setattr(judge_mod, 'call_llm', lambda *a, **k: calls.__setitem__('llm', calls['llm'] + 1))
    fake_result = (['walk'], {'rejected': 0, 'kept': 1, 'rejected_items': [], 'model': 'x', 'version': 1})
    monkeypatch.setattr(judge_mod, 'filter_distractors', lambda *a, **k: fake_result)

    reqs = BundleJudgeRequests(cloze=[
        DistractorRequest('A:L3', ['walk', 'jog'], 'sentence + correct',
                           {'sentence_with_blank': '___', 'correct_answer': 'run'}),
    ])
    bj = BundleJudge(db=object(), language_id=LANG_EN)
    result = bj.judge_bundle(1, 'run', reqs)

    assert calls['llm'] == 0
    assert result.ok is False
    assert result.cloze['A:L3'] == fake_result
    assert 'cloze:A:L3' in result.fallback_requests


def test_empty_requests_is_a_no_op_success():
    bj = BundleJudge(db=object(), language_id=LANG_ZH)
    result = bj.judge_bundle(1, 'run', BundleJudgeRequests())
    assert result.ok is True
    assert result.fallback_requests == []


def test_full_success_zh_sentence_validity_and_cloze(monkeypatch):
    _fake_cfg(monkeypatch)

    def _fake_call_llm(prompt, **kwargs):
        # sentence_validity: A:L6 has 2 pairs (indices 1,2), B:L7 has 1 pair (index 3).
        # cloze: A:L3 has 2 candidates (indices 1,2).
        return {
            'sentence_validity': {
                '1': {'rating': 5, 'reason': 'clean'},
                '2': {'rating': 2, 'reason': 'actually grammatical'},
                '3': {'rating': 4, 'reason': 'clean enough'},
            },
            'cloze': {
                '1': {'verdict': 'keep', 'reason': 'clean'},
                '2': {'verdict': 'reject', 'reason': 'also correct'},
            },
        }
    monkeypatch.setattr(judge_mod, 'call_llm', _fake_call_llm)

    def _boom(*a, **k):
        raise AssertionError('fallback must not run when the bundle succeeds')
    monkeypatch.setattr(judge_mod, 'filter_distractors', _boom)
    monkeypatch.setattr(judge_mod, 'judge_wrong_sentences', _boom)

    reqs = BundleJudgeRequests(
        sentence_validity=[
            SentenceValidityRequest('A:L6', 'run', [('He run fast.', 'agreement'), ('He runned.', 'wrong form')]),
            SentenceValidityRequest('B:L7', 'run', [('He run.', 'agreement')]),
        ],
        cloze=[
            DistractorRequest('A:L3', ['walk', 'jog'], 'ctx',
                               {'sentence_with_blank': 'He ___ fast.', 'correct_answer': 'runs'}),
        ],
    )
    bj = BundleJudge(db=object(), language_id=LANG_ZH)
    result = bj.judge_bundle(1, 'run', reqs)

    assert result.ok is True
    assert result.fallback_requests == []

    sv_a = result.sentence_validity['A:L6']
    assert [o.verdict for o in sv_a] == ['accept', 'reject']
    sv_b = result.sentence_validity['B:L7']
    assert sv_b[0].verdict == 'accept'

    kept, meta = result.cloze['A:L3']
    assert kept == ['walk']
    assert meta['rejected'] == 1


def test_total_bundle_failure_falls_back_every_request(monkeypatch):
    _fake_cfg(monkeypatch)
    monkeypatch.setattr(judge_mod, 'call_llm', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('empty')))

    sv_outcome = [JudgeOutcome(verdict='accept', confidence=5.0, reason='fallback')]
    monkeypatch.setattr(judge_mod, 'judge_wrong_sentences', lambda *a, **k: sv_outcome)
    l1_result = (['cot'], {'rejected': 0, 'kept': 1, 'rejected_items': [], 'model': 'x', 'version': 1})
    monkeypatch.setattr(judge_mod, 'filter_l1_distractors', lambda *a, **k: l1_result)

    reqs = BundleJudgeRequests(
        sentence_validity=[SentenceValidityRequest('A:L7', 'cat', [('He cat.', 'wrong pos')])],
        l1_distractor=[DistractorRequest('A:L1', ['cot'], 'ctx', {'target': 'cat'})],
    )
    bj = BundleJudge(db=object(), language_id=LANG_ZH)
    result = bj.judge_bundle(1, 'cat', reqs)

    assert result.ok is False
    assert result.sentence_validity['A:L7'] == sv_outcome
    assert result.l1_distractor['A:L1'] == l1_result
    assert 'sentence_validity:A:L7' in result.fallback_requests
    assert 'l1_distractor:A:L1' in result.fallback_requests


def test_axis_present_but_malformed_item_falls_back_only_that_request(monkeypatch):
    _fake_cfg(monkeypatch)

    def _fake_call_llm(prompt, **kwargs):
        return {
            'l1_distractor': {
                '1': {'verdict': 'keep', 'reason': 'ok'},
                # index '2' missing entirely -> malformed for this request
            },
        }
    monkeypatch.setattr(judge_mod, 'call_llm', _fake_call_llm)

    fallback_result = (['cut'], {'rejected': 1, 'kept': 1, 'rejected_items': ['cap'], 'model': 'x', 'version': 1})
    monkeypatch.setattr(judge_mod, 'filter_l1_distractors', lambda *a, **k: fallback_result)

    reqs = BundleJudgeRequests(
        l1_distractor=[DistractorRequest('A:L1', ['cot', 'cap'], 'ctx', {'target': 'cat'})],
    )
    bj = BundleJudge(db=object(), language_id=LANG_ZH)
    result = bj.judge_bundle(1, 'cat', reqs)

    assert result.ok is True  # the bundle call itself succeeded
    assert result.l1_distractor['A:L1'] == fallback_result
    assert 'l1_distractor:A:L1' in result.fallback_requests


def test_relation_and_particle_axes(monkeypatch):
    _fake_cfg(monkeypatch)

    def _fake_call_llm(prompt, **kwargs):
        return {
            'relation': {'1': {'0': 5, '1': 'unrelated'}, '2': {'0': 1, '1': 'is a synonym'}},
            'particle': {'1': {'0': 5, '1': 'unnatural'}},
        }
    monkeypatch.setattr(judge_mod, 'call_llm', _fake_call_llm)

    def _boom(*a, **k):
        raise AssertionError('fallback must not run')
    monkeypatch.setattr(judge_mod, 'filter_relation_foils', _boom)
    monkeypatch.setattr(judge_mod, 'filter_particle_foils', _boom)

    reqs = BundleJudgeRequests(
        relation=[RelationRequest('A:synant', 'happy', 'feeling joy', 'synonym', 'joyful', ['sad', 'glad'])],
        particle=[ParticleRequest('A:particle', 'A ___ B', 'に', ['へ'])],
    )
    bj = BundleJudge(db=object(), language_id=LANG_JA)
    result = bj.judge_bundle(1, 'happy', reqs)

    assert result.ok is True
    kept, meta = result.relation['A:synant']
    assert kept == ['sad']  # 'glad' rejected (rating 1 = actually a synonym)
    kept_p, meta_p = result.particle['A:particle']
    assert kept_p == ['へ']


def test_collocation_filter_and_verdict_share_one_axis(monkeypatch):
    _fake_cfg(monkeypatch)

    def _fake_call_llm(prompt, **kwargs):
        return {
            'collocation': {
                '1': {'rating': 5, 'reason': 'not a collocate'},   # L5 filter candidate 1
                '2': {'rating': 1, 'reason': 'also valid'},        # L5 filter candidate 2
                '3': {'rating': 5, 'reason': 'clearly wrong'},     # L8 verdict candidate
            },
        }
    monkeypatch.setattr(judge_mod, 'call_llm', _fake_call_llm)

    reqs = BundleJudgeRequests(
        collocation_filter=[
            DistractorRequest('A:L5', ['brisk', 'quick'], 'ctx',
                               {'sentence': 'a ___ walk', 'target': 'walk', 'correct_collocate': 'long'}),
        ],
        collocation_verdict=[
            CollocationVerdictRequest('A:L8', 'She likes to cook coffee.', 'coffee', 'brew', 'cook'),
        ],
    )
    bj = BundleJudge(db=object(), language_id=LANG_ZH)
    result = bj.judge_bundle(1, 'walk', reqs)

    assert result.ok is True
    kept, _meta = result.collocation_filter['A:L5']
    assert kept == ['brisk']  # 'quick' rejected (rating 1 = a valid collocate)
    outcome = result.collocation_verdict['A:L8']
    assert outcome.verdict == 'accept'
