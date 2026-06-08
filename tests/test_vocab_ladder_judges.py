"""Unit tests for the vocabulary-ladder judge layer (Phase 4).

LLM-free: every test mocks the judge module's ``get_template_config`` /
``call_llm`` boundary (or the ``judge_p1_sentences`` entry point for the
pipeline-wiring tests). Nothing here touches Supabase or OpenRouter.

Sections:
  - P1 sentence judge (TASK-402): rating parse + fail-open contract.
  - P1 pipeline wiring (TASK-404): index stability + block threshold.
"""

import pytest

from services.exercise_generation.judges import p1_sentences as p1mod
from services.exercise_generation.judges import l1_distractor as l1mod
from services.exercise_generation.judges import collocation as collocmod
from services.exercise_generation.judges import sentence_validity as svmod
from services.exercise_generation.judges.base import JudgeOutcome


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_TEMPLATE = (
    "word={lemma} def={definition} fp={sense_fingerprint} "
    "reg={register}\n{sentences_numbered}"
)


@pytest.fixture(autouse=True)
def _clear_cfg_cache():
    """The judges cache cfg per language_id; clear them around every test."""
    p1mod._cfg_cache.clear()
    l1mod._cfg_cache.clear()
    collocmod._cfg_cache.clear()
    svmod._cfg_cache.clear()
    yield
    p1mod._cfg_cache.clear()
    l1mod._cfg_cache.clear()
    collocmod._cfg_cache.clear()
    svmod._cfg_cache.clear()


def _patch_cfg(monkeypatch, template=_TEMPLATE):
    monkeypatch.setattr(
        p1mod, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': template, 'model': 'test-model',
            'provider': 'openrouter', 'version': 1,
        },
    )
    # log_judge_verdict writes to the DB best-effort; stub it out.
    monkeypatch.setattr(p1mod, 'log_judge_verdict', lambda **kw: None)


# ---------------------------------------------------------------------------
# P1 sentence judge — parsing
# ---------------------------------------------------------------------------

def test_p1_judge_parses_ratings(monkeypatch):
    _patch_cfg(monkeypatch)
    monkeypatch.setattr(p1mod, 'call_llm', lambda *a, **k: {
        '1': {'rating': 5, 'reason': 'clean'},
        '2': {'rating': 2, 'reason': 'sense: wrong homonym'},
        '3': {'rating': 3, 'reason': 'borderline register'},
    })
    out = p1mod.judge_p1_sentences(
        db=None, lemma='bank', definition='financial institution',
        sense_fingerprint='bank:money', register='neutral',
        sentences=['a', 'b', 'c'], language_id=2,
    )
    assert [o.verdict for o in out] == ['accept', 'reject', 'flag']
    assert [o.confidence for o in out] == [5.0, 2.0, 3.0]
    assert out[1].reason.startswith('sense')


def test_p1_judge_empty_sentences_returns_empty(monkeypatch):
    _patch_cfg(monkeypatch)
    assert p1mod.judge_p1_sentences(
        db=None, lemma='x', definition='', sense_fingerprint='',
        register='neutral', sentences=[], language_id=2,
    ) == []


def test_p1_judge_missing_entry_safe_accepts_that_sentence(monkeypatch):
    _patch_cfg(monkeypatch)
    monkeypatch.setattr(p1mod, 'call_llm', lambda *a, **k: {
        '1': {'rating': 2, 'reason': 'bad'},
        # key "2" absent → that sentence must safe-accept, never reject.
    })
    out = p1mod.judge_p1_sentences(
        db=None, lemma='x', definition='', sense_fingerprint='',
        register='neutral', sentences=['a', 'b'], language_id=2,
    )
    assert len(out) == 2
    assert out[0].verdict == 'reject'
    assert out[1].verdict == 'accept'


