"""CSV exercise authoring infrastructure (TASK-795 .. TASK-797).

Offline: no database, no LLM. The live parity proof for the mining split is
scripts/verify_mining_split.py (12/12 ja senses byte-identical, 2026-09-19).

Run: PYTHONPATH=. python -m pytest tests/test_csv_exercise_authoring.py -q
"""

import json
import os
import sys
import types

import pytest

from services.vocabulary_ladder import asset_pipeline as ap
from services.vocabulary_ladder import stage_runner as sr


# ---------------------------------------------------------------------------
# TASK-795: _fetch_corpus_sentences = RPC + mine_sentences
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, data):
        self.data = data


class _FakeDB:
    """Just enough of the supabase client for _lemma_for_sense and the RPC."""

    def __init__(self, lemma='走る', rows=None, rpc_error=None):
        self.lemma, self.rows, self.rpc_error = lemma, rows or [], rpc_error
        self.rpc_calls = []

    def table(self, _name):
        db = self

        class _Q:
            def select(self, *_a): return self
            def eq(self, *_a): return self
            def single(self): return self
            def execute(self): return _Resp({'dim_vocabulary': {'lemma': f' {db.lemma} '}})
        return _Q()

    def rpc(self, name, params):
        self.rpc_calls.append((name, params))
        if self.rpc_error:
            raise self.rpc_error
        return types.SimpleNamespace(execute=lambda: _Resp(self.rows))


def test_fetch_delegates_rows_and_stripped_lemma_to_mine_sentences(monkeypatch):
    rows = [{'id': 't1', 'transcript': 'x', 'difficulty': 3, 'vocab_token_map': []}]
    seen = {}

    def spy(r, lemma, sense_id, language_id, tier=None):
        seen.update(rows=r, lemma=lemma, sense_id=sense_id, language_id=language_id)
        return ['sentinel']

    monkeypatch.setattr(ap, 'mine_sentences', spy)
    db = _FakeDB(rows=rows)
    out = ap.VocabAssetPipeline(db)._fetch_corpus_sentences(42, 3)

    assert out == ['sentinel']
    assert seen == {'rows': rows, 'lemma': '走る', 'sense_id': 42, 'language_id': 3}
    assert db.rpc_calls == [('tests_containing_sense', {'p_sense_id': 42, 'p_language_id': 3})]


def test_fetch_degrades_to_empty_on_rpc_failure():
    db = _FakeDB(rpc_error=RuntimeError('boom'))
    assert ap.VocabAssetPipeline(db)._fetch_corpus_sentences(42, 3) == []


def test_mine_sentences_empty_rows_and_processor_failure(monkeypatch):
    assert ap.mine_sentences([], '走る', 1, 3) == []

    from services.exercise_generation import language_processor as lp
    monkeypatch.setattr(lp.LanguageProcessor, 'for_language',
                        classmethod(lambda cls, lid: (_ for _ in ()).throw(ValueError('x'))))
    assert ap.mine_sentences([{'transcript': 'abc'}], '走る', 1, 3) == []


def test_mine_sentences_uses_token_map_surface_and_caps(monkeypatch):
    """Surface tokens come from vocab_token_map (not the lemma), the cap holds,
    duplicates are skipped, and the tier screen is applied."""
    from services.exercise_generation import language_processor as lp
    from services.vocabulary_ladder import tier_gate

    class _Proc:
        def split_sentences(self, text):
            return text.split('|')

        def contains_whole_word(self, text, tok):
            return tok in text

        def tokenize(self, text):
            return [text]

    monkeypatch.setattr(lp.LanguageProcessor, 'for_language', classmethod(lambda c, l: _Proc()))
    monkeypatch.setattr(tier_gate, 'tier_for_lemma', lambda lemma, lid: 'T3')
    monkeypatch.setattr(tier_gate, 'screen_sentence',
                        lambda text, lid, tier, target_word=None:
                        types.SimpleNamespace(passed='NG' not in text))
    monkeypatch.setattr(ap.Config, 'VOCAB_SENTENCES_PER_WORD', 2)

    rows = [{'id': 't1', 'difficulty': 3,
             'vocab_token_map': [{'token': '走った', 'sense_id': 7}, ['走る', 99]],
             'transcript': '彼は毎朝公園を走った。|NG 彼は昨日も駅まで走った。|'
                           '彼は毎朝公園を走った。|彼女は夜も川沿いを走った。|三つ目も走った文です。'}]
    out = ap.mine_sentences(rows, '走る', 7, 3)

    assert [s['text'] for s in out] == ['彼は毎朝公園を走った。', '彼女は夜も川沿いを走った。']
    assert {s['target_word'] for s in out} == {'走った'}
    assert all(s['sentence_source'] == 'mined' and s['test_id'] == 't1' for s in out)


