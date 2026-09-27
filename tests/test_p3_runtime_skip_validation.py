# tests/test_p3_runtime_skip_validation.py
"""Regression test for the prompt3_transforms "Missing level_8" false invalid.

Root cause (found investigating the ADR-028 Phase 1 baseline/smoke evals,
en prompt3_transforms invalid_rate ~= 0.96 on baseline_en / sonnet-5 and
4/5 on phase1_smoke_en / qwen -- i.e. present under BOTH models, so not a
qwen-specific defect):

``p3_expected_levels`` (services/vocabulary_ladder/asset_pipeline.py,
computed via ``prompt3_levels_for_context`` before any sentence exists) is a
*planning-time* decision. L8's capability row requires ``primary_collocate``,
but ``capability_context_from_core`` never puts that key in the context dict
(config.py: only ``morph_forms`` / ``pronunciation`` / ``p1_definition`` /
``p1_sentences`` are included), so ``requirements_met`` treats it as
"unevaluable, satisfied" -- L8 (and, by the same shape, L4) is essentially
always planned as expected.

Whether L8 can *actually* run is a separate, runtime-only question answered
by ``CollocationRepairGenerator._sentence_index`` (does the primary_collocate
literally occur, whole-word, in one of the sentences P1 wrote?) -- almost
always "no" for English collocates, since P1's sentence pool is small and
unconstrained. When it's "no", ``SplitLevelGenerator.generate()`` returns
``{}`` (a documented clean skip, not a failure). Before the fix, that `{}`
never added a ``level_8`` key to the merged asset, but ``p3_expected_levels``
still expected one -- so ``validate_prompt3`` raised "Missing level_8" and
marked an otherwise entirely healthy asset invalid. L5 already gets an
equivalent *upfront* PMI-based gate (see the "Dropping L5" block in
``_generate_for_sense_impl``); L4/L8 had no such gate because their runtime
feasibility check can only run after P1's sentences exist.

The fix drops any split level whose generator returned the clean-skip `{}`
from what the validator is told to expect, for that one variant, without
touching the (already self-consistent) P3-monolith `{}` case or genuine
generation failures (`None`, which still raise the usual "Prompt 3 (L*)
variant * generation failed" error).

This test drives the real pipeline (`VocabAssetPipeline._generate_for_sense_impl`)
and the real ``VocabAssetValidator`` end to end, faking out every LLM-calling
generator and DB write so no network/DB access happens. No real LLM calls.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import services.vocabulary_ladder.asset_pipeline as asset_pipeline_module  # noqa: E402
from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline  # noqa: E402


CORE_ASSET = {
    'pos': 'verb',
    'semantic_class': 'action',
    'definition': 'to do a thing',
    'pronunciation': '/duː/',
    'primary_collocate': 'somewhat-unrelated-word',
    'morphological_forms': [{'form': 'doing'}, {'form': 'done'}],
    'sentences': [
        {'text': 'She does it every day.', 'target': 'does'},
        {'text': 'He did it yesterday.', 'target': 'did'},
    ],
}

VALID_LEVEL_7 = {
    'level_7': {
        'incorrect_sentence': 'She do it every day.',
        'corrected_sentence': 'She does it every day.',
        'error_description': 'subject-verb agreement',
    },
}


class _FakeCoreGen:
    model = 'fake-model'

    def __init__(self, _db, _language_id):
        pass

    def generate(self, _sense_id, _corpus_sentences):
        return dict(CORE_ASSET)


class _FakeP2Gen:
    """Simulates a P2 failure -- irrelevant to this test's assertion, kept
    simple (`None`) so `result['errors']` carries one unrelated, expected
    entry and nothing this test needs to distinguish from the L8 bug."""

    model = 'fake-model'

    def __init__(self, _db, _language_id):
        pass

    def generate(self, *_a, **_kw):
        return None


class _FakeP3MonolithGen:
    """Simulates a real, successful P3 monolith call producing level_7 --
    proves the merged asset is otherwise healthy so the ONLY thing that can
    flip `is_valid` is the L8 handling under test."""

    model = 'fake-model'

    def __init__(self, _db, _language_id):
        pass

    def generate(self, *_a, **_kw):
        return dict(VALID_LEVEL_7)


class _FakeCleanSkipSplitGen:
    """Simulates SplitLevelGenerator.generate()'s documented clean-skip
    return: `{}` when the sense cannot support this level at runtime."""

    model = 'fake-model'

    def __init__(self, _db, _language_id):
        pass

    def generate(self, *_a, **_kw):
        return {}


def _make_pipeline(monkeypatch):
    pipeline = VocabAssetPipeline(db=object())  # never touched on this path

    monkeypatch.setattr(asset_pipeline_module, 'is_quarantined', lambda db, sid: False)
    monkeypatch.setattr(pipeline, '_assets_exist', lambda sid: False)
    monkeypatch.setattr(pipeline, '_fetch_corpus_sentences', lambda sid, lid: [])
    monkeypatch.setattr(pipeline, '_update_vocabulary_metadata', lambda *a, **kw: None)
    monkeypatch.setattr(pipeline, '_collocation_is_fixed', lambda *a, **kw: True)
    monkeypatch.setattr(pipeline, '_judge_p1_sentences', lambda *a, **kw: ([], False))

    stored = []
    monkeypatch.setattr(
        pipeline, '_store_asset',
        lambda sense_id, language_id, asset_type, content, model, batch_id,
               is_valid=True, validation_errors=None, validation_warnings=None:
            stored.append({
                'asset_type': asset_type, 'content': content,
                'is_valid': is_valid, 'validation_errors': validation_errors,
            }),
    )

    monkeypatch.setattr(
        asset_pipeline_module, 'CoreAssetGenerator',
        lambda db, language_id: _FakeCoreGen(db, language_id),
    )
    monkeypatch.setattr(pipeline.validator, 'validate_prompt1', lambda content, lid: (True, [], []))

    monkeypatch.setattr(asset_pipeline_module, 'ExerciseAssetGenerator', _FakeP2Gen)
    monkeypatch.setattr(asset_pipeline_module, 'TransformAssetGenerator', _FakeP3MonolithGen)
    monkeypatch.setattr(asset_pipeline_module, 'MorphologySlotGenerator', _FakeCleanSkipSplitGen)
    monkeypatch.setattr(asset_pipeline_module, 'CollocationRepairGenerator', _FakeCleanSkipSplitGen)
    monkeypatch.setattr(
        asset_pipeline_module.typed_llm, 'generate_all',
        lambda *a, **kw: ({}, []),
    )

    return pipeline, stored


def test_l8_clean_skip_does_not_invalidate_an_otherwise_healthy_asset(monkeypatch):
    """The bug, pinned: L4 and L8 both come back as a clean `{}` skip (no
    usable sentence for either), while P3's own level_7 succeeds. The stored
    prompt3_transforms asset must be valid, and neither "Missing level_4" nor
    "Missing level_8" may appear anywhere in the result."""
    pipeline, stored = _make_pipeline(monkeypatch)

    result = pipeline._generate_for_sense_impl(1, 2, False, 'batch-1')

    p3_rows = [s for s in stored if s['asset_type'].startswith('prompt3_transforms_')]
    assert p3_rows, 'expected at least one prompt3_transforms_* asset to be stored'
    for row in p3_rows:
        assert row['is_valid'] is True, (
            f"{row['asset_type']} marked invalid: {row['validation_errors']}"
        )
        assert 'level_7' in row['content']
        assert 'level_4' not in row['content']
        assert 'level_8' not in row['content']

    joined_errors = ' | '.join(result['errors'])
    assert 'Missing level_4' not in joined_errors
    assert 'Missing level_8' not in joined_errors


def test_a_genuine_l8_generation_failure_is_still_reported(monkeypatch):
    """Sanity check on the fix's scoping: `None` (a real failure) must still
    raise the usual error and still fail validation -- only the `{}` clean
    skip is exempted."""
    pipeline, stored = _make_pipeline(monkeypatch)

    class _FailingSplitGen(_FakeCleanSkipSplitGen):
        def generate(self, *_a, **_kw):
            return None

    monkeypatch.setattr(asset_pipeline_module, 'CollocationRepairGenerator', _FailingSplitGen)

    result = pipeline._generate_for_sense_impl(1, 2, False, 'batch-1')

    assert any(
        'Prompt 3 (L8)' in e and 'generation failed' in e for e in result['errors']
    ), result['errors']
