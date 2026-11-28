"""Offline test bundles: slot plan, assembly, upload selection, record persistence."""

import json
import lzma
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest

from scripts import export_offline_tests as exp
from scripts import upload_offline_tests as up


def test_slots_are_broad_before_deep_and_tier_balanced():
    topics = [f't{i}' for i in range(8)]
    slots = exp.build_slots(topics, [1, 2, 3, 4], 16)
    assert len(slots) == 16 and len({s['key'] for s in slots}) == 16
    # every topic appears twice before any appears a third time
    per_topic = {}
    for s in slots:
        per_topic[s['topic_id']] = per_topic.get(s['topic_id'], 0) + 1
    assert set(per_topic.values()) == {2}
    per_tier = {}
    for s in slots:
        per_tier[s['tier']] = per_tier.get(s['tier'], 0) + 1
    assert set(per_tier.values()) == {4}
    assert [s['topic_id'] for s in slots[:8]] == topics


def test_slot_angles_differ_across_tiers_of_a_topic():
    slots = exp.build_slots(['a'], [1, 2, 3, 4], 4)
    assert len({s['angle'] for s in slots}) == 4


def test_shards_partition_the_slots():
    slots = exp.build_slots([f't{i}' for i in range(7)], [1, 2, 3, 4], 25)
    parts = [exp.shard_slots(slots, 3, k) for k in range(3)]
    keys = [s['key'] for part in parts for s in part]
    assert sorted(keys) == sorted(s['key'] for s in slots)
    assert len(keys) == len(set(keys))


def _record(key, h, tier=2, elo=1250):
    return {'record_version': 1, 'slot_key': key, 'passage_hash': h,
            'tier_id': tier, 'seeded_elo': elo, 'topic_id': key.split(':')[0],
            'questions': [{'question': 'q'}], 'generation_model': 'm',
            'slug': key, 'transcript': 't', 'test_id': str(uuid4())}