def test_ja_pos_enum_is_unidic():
    from services.vocabulary_ladder.config import get_validation_profile
    pos = get_validation_profile(3).pos_set
    assert '形状詞' in pos and '名詞' in pos
    assert not {'名词', '动词', '形容词'} & set(pos)


# ---------------------------------------------------------------------------
# TASK-797: stage runner
# ---------------------------------------------------------------------------

def _units(n, judge=False):
    return [sr.Unit(unit_id=str(100 + i), sense_id=100 + i, body=f'prompt {i}',
                    original={'a': i} if judge else None) for i in range(n)]


def _respond(round_dir, call, payload):
    with open(os.path.join(round_dir, f'{call}.response.json'), 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False)


def test_envelope_round_trip_marks_missing_and_skips(tmp_path):
    rd = str(tmp_path / 'stage1' / 'round_01')
    manifest = sr.write_calls(rd, 1, _units(3), width=2)
    assert [c['units'] for c in manifest['calls']] == [['100', '101'], ['102']]
    prompt = open(os.path.join(rd, 'call_001.prompt.md'), encoding='utf-8').read()
    assert '### item_1\nprompt 0' in prompt and '### item_2\nprompt 1' in prompt

    _respond(rd, 'call_001', {'item_1': {'1': '名詞'}, 'item_2': {'skip': True, 'reason': 'proper noun'}})
    # call_002 never answered
    res = sr.collect_round(rd, 1)
    assert res['100']['status'] == 'ok' and res['100']['answer'] == {'1': '名詞'}
    assert res['101']['status'] == 'skip' and res['101']['reason'] == 'proper noun'
    assert res['102']['status'] == 'failed' and 'no response file' in res['102']['reason']


def test_blocked_units_are_recorded_not_dropped(tmp_path):
    rd = str(tmp_path / 'stage6' / 'round_01')
    sr.write_calls(rd, 6, [], width=4, blocked={'7': {'sense_id': 7, 'reason': 'Missing level_4'}})
    res = sr.collect_round(rd, 6)
    assert res['7']['status'] == 'failed' and res['7']['reason'] == 'Missing level_4'


@pytest.mark.parametrize('payload,ok,why', [
    ({'judged': True, 'verdict': 'accept', 'changed': False, 'answer': {'a': 0}}, True, None),
    ({'judged': True, 'verdict': 'rewrite', 'changed': True, 'answer': {'a': 9}}, True, None),
    ({'judged': True, 'verdict': 'accept', 'changed': False, 'answer': {'a': 9}}, False, 'different'),
    ({'judged': True, 'verdict': 'rewrite', 'changed': True, 'answer': {'a': 0}}, False, 'identical'),
    ({'judged': True, 'verdict': 'reject', 'changed': False}, True, None),
    ({'judged': False, 'verdict': 'accept', 'changed': False, 'answer': {'a': 0}}, False, 'judged'),
    ({'judged': True, 'verdict': 'fine', 'changed': False, 'answer': {'a': 0}}, False, 'verdict'),
])
def test_judge_changed_flag_is_checked_against_the_diff(payload, ok, why):
    status, record, reason = sr.validate_judge_payload(payload, {'a': 0})
    assert (status == 'ok') is ok
    if why:
        assert why in reason