def test_p1_judge_unparseable_rating_safe_accepts(monkeypatch):
    _patch_cfg(monkeypatch)
    monkeypatch.setattr(p1mod, 'call_llm', lambda *a, **k: {
        '1': {'rating': 'not-a-number', 'reason': 'x'},
    })
    out = p1mod.judge_p1_sentences(
        db=None, lemma='x', definition='', sense_fingerprint='',
        register='neutral', sentences=['a'], language_id=2,
    )
    assert out[0].verdict == 'accept'


# ---------------------------------------------------------------------------
# P1 sentence judge — fail-open contract
# ---------------------------------------------------------------------------

def test_p1_judge_template_missing_safe_accepts_all(monkeypatch):
    def _boom(db, task_name, language_id):
        raise RuntimeError('no active prompt row')
    monkeypatch.setattr(p1mod, 'get_template_config', _boom)
    out = p1mod.judge_p1_sentences(
        db=None, lemma='x', definition='', sense_fingerprint='',
        register='neutral', sentences=['a', 'b', 'c'], language_id=2,
    )
    assert len(out) == 3
    assert all(o.verdict == 'accept' for o in out)


def test_p1_judge_llm_error_safe_accepts_all(monkeypatch):
    _patch_cfg(monkeypatch)

    def _boom(*a, **k):
        raise RuntimeError('llm down')
    monkeypatch.setattr(p1mod, 'call_llm', _boom)
    out = p1mod.judge_p1_sentences(
        db=None, lemma='x', definition='', sense_fingerprint='',
        register='neutral', sentences=['a', 'b'], language_id=2,
    )
    assert len(out) == 2 and all(o.verdict == 'accept' for o in out)


def test_p1_judge_non_dict_response_safe_accepts_all(monkeypatch):
    _patch_cfg(monkeypatch)
    monkeypatch.setattr(p1mod, 'call_llm', lambda *a, **k: ['not', 'a', 'dict'])
    out = p1mod.judge_p1_sentences(
        db=None, lemma='x', definition='', sense_fingerprint='',
        register='neutral', sentences=['a', 'b'], language_id=2,
    )
    assert len(out) == 2 and all(o.verdict == 'accept' for o in out)


# ---------------------------------------------------------------------------
# P1 pipeline wiring (TASK-404) — index stability + block threshold
# ---------------------------------------------------------------------------

def _make_pipeline():
    from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
    # Pass a truthy sentinel db so __init__ never calls get_supabase_admin().
    return VocabAssetPipeline(db=object())


def _core_asset(n=10):
    return {
        'definition': 'financial institution',
        'sense_fingerprint': 'bank:money',
        'register': 'neutral',
        'sentences': [
            {'text': f'sentence {i}', 'target_word': 'bank',
             'source': 'gen', 'complexity_tier': 'B1'}
            for i in range(n)
        ],
    }


class _FakeP1Gen:
    """Stub CoreAssetGenerator: repair_sentences returns a scripted map."""
    def __init__(self, repaired):
        self._repaired = repaired
        self.model = 'test-model'

    def repair_sentences(self, core_asset, bad_indices, reasons, sense_id):
        return self._repaired


def _script_judge(monkeypatch, sequence):
    """Patch judge_p1_sentences (imported inside the helper) to pop scripted
    return-lists, one per call."""
    calls = list(sequence)

    def fake(db, lemma=None, definition=None, sense_fingerprint=None,
             register=None, sentences=None, language_id=None):
        return calls.pop(0)
    monkeypatch.setattr(p1mod, 'judge_p1_sentences', fake)


