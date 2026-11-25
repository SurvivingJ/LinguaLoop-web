"""Characterisation of the vocabulary-ladder DEFAULT path (bundle mode unset).

Pins the observable output of ``VocabAssetPipeline._generate_for_sense_impl``
(stored assets, errors, generator call log) and of
``LadderExerciseRenderer.build_rows`` (every row, every judge call) for a fixed
fixture, so that removing the retired bundle mode cannot change what the
fat-seed and staged-runner pipelines produce.  The expected values were captured
from the code BEFORE bundle mode was deleted.

Each test also sets ``VOCAB_LADDER_BUNDLE_MODE=on`` in the environment: after
the bundle package's deletion nothing reads that variable, so the output must be
identical to the unset case (an environment that still sets it is harmless).

LLM-free and DB-free: every generator and judge is a recording fake.
"""

import json
import pathlib
import random
import threading

import pytest

import services.vocabulary_ladder.asset_pipeline as asset_pipeline_module
import services.vocabulary_ladder.exercise_renderer as rendermod
from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline

LANG_EN = 2


def _canon(obj):
    return json.loads(json.dumps(obj, sort_keys=True, default=str))


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

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


def _pipeline(monkeypatch, calls):
    lock = threading.Lock()

    def rec(name, *args):
        with lock:
            calls.append((name,) + args)

    pipeline = VocabAssetPipeline(db=object())
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
                'asset_type': asset_type, 'content': content, 'model': model,
                'is_valid': is_valid, 'validation_errors': validation_errors,
            }),
    )

    class Core:
        model = 'm-core'

        def __init__(self, db, language_id):
            pass

        def generate(self, sense_id, corpus):
            rec('p1.generate', sense_id)
            return dict(CORE_ASSET)

    class P2:
        model = 'm-p2'

        def __init__(self, db, language_id):
            pass

        def generate(self, sense_id, core, active_levels, sa):
            rec('p2.generate', sense_id, tuple(active_levels), tuple(sorted(sa.items())))
            return {'level_1': {'marker': 'p2-%s' % sorted(sa.items())[0][1]}}

    class P3:
        model = 'm-p3'

        def __init__(self, db, language_id):
            pass

        def generate(self, sense_id, core, active_levels, sa, l7, *rest):
            rec('p3.generate', sense_id, tuple(active_levels), tuple(l7), rest[1:2])
            return {'level_7': {
                'incorrect_sentence': 'She do it every day.',
                'corrected_sentence': 'She does it every day.',
                'error_description': 'agreement',
                'correct_sentence_indices': list(l7),
            }}

    class Split:
        model = 'm-split'

        def __init__(self, db, language_id):
            pass

        def generate(self, sense_id, core, sa):
            rec('split.generate', sense_id, tuple(sorted(sa.items())))
            return {}

    monkeypatch.setattr(asset_pipeline_module, 'CoreAssetGenerator', Core)
    monkeypatch.setattr(asset_pipeline_module, 'ExerciseAssetGenerator', P2)
    monkeypatch.setattr(asset_pipeline_module, 'TransformAssetGenerator', P3)
    monkeypatch.setattr(asset_pipeline_module, 'MorphologySlotGenerator', Split)
    monkeypatch.setattr(asset_pipeline_module, 'CollocationRepairGenerator', Split)
    monkeypatch.setattr(pipeline.validator, 'validate_prompt1', lambda c, l: (True, [], []))
    monkeypatch.setattr(pipeline.validator, 'validate_prompt2', lambda a, lv: (True, []))

    def typed(db, language_id, sense_id, core, sc, sa, cc, wanted):
        rec('typed.generate', sense_id, tuple(sorted(sa.items())),
            None if wanted is None else tuple(sorted(wanted)))
        return {}, []

    monkeypatch.setattr(asset_pipeline_module.typed_llm, 'generate_all', typed)
    return pipeline, stored


def _run_pipeline(monkeypatch, levels):
    calls = []
    pipeline, stored = _pipeline(monkeypatch, calls)
    result = pipeline._generate_for_sense_impl(1, LANG_EN, False, 'batch-1', levels=levels)
    result.pop('stage_seconds', None)
    return _canon({
        'result': result,
        'stored': sorted(stored, key=lambda s: s['asset_type']),
        'calls': sorted(calls, key=repr),
    })


@pytest.mark.parametrize('bundle_env', [None, 'on', 'shadow'])
@pytest.mark.parametrize('levels', [None, {7}])
def test_pipeline_default_path_output(monkeypatch, levels, bundle_env):
    if bundle_env is None:
        monkeypatch.delenv('VOCAB_LADDER_BUNDLE_MODE', raising=False)
    else:
        monkeypatch.setenv('VOCAB_LADDER_BUNDLE_MODE', bundle_env)

    got = _run_pipeline(monkeypatch, levels)

    assert got == PIPELINE_GOLDEN[repr(levels)]


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

def _sent(i):
    return {'text': f'Marcus will run quickly number {i}.', 'target_word': 'run',
            'complexity_tier': 'T3'}


RENDER_CORE = {
    'pos': 'verb', 'semantic_class': 'action',
    'definition': 'to move quickly on foot',
    'primary_collocate': 'quickly', 'pronunciation': 'rʌn',
    'sentences': [_sent(i) for i in range(10)],
}