def test_all_unchanged_judge_pass_is_a_rubber_stamp(tmp_path):
    rd = str(tmp_path / 'stage2' / 'round_01')
    sr.write_calls(rd, 2, _units(2, judge=True), width=4)
    _respond(rd, 'call_001', {
        'item_1': {'judged': True, 'verdict': 'accept', 'changed': False, 'answer': {'a': 0}},
        'item_2': {'judged': True, 'verdict': 'accept', 'changed': False, 'answer': {'a': 1}}})
    merged = sr.merge_results({}, sr.collect_round(rd, 2), 2)
    assert merged['rubber_stamp'] is True
    sr.write_json(str(tmp_path / sr.STAGE_FILES[2]), merged)
    with pytest.raises(sr.StageError, match='rubber stamp'):
        sr.require_judged(str(tmp_path), 2)

    # one real rewrite clears it
    _respond(rd, 'call_001', {
        'item_1': {'judged': True, 'verdict': 'rewrite', 'changed': True, 'answer': {'a': 5}},
        'item_2': {'judged': True, 'verdict': 'accept', 'changed': False, 'answer': {'a': 1}}})
    assert sr.merge_results({}, sr.collect_round(rd, 2), 2)['rubber_stamp'] is False


def test_missing_judge_stage_counts_as_not_run(tmp_path):
    with pytest.raises(sr.StageError, match='not run'):
        sr.require_judged(str(tmp_path), 6)


def test_rounds_never_fill_a_gap(tmp_path):
    base = tmp_path / 'stage2'
    (base / 'round_02').mkdir(parents=True)
    assert sr.next_round_dir(str(tmp_path), 2).endswith('round_03')
    assert sr.latest_round_dir(str(tmp_path), 2).endswith('round_02')


def test_capture_restores_modules_imported_inside_the_block():
    """A judge module first imported inside the capture binds call_llm at
    import time; it must not keep the recorder afterwards."""
    import services.llm_service as llm_service
    real = llm_service.call_llm
    name = 'services._csv_authoring_fake_judge'
    try:
        with sr.capture_llm_calls() as captured:
            mod = types.ModuleType(name)
            exec('from services.llm_service import call_llm', mod.__dict__)
            sys.modules[name] = mod
            with pytest.raises(sr.PromptCaptured):
                mod.call_llm('hello', task_name='judge_x', template_version=2)
        assert captured == [{'task_name': 'judge_x', 'template_version': 2, 'prompt': 'hello'}]
        assert mod.call_llm is real and llm_service.call_llm is real
        with sr.capture_llm_calls() as again:  # second block sees it too
            with pytest.raises(sr.PromptCaptured):
                mod.call_llm('second')
        assert [c['prompt'] for c in again] == ['second']
    finally:
        sys.modules.pop(name, None)


def test_replay_answers_known_prompts_and_records_misses():
    """Render-time judges are answered from stored subagent answers; an
    unanswered request is a recorded miss, never a network call."""
    import services.llm_service as llm_service
    real = llm_service.call_llm
    name = 'services._csv_authoring_fake_judge2'
    key = sr.prompt_key('judge_x', 'known')
    try:
        mod = types.ModuleType(name)
        exec('from services.llm_service import call_llm', mod.__dict__)
        sys.modules[name] = mod
        with sr.replay_llm_calls({key: {'1': {'rating': 5}}}) as misses:
            got = mod.call_llm('known', task_name='judge_x')
            got['1']['rating'] = 1  # caller mutation must not corrupt the store
            again = mod.call_llm('known', task_name='judge_x')
            with pytest.raises(sr.PromptCaptured):
                mod.call_llm('unknown', task_name='judge_x')
        assert again == {'1': {'rating': 5}}
        assert [m['prompt'] for m in misses] == ['unknown']
        assert mod.call_llm is real
    finally:
        sys.modules.pop(name, None)