def test_pipeline_p1_judge_preserves_indices_after_repair(monkeypatch):
    pipe = _make_pipeline()
    core = _core_asset(10)

    # First judge pass: indices 2 and 5 reject, rest accept.
    first = [JudgeOutcome('accept', 5.0, 'clean') for _ in range(10)]
    first[2] = JudgeOutcome('reject', 2.0, 'sense')
    first[5] = JudgeOutcome('reject', 1.0, 'register')
    # Re-judge of the two repaired sentences: both accept now.
    rejudge = [JudgeOutcome('accept', 5.0, 'fixed'),
               JudgeOutcome('accept', 5.0, 'fixed')]
    _script_judge(monkeypatch, [first, rejudge])

    p1_gen = _FakeP1Gen(repaired={2: 'fixed two', 5: 'fixed five'})
    warnings, blocked = pipe._judge_p1_sentences(core, 2, p1_gen, sense_id=1)

    sents = core['sentences']
    assert len(sents) == 10                      # count unchanged
    assert [s['target_word'] for s in sents] == ['bank'] * 10  # order unchanged
    assert sents[2]['text'] == 'fixed two'       # repaired in place
    assert sents[5]['text'] == 'fixed five'
    assert sents[3]['text'] == 'sentence 3'      # untouched neighbour
    assert blocked is False
    assert warnings == []                        # all accept after repair


def test_pipeline_p1_judge_blocks_when_too_few_acceptable(monkeypatch):
    pipe = _make_pipeline()
    core = _core_asset(10)

    # 8 rejects (0-7), 2 accepts (8,9); repair yields nothing → 2 acceptable < 6.
    outcomes = [JudgeOutcome('reject', 1.0, 'bad') for _ in range(8)]
    outcomes += [JudgeOutcome('accept', 5.0, 'clean') for _ in range(2)]
    _script_judge(monkeypatch, [outcomes])

    p1_gen = _FakeP1Gen(repaired=None)           # repair fails
    warnings, blocked = pipe._judge_p1_sentences(core, 2, p1_gen, sense_id=1)

    assert blocked is True
    assert len(core['sentences']) == 10          # still never deletes
    assert any('asset blocked' in w for w in warnings)


def test_pipeline_p1_judge_failopen_on_length_mismatch(monkeypatch):
    pipe = _make_pipeline()
    core = _core_asset(10)
    # Judge returns fewer outcomes than sentences → can't map → fail open.
    _script_judge(monkeypatch, [[JudgeOutcome('reject', 1.0, 'x')]])
    warnings, blocked = pipe._judge_p1_sentences(core, 2, _FakeP1Gen(None), sense_id=1)
    assert (warnings, blocked) == ([], False)


# ---------------------------------------------------------------------------
# L1 listening-distractor judge (TASK-405) — filter + fail-open
# ---------------------------------------------------------------------------

def _patch_l1_cfg(monkeypatch, template="t={target}\n{distractors_numbered}"):
    monkeypatch.setattr(
        l1mod, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': template, 'model': 'test-model',
            'provider': 'openrouter', 'version': 1,
        },
    )


def test_l1_filter_keeps_and_rejects(monkeypatch):
    _patch_l1_cfg(monkeypatch)
    # ship: keep (minimal pair), sheep-synonym: reject, vessel: reject (synonym)
    monkeypatch.setattr(l1mod, 'call_llm', lambda *a, **k: {
        '1': {'verdict': 'keep', 'reason': 'minimal pair'},
        '2': {'verdict': 'reject', 'reason': 'synonym of target'},
        '3': {'verdict': 'reject', 'reason': 'spelling look-alike'},
    })
    kept, meta = l1mod.filter_l1_distractors(
        db=None, target='ship', distractors=['sheep', 'boat', 'shipment'],
        language_id=2,
    )
    assert kept == ['sheep']
    assert meta['rejected'] == 2 and meta['kept'] == 1
    assert set(meta['rejected_items']) == {'boat', 'shipment'}


def test_l1_filter_template_missing_keeps_all(monkeypatch):
    def _boom(db, task_name, language_id):
        raise RuntimeError('no row')
    monkeypatch.setattr(l1mod, 'get_template_config', _boom)
    kept, meta = l1mod.filter_l1_distractors(
        db=None, target='ship', distractors=['a', 'b', 'c'], language_id=2,
    )
    assert kept == ['a', 'b', 'c'] and meta['rejected'] == 0


def test_l1_filter_llm_error_keeps_all(monkeypatch):
    _patch_l1_cfg(monkeypatch)

    def _boom(*a, **k):
        raise RuntimeError('llm down')
    monkeypatch.setattr(l1mod, 'call_llm', _boom)
    kept, meta = l1mod.filter_l1_distractors(
        db=None, target='ship', distractors=['a', 'b'], language_id=2,
    )
    assert kept == ['a', 'b'] and meta['rejected'] == 0