def _opts(correct, wrong):
    return [{'text': correct, 'is_correct': True}] + [
        {'text': w, 'is_correct': False} for w in wrong]


def _p2(base):
    return {
        'level_1': {'options': _opts('run', ['ran', 'rum', 'rub', 'ruin'])},
        'level_3': {'sentence_index': base, 'correct_answer': 'run',
                    'options': _opts('run', ['walk', 'jump', 'swim']),
                    'explanations': {'run': 'fits'}},
        'level_5': {'sentence_index': base, 'correct_collocate': 'quickly',
                    'options': _opts('quickly', ['slowly', 'loudly', 'softly', 'tamely']),
                    'explanations': {'quickly': 'collocate'}},
        'level_6': {'correct_sentence_index': base,
                    'wrong_sentences': [
                        {'text': f'Wrong {k} sentence.', 'explanation': f'bad {k}'}
                        for k in range(4)]},
    }


def _p3(base):
    return {
        'level_7': {'incorrect_sentence': 'Marcus run quickly.',
                    'corrected_sentence': 'Marcus runs quickly.',
                    'error_description': 'agreement',
                    'correct_sentence_indices': [base, base + 1, base + 2]},
        'level_8': {'sentence_index': base, 'correct_collocate': 'quickly',
                    'error_collocate': 'hardly', 'explanations': {'quickly': 'ok'}},
    }


class _Outcome:
    def __init__(self, verdict, confidence=7.0, reason='r'):
        self.verdict, self.confidence, self.reason = verdict, confidence, reason


def _renderer(monkeypatch, judge_calls):
    import services.exercise_generation.cloze_judge as cloze
    import services.exercise_generation.judges.collocation as coll
    import services.exercise_generation.judges.l1_distractor as l1
    import services.exercise_generation.judges.sentence_validity as sv

    r = rendermod.LadderExerciseRenderer(db=object())
    assets = {
        'prompt1_core': RENDER_CORE,
        'prompt2_exercises_A': _p2(0), 'prompt3_transforms_A': _p3(0),
        'prompt2_exercises_B': _p2(5), 'prompt3_transforms_B': _p3(5),
    }
    monkeypatch.setattr(r, '_load_assets', lambda sid: assets)
    monkeypatch.setattr(r, '_load_asset_ids', lambda sid: {'prompt1_core': 'asset-1'})
    monkeypatch.setattr(r, '_render_hant_mirror', lambda content, lid: None)
    monkeypatch.setattr(r, '_generate_l1_audio', lambda *a, **kw: 'audio://x')

    def l1_filter(db, correct, distractors, language_id):
        judge_calls.append(('l1', correct, tuple(distractors)))
        return distractors[:3], {'rejected': len(distractors) - 3, 'kept': 3}

    def cloze_filter(db, sentence_with_blank, correct_answer, distractors, language_id):
        judge_calls.append(('cloze', sentence_with_blank, correct_answer, tuple(distractors)))
        return distractors[:3], {'rejected': 0, 'kept': len(distractors)}

    def coll_filter(db, blanked, target, collocate, distractors, language_id):
        judge_calls.append(('l5', blanked, target, collocate, tuple(distractors)))
        return distractors[1:], {'rejected': 1, 'kept': len(distractors) - 1}

    def wrong(db, target, pairs, language_id):
        judge_calls.append(('sv', target, tuple(pairs)))
        return [_Outcome('reject' if i == 0 and len(pairs) > 1 else 'accept')
                for i in range(len(pairs))]

    def repair(db, text, target, correct, error, language_id):
        judge_calls.append(('l8', text, target, correct, error))
        return _Outcome('accept')

    monkeypatch.setattr(l1, 'filter_l1_distractors', l1_filter)
    monkeypatch.setattr(cloze, 'filter_distractors', cloze_filter)
    monkeypatch.setattr(coll, 'filter_collocation_distractors', coll_filter)
    monkeypatch.setattr(sv, 'judge_wrong_sentences', wrong)
    monkeypatch.setattr(coll, 'judge_collocation_repair', repair)
    return r


def _run_render(monkeypatch, levels):
    judge_calls = []
    r = _renderer(monkeypatch, judge_calls)
    random.seed(1234)
    rows = r.build_rows(sense_id=10, language_id=LANG_EN, levels=levels)
    for row in rows:
        row.pop('id', None)
    return _canon({
        'rows': rows,
        'judge_calls': judge_calls,
        'skips': [(s.type_code, s.reason) for s in r.last_skips],
    })


@pytest.mark.parametrize('bundle_env', [None, 'on', 'shadow'])
@pytest.mark.parametrize('levels', [None, {5, 6, 8}])
def test_renderer_default_path_output(monkeypatch, levels, bundle_env):
    if bundle_env is None:
        monkeypatch.delenv('VOCAB_LADDER_BUNDLE_MODE', raising=False)
    else:
        monkeypatch.setenv('VOCAB_LADDER_BUNDLE_MODE', bundle_env)

    got = _run_render(monkeypatch, levels)

    assert got == RENDER_GOLDEN[repr(levels)]


_GOLDEN = json.loads(
    (pathlib.Path(__file__).parent / 'fixtures' / 'ladder_default_path_golden.json')
    .read_text(encoding='utf-8')
)
PIPELINE_GOLDEN = _GOLDEN['pipeline']
RENDER_GOLDEN = _GOLDEN['render']
