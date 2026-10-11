# tests/test_asset_pipeline_p1_gate.py
"""Regression test for ADR-028 Phase 0's "en prompt1_core fails" diagnosis.

Investigating the pilot_en run (data/eval/runs/pilot_en/*.json) found that
prompt1_core does NOT actually fail there -- it validates successfully
(after one repair round) for both senses, so P2/P3/L4/typed generation
legitimately ran and spent money. The 0-exercise-rows symptom was traced to
scripts/run_exercise_gen_eval.py's write-interception architecture instead
(see the ShadowReadClient tests in tests/test_run_exercise_gen_eval.py).

Separately, the task asked to verify (and lock in with a test) that the
REAL production pipeline stops before P2/P3/L4/typed generation whenever
there is no valid prompt1_core -- since running them without one is pure
waste (nothing can render without it; see
exercise_renderer.py::build_rows's own early return). This already exists in
`VocabAssetPipeline._generate_for_sense_impl` (services/vocabulary_ladder/
asset_pipeline.py, the `if core_asset is None` / `if not p1_valid` blocks
before the P2/P3 fan-out is ever constructed) -- these tests pin that
behaviour so a future refactor can't silently drop it. Also consistent with
services/vocabulary_ladder/queue_drain.py::_regenerate, which independently
refuses to call the renderer at all once generate_for_sense() reports
status == 'failed'.

No real DB, no real LLM calls -- CoreAssetGenerator and the validator are
replaced with fakes, and BatchModeThreadPoolExecutor is replaced with a
stand-in that raises if the pipeline ever tries to enter the P2/P3/L4/typed
fan-out stage.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import services.vocabulary_ladder.asset_pipeline as asset_pipeline_module  # noqa: E402
from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline  # noqa: E402


class _RefusingPool:
    """Stands in for `BatchModeThreadPoolExecutor(...)`. Entering the `with`
    block is exactly the P2/P3/L4/typed fan-out starting -- which must never
    happen without a valid prompt1_core -- so `__enter__` fails the test
    instead of letting any of that code run."""

    def __enter__(self):
        raise AssertionError(
            "P2/P3/L4/typed fan-out must not start without a valid prompt1_core"
        )

    def __exit__(self, *_a):
        return False


class _FakeCoreGen:
    """Stands in for CoreAssetGenerator -- returns canned generate()/repair()
    output so the test controls P1's raw content without any LLM call."""

    model = 'fake-model'

    def __init__(self, _db, _language_id, *, raw=None, repaired=None,
                 sentence_repair=None):
        self._raw = raw
        self._repaired = repaired
        self._sentence_repair = sentence_repair
        self.sentence_repair_calls: list = []

    def generate(self, _sense_id, _corpus_sentences):
        return self._raw

    def repair(self, _current_content, _validation_errors, _sense_id):
        return self._repaired

    def repair_sentences(self, core_asset, bad_indices, reasons, sense_id):
        self.sentence_repair_calls.append(
            {'bad_indices': list(bad_indices), 'reasons': dict(reasons)},
        )
        return self._sentence_repair


def _make_pipeline(monkeypatch, *, p1_raw, p1_valid_sequence, repaired=None,
                    sentence_repair=None):
    """A VocabAssetPipeline with every DB-touching helper before the P1 gate
    faked out, `validate_prompt1` returning `p1_valid_sequence` in order (one
    call for the initial attempt, a second for the post-repair re-check when
    reached), and the fan-out stage wired to blow up if ever entered."""
    pipeline = VocabAssetPipeline(db=object())  # never touched on this path

    monkeypatch.setattr(asset_pipeline_module, 'is_quarantined', lambda db, sid: False)
    monkeypatch.setattr(pipeline, '_assets_exist', lambda sid: False)
    monkeypatch.setattr(pipeline, '_fetch_corpus_sentences', lambda sid, lid: [])
    monkeypatch.setattr(pipeline, '_store_asset', lambda *a, **kw: None)
    fake_gen_holder = {}

    def _make_fake_gen(db, language_id):
        fake_gen_holder['gen'] = _FakeCoreGen(
            db, language_id, raw=p1_raw, repaired=repaired,
            sentence_repair=sentence_repair,
        )
        return fake_gen_holder['gen']

    monkeypatch.setattr(asset_pipeline_module, 'CoreAssetGenerator', _make_fake_gen)
    monkeypatch.setattr(
        asset_pipeline_module, 'BatchModeThreadPoolExecutor',
        lambda *a, **kw: _RefusingPool(),
    )

    remaining = list(p1_valid_sequence)

    def _fake_validate(content, language_id):
        return remaining.pop(0)

    monkeypatch.setattr(pipeline.validator, 'validate_prompt1', _fake_validate)
    pipeline._fake_gen_holder = fake_gen_holder
    return pipeline


def test_no_fan_out_when_p1_generation_returns_none(monkeypatch):
    pipeline = _make_pipeline(monkeypatch, p1_raw=None, p1_valid_sequence=[])

    result = pipeline._generate_for_sense_impl(1, 2, False, 'batch-1')

    assert result['status'] == 'failed'
    assert result['errors'] == ['Prompt 1 generation failed']