def test_l1_filter_non_dict_keeps_all(monkeypatch):
    _patch_l1_cfg(monkeypatch)
    monkeypatch.setattr(l1mod, 'call_llm', lambda *a, **k: 'oops')
    kept, _ = l1mod.filter_l1_distractors(
        db=None, target='ship', distractors=['a', 'b'], language_id=2,
    )
    assert kept == ['a', 'b']


def test_l1_filter_empty_distractors(monkeypatch):
    _patch_l1_cfg(monkeypatch)
    kept, meta = l1mod.filter_l1_distractors(
        db=None, target='ship', distractors=[], language_id=2,
    )
    assert kept == [] and meta['rejected'] == 0


# ---------------------------------------------------------------------------
# Collocation judge (TASK-408) — one prompt, two call sites (L5 filter, L8 verdict)
# ---------------------------------------------------------------------------

def _patch_coll_cfg(
    monkeypatch,
    template="s={sentence} t={target} c={correct_collocate}\n{candidates_numbered}",
):
    monkeypatch.setattr(
        collocmod, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': template, 'model': 'test-model',
            'provider': 'openrouter', 'version': 1,
        },
    )
    # judge_collocation_repair logs a verdict row best-effort; stub it out.
    monkeypatch.setattr(collocmod, 'log_judge_verdict', lambda **kw: None)


# --- L5 filter shape -------------------------------------------------------

def test_collocation_filter_drops_valid_collocate_keeps_non_collocate(monkeypatch):
    _patch_coll_cfg(monkeypatch)
    # target 'decision', correct 'make': 'reach' is an also-valid collocate
    # (reach a decision) → drop; 'do'/'have' are genuine non-collocates → keep.
    monkeypatch.setattr(collocmod, 'call_llm', lambda *a, **k: {
        '1': {'rating': 1, 'reason': 'reach a decision is also valid'},
        '2': {'rating': 5, 'reason': 'unnatural'},
        '3': {'rating': 4, 'reason': 'unnatural'},
    })
    kept, meta = collocmod.filter_collocation_distractors(
        db=None, sentence='We must ___ a decision today.', target='decision',
        correct_collocate='make', distractors=['reach', 'do', 'have'],
        language_id=2,
    )
    assert kept == ['do', 'have']
    assert meta['rejected'] == 1 and meta['kept'] == 2
    assert meta['rejected_items'] == ['reach']


def test_collocation_filter_template_missing_keeps_all(monkeypatch):
    def _boom(db, task_name, language_id):
        raise RuntimeError('no row')
    monkeypatch.setattr(collocmod, 'get_template_config', _boom)
    kept, meta = collocmod.filter_collocation_distractors(
        db=None, sentence='s', target='t', correct_collocate='c',
        distractors=['a', 'b', 'c'], language_id=2,
    )
    assert kept == ['a', 'b', 'c'] and meta['rejected'] == 0


def test_collocation_filter_empty_distractors(monkeypatch):
    _patch_coll_cfg(monkeypatch)
    kept, meta = collocmod.filter_collocation_distractors(
        db=None, sentence='s', target='t', correct_collocate='c',
        distractors=[], language_id=2,
    )
    assert kept == [] and meta['rejected'] == 0


# --- L8 verdict shape ------------------------------------------------------

def test_collocation_repair_accepts_genuine_non_collocate(monkeypatch):
    _patch_coll_cfg(monkeypatch)
    monkeypatch.setattr(collocmod, 'call_llm', lambda *a, **k: {
        '1': {'rating': 5, 'reason': 'clearly wrong'},
    })
    out = collocmod.judge_collocation_repair(
        db=None, sentence='He ___ a strong coffee.', target='coffee',
        correct_collocate='made', error_collocate='cooked', language_id=2,
    )
    assert out.verdict == 'accept' and out.confidence == 5.0