def _plan(tmp_path, sids):
    item = lambda s: {'sense_id': s, 'variants': {
        'A': {'p2': {'levels': [1]}, 'p3': {'levels': [7]}, 'typed': {'particle_selection': {}}},
        'B': {'p2': {'levels': [1]}, 'p3': {'levels': [7]}, 'typed': {}}}}
    sr.write_json(str(tmp_path / sr.PLAN_FILE), {
        'language': 'ja', 'language_id': 3, 'all_sense_ids': sids + [999],
        'core_items': {str(s): {'sense_id': s, 'lemma': 'x', 'corpus_sentences': []} for s in sids},
        'exercise_items': [item(s) for s in sids], 'dropped': {'999': 'stage 1: skipped — proper noun'},
    })


def test_assemble_drops_incomplete_senses_with_reasons(tmp_path):
    _plan(tmp_path, [1, 2])
    ok = lambda ans: {'status': 'ok', 'answer': ans}
    judged = lambda v, ans: {'status': 'ok', 'verdict': v, 'changed': v == 'rewrite', 'answer': ans}
    sr.write_json(str(tmp_path / sr.STAGE_FILES[2]), {'units': {
        '1': judged('rewrite', {'8': []}), '2': judged('accept', {'8': []})}, 'rubber_stamp': False})
    units3 = {sr.unit_id(1, v, 'p2'): ok({'1': []}) for v in 'AB'}
    units4 = {sr.unit_id(1, v, 'p3'): ok({'7': {}}) for v in 'AB'}
    units5 = {sr.unit_id(1, 'A', 'typed:particle_selection'): ok({'0': []})}
    for stage, units in ((3, units3), (4, units4), (5, units5)):
        sr.write_json(str(tmp_path / sr.STAGE_FILES[stage]), {'units': units})
    full = {'A': {'p2': {'1': []}, 'p3': {'7': {}}, 'typed': {'particle_selection': {'0': []}}},
            'B': {'p2': {'1': []}, 'p3': {'7': {}}, 'typed': {}}}
    sr.write_json(str(tmp_path / sr.STAGE_FILES[6]), {'units': {
        '1': judged('rewrite', full)}, 'rubber_stamp': False})

    out = sr.assemble(str(tmp_path))
    assert out['kept'] == 1
    assert set(out['dropped']) == {'2', '999'}
    assert 'stage 2 p2' not in out['dropped']['2'] and 'stage 3 2:A:p2' in out['dropped']['2']
    ex = json.load(open(out['files']['exercises_answers'], encoding='utf-8'))
    assert ex == [{'sense_id': 1, **full}]
    batch = json.load(open(out['files']['exercises_batch'], encoding='utf-8'))
    assert batch['stage'] == 'exercises' and [i['sense_id'] for i in batch['items']] == [1]
    core = json.load(open(out['files']['core_batch'], encoding='utf-8'))
    assert core['stage'] == 'core' and core['items'][0]['sense_id'] == 1


def test_variant_parts_order():
    v = {'p2': {}, 'p3': {}, 'l4': {}, 'typed': {'synonym_antonym_match': {}, 'particle_selection': {}}}
    assert sr.variant_parts(v) == ['p2', 'p3', 'l4', 'typed:particle_selection',
                                   'typed:synonym_antonym_match']


# ---------------------------------------------------------------------------
# Typed fragments: the post-call half shared by the generator and the uploader
# ---------------------------------------------------------------------------

def test_typed_fragment_from_raw_matches_generate_contract():
    from services.vocabulary_ladder.asset_generators.syn_ant import SynonymAntonymGenerator
    gen = SynonymAntonymGenerator(None, 3)
    assert gen.fragment_from_raw({'9': 'no_relation'}, 6) == {}
    raw = {'0': [{'0': '下回る', '1': True, '2': 'a'}, {'0': '上回る', '1': False, '2': 'b'},
                 {'0': '達する', '1': False, '2': 'c'}, {'0': '増える', '1': False, '2': 'd'}],
           '1': 'antonym'}
    frag = gen.fragment_from_raw(raw, 6)
    assert list(frag) == ['synonym_antonym_match']
    body = frag['synonym_antonym_match']
    assert body['relation'] == 'antonym' and body['correct_answer'] == '下回る'
    assert body['sentence_index'] == 6