def test_assemble_dedups_and_writes_manifest(tmp_path, capsys):
    shards = tmp_path / 'shards'
    shards.mkdir()
    rows0 = [_record('a:T1', 'h1', 1, 1000), _record('a:T2', 'h2', 2, 1250)]
    rows1 = [_record('b:T1', 'h2'), _record('a:T1', 'h9')]  # same hash; repeat slot
    (shards / 'shard_0.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows0))
    (shards / 'shard_1.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows1))
    (shards / 'shard_1.failures.jsonl').write_text(json.dumps({'key': 'c:T1'}) + '\n')

    args = SimpleNamespace(out=str(tmp_path), language='ja')
    assert exp.assemble(args) == 0

    with lzma.open(tmp_path / 'tests.jsonl.xz', 'rt', encoding='utf-8') as f:
        got = [json.loads(line) for line in f]
    assert [r['slot_key'] for r in got] == ['a:T1', 'a:T2']   # b:T1 dropped as dup hash
    manifest = json.loads((tmp_path / 'manifest.json').read_text())
    assert manifest['tests'] == 2 and manifest['failed_slots'] == 1
    assert manifest['seeded_elo'] == {'min': 1000, 'median': 1250, 'max': 1250}
    manifest2, records = up.load_bundle(str(tmp_path))
    assert len(records) == 2 and manifest2['sha256'] == manifest['sha256']


def test_upload_select_filters():
    rs = [_record('a:T1', '1', 1, 900), _record('a:T2', '2', 2, 1250),
          _record('a:T3', '3', 3, 1400)]
    assert len(up.select(rs, tiers={2, 3})) == 2
    assert [r['tier_id'] for r in up.select(rs, min_elo=1200, max_elo=1300)] == [2]
    assert len(up.select(rs, limit=1)) == 1


def test_db_call_logging_switch(monkeypatch):
    from services.llm_service import db_call_logging_enabled
    monkeypatch.delenv('LLM_CALLS_DB_LOG', raising=False)
    assert db_call_logging_enabled()
    for off in ('0', 'false', 'OFF'):
        monkeypatch.setenv('LLM_CALLS_DB_LOG', off)
        assert not db_call_logging_enabled()


def test_llm_call_log_skips_db_but_writes_csv(monkeypatch):
    import services.llm_service as svc
    import services.supabase_factory as sf
    csv_rows = []
    monkeypatch.setenv('LLM_CALLS_DB_LOG', '0')
    monkeypatch.setattr(sf, 'get_supabase_admin', lambda: pytest.fail('DB touched'))
    monkeypatch.setattr(svc, '_log_llm_call_csv', csv_rows.append)
    svc._log_llm_call(
        pipeline='p', task_name='t', template_version=None, model='m',
        temperature=None, seed=None, prompt_hash=None, raw_response='x',
        parsed_ok=True, schema_ok=True, judge_verdict=None, judge_confidence=None,
        latency_ms=1, artifact_id=None, cost_usd=None,
    )
    assert len(csv_rows) == 1


class _FakeTable:
    def __init__(self, log, name):
        self.log, self.name = log, name

    def update(self, data):
        self.log.append((self.name, 'update', data))
        return self

    def insert(self, data):
        self.log.append((self.name, 'insert', data))
        return self

    def eq(self, *a):
        return self

    def execute(self):
        return SimpleNamespace(data=[])


def test_persist_exported_test_saves_record_through_live_path(monkeypatch):
    from services.test_generation import orchestrator as om
    log, inserted = [], {}
    db = SimpleNamespace(
        client=SimpleNamespace(table=lambda name: _FakeTable(log, name)),
        get_language_config_by_code=lambda code: SimpleNamespace(id=3, language_code='ja'),
        insert_test=lambda t: inserted.setdefault('test', t),
        get_question_type_id=lambda code: 7,
        insert_questions=lambda qs: inserted.setdefault('questions', qs),
        insert_test_skill_ratings=lambda **kw: inserted.setdefault('ratings', kw),
    )
    orch = object.__new__(om.TestGenerationOrchestrator)
    orch.db = db
    orch.audio_synthesizer = SimpleNamespace(
        generate_and_upload=lambda **kw: inserted.setdefault('audio', kw) and 'https://a/x.mp3')
    vocab = []
    orch._generate_vocabulary = lambda **kw: vocab.append(kw)
    monkeypatch.setattr(om, '_write_review_queue_rows', lambda **kw: None)
    monkeypatch.setattr(om, 'get_test_gen_config', lambda: SimpleNamespace(system_user_id='sys'))

    record = {
        'record_version': 1, 'test_id': str(uuid4()), 'slug': 'ja-d3-x',
        'language_id': 3, 'language_code': 'ja', 'language_name': 'Japanese',
        'topic_id': str(uuid4()), 'topic_concept_english': 'x', 'tier_id': 2,
        'legacy_difficulty': 3, 'transcript': '本文です。', 'title': 'T',
        'initial_elo': 1250, 'seeded_elo': 1250, 'age_tier_score': 1.0,
        'age_tier_confidence': None, 'age_tier_probabilities': {'T2': 1.0},
        'age_tier_model': 'm', 'age_tier_calibration': 'claude-uncalibrated',
        'passage_hash': 'h', 'generation_model': 'claude-cli:x',
        'test_type': 'listening', 'voice': 'ja-JP-NanamiNeural', 'tts_speed': 0.9,
        'questions': [{'question': 'Q?', 'choices': ['a', 'b', 'c', 'd'],
                       'answer': 'b', 'type_code': 'literal_detail',
                       'distractor_types': ['s', None, 'g', 'c']}],
        'pinyin_payload': None, 'pitch_payload': {'p': 1},
        'furigana_payload': {'f': 1},
    }
    orch.persist_exported_test(record)

    t = inserted['test']
    assert str(t.id) == record['test_id'] and t.audio_url == 'https://a/x.mp3'
    assert t.target_age_tier == 2 and t.age_tier_calibration == 'claude-uncalibrated'
    assert t.generation_model == 'claude-cli:x' and t.gen_user == 'sys'
    assert inserted['audio']['voice'] == 'ja-JP-NanamiNeural' and inserted['audio']['speed'] == 0.9
    (q,) = inserted['questions']
    assert q.question_id == 'ja-d3-x-q1' and q.answer == 'b' and q.question_type_id == 7
    assert inserted['ratings']['has_audio'] is True
    assert ('tests', 'update', {'pitch_payload': {'p': 1}, 'furigana_payload': {'f': 1}}) in log
    assert vocab and vocab[0]['transcript'] == '本文です。'


def test_persist_rejects_unknown_record_version():
    from services.test_generation import orchestrator as om
    orch = object.__new__(om.TestGenerationOrchestrator)
    with pytest.raises(ValueError, match='record_version'):
        orch.persist_exported_test({'record_version': 99})


def test_angle_instruction_mentions_angle():
    assert 'a comparison' in exp.angle_instruction(exp.ANGLES[4])
    assert os.path.basename(exp.__file__) == 'export_offline_tests.py'


def test_config_validation_keys(monkeypatch):
    from services.test_generation.config import TestGenConfig
    cfg = TestGenConfig()
    cfg.openrouter_api_key, cfg.openai_api_key = None, None
    monkeypatch.delenv('LLM_FORCE_PROVIDER', raising=False)
    assert cfg.validate() is False                     # OpenRouter still required
    monkeypatch.setenv('LLM_FORCE_PROVIDER', 'claude_cli')
    assert cfg.validate() is True                      # no OpenRouter, no OpenAI needed


def test_slots_exclude_prior_keys_and_shift_angles():
    base = exp.build_slots(['a', 'b'], [1, 2, 3], 6)
    shifted = exp.build_slots(['a', 'b'], [1, 2, 3], 6, angle_offset=3)
    assert [s['key'] for s in base] == [s['key'] for s in shifted]
    assert all(x['angle'] != y['angle'] for x, y in zip(base, shifted))
    excl = exp.build_slots(['a', 'b'], [1, 2, 3], 6, exclude=frozenset({'a:T1', 'b:T3'}))
    assert {s['key'] for s in excl} == {'a:T2', 'a:T3', 'b:T1', 'b:T2'}


def test_load_prior_bundles_reads_xz(tmp_path):
    with lzma.open(tmp_path / 'tests.jsonl.xz', 'wt', encoding='utf-8') as f:
        f.write(json.dumps({'slot_key': 'a:T1', 'passage_hash': 'h'}) + '\n')
    assert exp.load_prior_bundles([str(tmp_path)]) == [{'slot_key': 'a:T1', 'passage_hash': 'h'}]


def test_variant_slots_have_distinct_keys():
    base = exp.build_slots(['a'], [1, 2], 2)
    v2 = exp.build_slots(['a'], [1, 2], 2, variant=2, angle_offset=5,
                         exclude=frozenset(s['key'] for s in base))
    assert [s['key'] for s in v2] == ['a:T1:v2', 'a:T2:v2']
    assert exp.slot_key('a', 3) == 'a:T3'


def test_angle_instruction_appends_note():
    text = exp.angle_instruction(exp.ANGLES[0], ' Use HSK 7-9 vocabulary. ')
    assert text.endswith('\nUse HSK 7-9 vocabulary.')
    assert exp.angle_instruction(exp.ANGLES[0]).endswith('length given above.')