def test_collocation_repair_rejects_actual_collocate(monkeypatch):
    _patch_coll_cfg(monkeypatch)
    # The "error" word is actually a valid collocate → the exercise is broken.
    monkeypatch.setattr(collocmod, 'call_llm', lambda *a, **k: {
        '1': {'rating': 1, 'reason': 'brew coffee is also fine'},
    })
    out = collocmod.judge_collocation_repair(
        db=None, sentence='He ___ a strong coffee.', target='coffee',
        correct_collocate='made', error_collocate='brewed', language_id=2,
    )
    # rating 1 (idiomatic, also-correct collocate) → reject the repair exercise.
    assert out.verdict == 'reject' and out.confidence == 1.0


def test_collocation_repair_flags_uncertain(monkeypatch):
    _patch_coll_cfg(monkeypatch)
    monkeypatch.setattr(collocmod, 'call_llm', lambda *a, **k: {
        '1': {'rating': 3, 'reason': 'borderline'},
    })
    out = collocmod.judge_collocation_repair(
        db=None, sentence='s', target='t', correct_collocate='c',
        error_collocate='e', language_id=2,
    )
    assert out.verdict == 'flag' and out.confidence == 3.0


def test_collocation_repair_llm_error_safe_accepts(monkeypatch):
    _patch_coll_cfg(monkeypatch)

    def _boom(*a, **k):
        raise RuntimeError('llm down')
    monkeypatch.setattr(collocmod, 'call_llm', _boom)
    out = collocmod.judge_collocation_repair(
        db=None, sentence='s', target='t', correct_collocate='c',
        error_collocate='e', language_id=2,
    )
    assert out.verdict == 'accept'


def test_collocation_repair_no_error_word_safe_accepts(monkeypatch):
    _patch_coll_cfg(monkeypatch)
    out = collocmod.judge_collocation_repair(
        db=None, sentence='s', target='t', correct_collocate='c',
        error_collocate='', language_id=2,
    )
    assert out.verdict == 'accept'


# ---------------------------------------------------------------------------
# Sentence-validity judge (TASK-411) — verdict per wrong sentence; L6 + L7
# ---------------------------------------------------------------------------

def _patch_sv_cfg(monkeypatch, template="word={target}\n{pairs_numbered}"):
    monkeypatch.setattr(
        svmod, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': template, 'model': 'test-model',
            'provider': 'openrouter', 'version': 1,
        },
    )
    monkeypatch.setattr(svmod, 'log_judge_verdict', lambda **kw: None)


def test_sv_judge_parses_ratings(monkeypatch):
    _patch_sv_cfg(monkeypatch)
    # 5 -> accept (cleanly wrong as labeled); 1 -> reject (actually fine);
    # 2 -> reject (mislabeled); 3 -> flag.
    monkeypatch.setattr(svmod, 'call_llm', lambda *a, **k: {
        '1': {'rating': 5, 'reason': 'wrong measure word as labeled'},
        '2': {'rating': 1, 'reason': 'sentence is actually grammatical'},
        '3': {'rating': 2, 'reason': 'wrong, but for word order not aspect'},
        '4': {'rating': 3, 'reason': 'borderline'},
    })
    out = svmod.judge_wrong_sentences(
        db=None, target='看', language_id=1,
        sentences_with_reasons=[
            ('s1', 'measure word'), ('s2', 'aspect marker'),
            ('s3', 'aspect marker'), ('s4', 'direction complement'),
        ],
    )
    assert [o.verdict for o in out] == ['accept', 'reject', 'reject', 'flag']
    assert [o.confidence for o in out] == [5.0, 1.0, 2.0, 3.0]


def test_sv_judge_l7_single_item(monkeypatch):
    _patch_sv_cfg(monkeypatch)
    monkeypatch.setattr(svmod, 'call_llm', lambda *a, **k: {
        '1': {'rating': 1, 'reason': 'this "incorrect" sentence is fine'},
    })
    out = svmod.judge_wrong_sentences(
        db=None, target='run', language_id=2,
        sentences_with_reasons=[('He runs fast.', 'subject-verb agreement')],
    )
    assert len(out) == 1 and out[0].verdict == 'reject'