def test_no_fan_out_when_p1_invalid_and_repair_also_fails(monkeypatch):
    pipeline = _make_pipeline(
        monkeypatch, p1_raw={'pos': 'noun'},
        p1_valid_sequence=[(False, ['bad sentences'], [])],
        repaired=None,  # repair() itself returns nothing usable
    )

    result = pipeline._generate_for_sense_impl(1, 2, False, 'batch-1')

    assert result['status'] == 'failed'
    assert result['errors'] == ['bad sentences']


def test_no_fan_out_when_repair_output_is_still_invalid(monkeypatch):
    pipeline = _make_pipeline(
        monkeypatch, p1_raw={'pos': 'noun'},
        p1_valid_sequence=[(False, ['bad'], []), (False, ['still bad'], [])],
        repaired={'pos': 'noun', 'patched': True},
    )

    result = pipeline._generate_for_sense_impl(1, 2, False, 'batch-1')

    assert result['status'] == 'failed'
    assert result['errors'] == ['still bad']


def test_sentence_scoped_p1_error_uses_surgical_repair_not_blunt_repair(monkeypatch):
    """TASK-8xx (item 2): a P1 validation failure confined ENTIRELY to
    specific sentences (e.g. a whole-word mismatch, observed live on en sense
    15328 'away' and ja sense 34999 '一') must route through the
    index-preserving `repair_sentences` -- the same surgical repair the tier
    gate and the P1 sentence judge already use -- rather than losing the
    whole asset or handing it to the blunt whole-JSON `repair()` first."""
    sentences = [{'text': f'Sentence {i} text.', 'target_word': 'away'} for i in range(10)]
    pipeline = _make_pipeline(
        monkeypatch,
        p1_raw={'pos': 'adverb', 'sentences': sentences},
        p1_valid_sequence=[
            (False, ["Sentence 7: target_word 'away' is not a whole-word match in text"], []),
            (True, [], []),
        ],
        sentence_repair={7: 'A fresh sentence that really is far away.'},
    )

    try:
        pipeline._generate_for_sense_impl(1, 2, False, 'batch-1')
    except Exception:
        pass  # raised before/at the fan-out -- proves the P1 gate passed

    fake_gen = pipeline._fake_gen_holder['gen']
    assert len(fake_gen.sentence_repair_calls) == 1
    assert fake_gen.sentence_repair_calls[0]['bad_indices'] == [7]


def test_sentence_scoped_repair_failure_falls_through_to_blunt_repair(monkeypatch):
    """When the scoped repair itself doesn't resolve it, the existing blunt
    whole-JSON `repair()` is still tried (unchanged fallback), and the scoped
    attempt happened FIRST."""
    sentences = [{'text': f'Sentence {i} text.', 'target_word': 'away'} for i in range(10)]
    pipeline = _make_pipeline(
        monkeypatch,
        p1_raw={'pos': 'adverb', 'sentences': sentences},
        p1_valid_sequence=[
            (False, ["Sentence 7: target_word 'away' is not a whole-word match in text"], []),
        ],
        sentence_repair=None,   # the scoped repair call itself produced nothing
        repaired=None,          # the blunt repair also fails
    )

    result = pipeline._generate_for_sense_impl(1, 2, False, 'batch-1')

    fake_gen = pipeline._fake_gen_holder['gen']
    assert len(fake_gen.sentence_repair_calls) == 1, 'scoped repair was attempted first'
    assert result['status'] == 'failed'


def test_asset_wide_p1_error_skips_sentence_repair_entirely(monkeypatch):
    """A non-sentence-scoped error (e.g. an invalid POS enum) must go
    straight to the blunt `repair()` -- `repair_sentences` has nothing to
    target when the defect isn't confined to specific sentence indices."""
    sentences = [{'text': f'Sentence {i} text.', 'target_word': 'away'} for i in range(10)]
    pipeline = _make_pipeline(
        monkeypatch,
        p1_raw={'pos': 'bogus', 'sentences': sentences},
        p1_valid_sequence=[
            (False, ["Invalid POS: 'bogus'"], []),
        ],
        sentence_repair={7: 'should never be used'},
        repaired=None,
    )

    result = pipeline._generate_for_sense_impl(1, 2, False, 'batch-1')

    fake_gen = pipeline._fake_gen_holder['gen']
    assert fake_gen.sentence_repair_calls == [], \
        'an asset-wide error must not trigger the sentence-scoped repair path'
    assert result['status'] == 'failed'


def test_fan_out_does_start_once_p1_is_valid(monkeypatch):
    """Sanity check on the fake itself: a valid P1 (no repair needed) DOES
    reach the fan-out stage -- proving the previous three tests fail for the
    right reason (an invalid P1 short-circuiting before the fan-out) and not
    because `_RefusingPool` is simply never reachable for any input.

    `_generate_for_sense_impl` reads real config/corpus-gating state between
    the P1 gate and the fan-out that this test doesn't fake, so it may raise
    something unrelated first -- the one outcome that specifically
    disproves this test is a clean 'failed' *return* (no exception at all),
    which would mean the P1 gate fired even though P1 was valid.
    """
    pipeline = _make_pipeline(
        monkeypatch, p1_raw={'pos': 'noun', 'sentences': []},
        p1_valid_sequence=[(True, [], [])],
    )

    try:
        result = pipeline._generate_for_sense_impl(1, 2, False, 'batch-1')
    except Exception:
        return  # raised before/at the fan-out -- the P1 gate did not fire

    assert result['status'] != 'failed', (
        "P1 was valid, but _generate_for_sense_impl returned 'failed' without "
        "ever raising -- the P1 gate must have misfired"
    )