def test_sv_judge_empty_returns_empty(monkeypatch):
    _patch_sv_cfg(monkeypatch)
    assert svmod.judge_wrong_sentences(
        db=None, target='x', sentences_with_reasons=[], language_id=2,
    ) == []


def test_sv_judge_missing_entry_safe_accepts_that_sentence(monkeypatch):
    _patch_sv_cfg(monkeypatch)
    monkeypatch.setattr(svmod, 'call_llm', lambda *a, **k: {
        '1': {'rating': 1, 'reason': 'fine'},
        # key "2" absent → safe-accept, never a spurious reject.
    })
    out = svmod.judge_wrong_sentences(
        db=None, target='x', language_id=2,
        sentences_with_reasons=[('a', 'r1'), ('b', 'r2')],
    )
    assert len(out) == 2
    assert out[0].verdict == 'reject'
    assert out[1].verdict == 'accept'


def test_sv_judge_unparseable_rating_safe_accepts(monkeypatch):
    _patch_sv_cfg(monkeypatch)
    monkeypatch.setattr(svmod, 'call_llm', lambda *a, **k: {
        '1': {'rating': 'nope', 'reason': 'x'},
    })
    out = svmod.judge_wrong_sentences(
        db=None, target='x', language_id=2,
        sentences_with_reasons=[('a', 'r')],
    )
    assert out[0].verdict == 'accept'


def test_sv_judge_template_missing_safe_accepts_all(monkeypatch):
    def _boom(db, task_name, language_id):
        raise RuntimeError('no row')
    monkeypatch.setattr(svmod, 'get_template_config', _boom)
    out = svmod.judge_wrong_sentences(
        db=None, target='x', language_id=2,
        sentences_with_reasons=[('a', 'r1'), ('b', 'r2'), ('c', 'r3')],
    )
    assert len(out) == 3 and all(o.verdict == 'accept' for o in out)


def test_sv_judge_llm_error_safe_accepts_all(monkeypatch):
    _patch_sv_cfg(monkeypatch)

    def _boom(*a, **k):
        raise RuntimeError('llm down')
    monkeypatch.setattr(svmod, 'call_llm', _boom)
    out = svmod.judge_wrong_sentences(
        db=None, target='x', language_id=2,
        sentences_with_reasons=[('a', 'r1'), ('b', 'r2')],
    )
    assert len(out) == 2 and all(o.verdict == 'accept' for o in out)


def test_sv_judge_non_dict_response_safe_accepts_all(monkeypatch):
    _patch_sv_cfg(monkeypatch)
    monkeypatch.setattr(svmod, 'call_llm', lambda *a, **k: ['nope'])
    out = svmod.judge_wrong_sentences(
        db=None, target='x', language_id=2,
        sentences_with_reasons=[('a', 'r1'), ('b', 'r2')],
    )
    assert len(out) == 2 and all(o.verdict == 'accept' for o in out)


# ---------------------------------------------------------------------------
# TASK-416: end-to-end integration — every judged level for one fixture sense
# with planted defects. Drives the REAL renderer (build_rows) and the REAL P1
# pipeline path; only each judge's call_llm / get_template_config boundary is
# mocked, so the renderer wiring (drop the bad item + lift tags.<judge>_judge)
# and the P1 index-preserving warning sidecar are both exercised.
#
# Planted defects (one per judge):
#   L1  synonym distractor          → not audio-confusable → dropped
#   L5  also-valid collocate        → an also-correct answer → dropped
#   L8  genuinely-correct error word→ exercise is broken → variant dropped
#   L6  mislabeled wrong sentence   → wrong for a different reason → dropped
#   L7  not-actually-wrong sentence → nothing to spot → variant dropped
#   P1  off-sense base sentence     → flagged in validation_warnings sidecar
# ---------------------------------------------------------------------------

import re

_L1_SYNONYM     = 'comprehend'     # synonym of 'learn' — not mishearable
_L5_VALID_COLLO = 'fast'           # 'learn fast' is also valid → drop as L5 distractor
_L8_VALID_COLLO = 'master'         # genuinely collocates → L8 repair exercise broken
_L6_MISLABELED  = 'MISLABELED'     # marker inside the mislabeled L6 wrong sentence
_L7_ACTUALLY_OK = 'ACTUALLYFINE'   # marker inside the not-actually-wrong L7 sentence


def _numbered_items(prompt: str) -> list[tuple[str, str]]:
    """Parse '<n>. <text>' lines from a rendered judge prompt. All three judged
    prompts (L1, collocation, sentence-validity) number their items this way."""
    return [(m.group(1), m.group(2).strip())
            for m in re.finditer(r'(?m)^\s*(\d+)\.\s*(.*)$', prompt)]


def _fake_l1_call(prompt, *a, **k):
    return {n: {'verdict': 'reject' if t == _L1_SYNONYM else 'keep', 'reason': t}
            for n, t in _numbered_items(prompt)}


def _fake_coll_call(prompt, *a, **k):
    bad = {_L5_VALID_COLLO, _L8_VALID_COLLO}
    return {n: {'rating': 1 if t in bad else 5, 'reason': t}
            for n, t in _numbered_items(prompt)}


def _fake_sv_call(prompt, *a, **k):
    out = {}
    for n, t in _numbered_items(prompt):
        if _L7_ACTUALLY_OK in t:
            out[n] = {'rating': 1, 'reason': 'actually grammatical'}
        elif _L6_MISLABELED in t:
            out[n] = {'rating': 2, 'reason': 'wrong for a different reason'}
        else:
            out[n] = {'rating': 5, 'reason': 'cleanly wrong as labeled'}
    return out


def _integration_core():
    sents = [
        {'text': 'I learn every day.',            'target_word': 'learn'},  # 0
        {'text': 'She learns new words.',         'target_word': 'learn'},  # 1
        {'text': 'Children learn music quickly.', 'target_word': 'learn'},  # 2  L5
        {'text': 'We learn from mistakes.',       'target_word': 'learn'},  # 3  L6 correct
        {'text': 'They learn German slowly.',     'target_word': 'learn'},  # 4  L8
        {'text': 'He likes to learn alone.',      'target_word': 'learn'},  # 5  L9
        {'text': 'You learn best by doing.',      'target_word': 'learn'},  # 6
        {'text': 'An off-sense learn line.',      'target_word': 'learn'},  # 7  P1 plant
        {'text': 'Teachers learn too.',           'target_word': 'learn'},  # 8
        {'text': 'Learn it well today.',          'target_word': 'learn'},  # 9
    ]
    return {
        'semantic_class': 'action_verb',   # keeps all 9 levels active (en)
        'definition': 'to acquire knowledge of a subject',
        'sense_fingerprint': 'learn:acquire-knowledge',
        'register': 'neutral',
        'pronunciation': 'lɜːrn',
        'sentences': sents,
    }


def _integration_p2():
    return {
        'level_1': {
            'options': [
                {'text': 'learn', 'is_correct': True},
                {'text': _L1_SYNONYM},                       # synonym → judge rejects
                {'text': 'yearn'}, {'text': 'burn'}, {'text': 'turn'},
            ],
            'explanations': {},
        },
        'level_5': {
            'sentence_index': 2,
            'correct_collocate': 'quickly',
            'options': [
                {'text': 'quickly', 'is_correct': True},
                {'text': _L5_VALID_COLLO},                   # also-valid → dropped
                {'text': 'green'}, {'text': 'tall'}, {'text': 'blue'},
            ],
        },
        'level_6': {
            'correct_sentence_index': 3,
            'wrong_sentences': [
                {'text': f'A wrong sentence {_L6_MISLABELED} here.', 'explanation': 'aspect marker'},
                {'text': 'Wrong two example.',   'explanation': 'word order'},
                {'text': 'Wrong three example.', 'explanation': 'measure word'},
                {'text': 'Wrong four example.',  'explanation': 'tense'},
            ],
        },
    }


def _integration_p3():
    return {
        'level_7': {
            'incorrect_sentence': f'This one is {_L7_ACTUALLY_OK} grammatical.',
            'error_description': 'subject-verb agreement',
            'correct_sentence_indices': [0, 1, 2],
        },
        'level_8': {
            'sentence_index': 4,
            'correct_collocate': 'slowly',
            'error_collocate': _L8_VALID_COLLO,              # genuine collocate → reject
            'explanations': {'slowly': 'pace adverb'},
        },
    }


def test_integration_all_judges_drop_planted_defects(monkeypatch):
    from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer

    core = _integration_core()
    p2, p3 = _integration_p2(), _integration_p3()

    # Mock every judge's template + LLM boundary so the plants are recognised;
    # everything else (renderer wiring, parsing, verdict mapping) is real.
    _patch_cfg(monkeypatch)                                 # P1 cfg + log stub
    monkeypatch.setattr(p1mod, 'call_llm',
                        lambda *a, **k: {'8': {'rating': 1, 'reason': 'off-sense'}})
    _patch_l1_cfg(monkeypatch)
    monkeypatch.setattr(l1mod, 'call_llm', _fake_l1_call)
    _patch_coll_cfg(monkeypatch)
    monkeypatch.setattr(collocmod, 'call_llm', _fake_coll_call)
    _patch_sv_cfg(monkeypatch)
    monkeypatch.setattr(svmod, 'call_llm', _fake_sv_call)

    # --- P1 sentence judge (asset-pipeline path) -----------------------------
    pipe = _make_pipeline()
    warnings, blocked = pipe._judge_p1_sentences(
        core, 2, _FakeP1Gen(repaired=None), sense_id=1)
    assert blocked is False                                 # 9 acceptable >= 6
    assert len(core['sentences']) == 10                     # indices never deleted
    assert any(w.startswith('P1 sentence[7] rejected') for w in warnings)

    # --- L1 / L5 / L6 / L7 / L8 via the real renderer ------------------------
    renderer = LadderExerciseRenderer(db=object(), audio_synthesizer=None)
    monkeypatch.setattr(renderer, '_load_assets', lambda sid: {
        'prompt1_core': core,
        'prompt2_exercises_A': p2,
        'prompt3_transforms_A': p3,
    })
    monkeypatch.setattr(renderer, '_load_asset_ids', lambda sid: {'prompt1_core': 999})
    monkeypatch.setattr(renderer, '_get_tier', lambda c: 'B1')

    rows = renderer.build_rows(sense_id=1, language_id=2)
    by_level = {r['ladder_level']: r for r in rows}

    # L1: synonym distractor dropped; meta lifted into tags.l1_distractor_judge.
    assert 1 in by_level, 'L1 should still render with 3 surviving distractors'
    l1 = by_level[1]
    assert l1['tags']['l1_distractor_judge']['rejected'] == 1
    assert _L1_SYNONYM not in l1['content']['options']

    # L5: also-valid collocate dropped; tags.collocation_judge populated.
    assert 5 in by_level
    l5 = by_level[5]
    assert l5['tags']['collocation_judge']['rejected'] == 1
    assert _L5_VALID_COLLO not in l5['content']['options']

    # L6: mislabeled wrong sentence dropped; tags.sentence_validity_judge populated.
    assert 6 in by_level
    l6 = by_level[6]
    assert l6['tags']['sentence_validity_judge']['rejected'] == 1
    assert not any(_L6_MISLABELED in s['text'] for s in l6['content']['sentences'])

    # L7 + L8: the judge rejected the planted artifact → the whole variant drops.
    assert 7 not in by_level, 'L7 dropped: the "incorrect" sentence is actually fine'
    assert 8 not in by_level, 'L8 dropped: the error word is a genuine collocate'
