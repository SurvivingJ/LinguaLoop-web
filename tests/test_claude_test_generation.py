"""scripts/run_claude_test_generation.py + per-task Claude model routing.

The runner's job is to apply a curated plan to the *unchanged* test pipeline
through headless Claude. Each test below pins one way that could silently go
wrong: a plan row lost in parsing, a brief that never reaches the prose
prompt, the phrase detector left on OpenRouter, the author model applied to
the wrong tasks, or ``--test-type`` ignored because ``run_single`` drops it.
"""

import os
import types
from types import SimpleNamespace
from uuid import uuid4

import pytest

from scripts import run_claude_test_generation as rct
from services import claude_cli_client as cli

PLAN = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                    'data', 'topic_plans', 'ja_n5_n4_topics.md')


# ── the plan ───────────────────────────────────────────────────────────────

def test_real_plan_parses_completely():
    rows = rct.parse_plan(PLAN)
    assert [r.num for r in rows] == list(range(1, 101))
    assert sum(r.level == 'N5' for r in rows) == 40
    assert sum(r.tier == 1 for r in rows) == 31
    assert sum(r.tier == 2 for r in rows) == 69
    # No N4 topic targets T1; the past-tense N5 rows target T2 (decision 1).
    assert all(r.tier == 2 for r in rows if r.level == 'N4')
    past = {3, 11, 54, 57, 62, 64, 68, 70, 82}
    assert {r.num for r in rows if r.level == 'N5' and r.tier == 2} == past


def test_every_row_has_a_category_lens_and_format():
    for r in rct.parse_plan(PLAN):
        assert r.theme in rct.THEME_CATEGORY
        assert r.fmt in rct.FORMAT_SPECS


def test_malformed_row_fails_loudly(tmp_path):
    p = tmp_path / 'plan.md'
    p.write_text('| 1 | N5 | T1 | 学校 | 学校 | School | narrative |\n', encoding='utf-8')
    with pytest.raises(ValueError, match='8 columns'):
        rct.parse_plan(str(p))


def test_unknown_theme_fails_loudly(tmp_path):
    p = tmp_path / 'plan.md'
    p.write_text('| 1 | N5 | T1 | 宇宙 | 宇宙 | Space | narrative | です |\n',
                 encoding='utf-8')
    with pytest.raises(ValueError, match='no category'):
        rct.parse_plan(str(p))


@pytest.mark.parametrize('raw,expected', [
    ('narrative (instructions)', 'narrative'),
    ('notice (forecast)', 'notice'),
    ('email/letter', 'email'),
    ('dialogue', 'dialogue'),
])
def test_format_normalisation(raw, expected):
    assert rct.normalise_format(raw) == expected


def test_parse_only():
    assert rct.parse_only('1-3,7') == {1, 2, 3, 7}
    assert rct.parse_only(None) is None
    with pytest.raises(ValueError):
        rct.parse_only('5-2')


# ── the brief ──────────────────────────────────────────────────────────────

def _row(**kw):
    base = dict(num=1, level='N5', tier=1, theme='食べ物', title_ja='朝ごはん',
                title_en='Breakfast', fmt='dialogue', grammar='〜をください')
    base.update(kw)
    return rct.PlanRow(**base)


def test_brief_length_follows_level_not_tier():
    assert (rct.build_brief(_row(level='N5', tier=2)).char_min,
            rct.build_brief(_row(level='N5', tier=2)).char_max) == (80, 150)
    assert rct.build_brief(_row(level='N4', tier=2)).char_max == 300


def test_brief_allows_past_tense_only_for_n5_rows_moved_to_t2():
    assert '過去形' not in rct.build_brief(_row(tier=1)).instruction
    assert '過去形' in rct.build_brief(_row(tier=2)).instruction
    assert '過去形' not in rct.build_brief(_row(level='N4', tier=2)).instruction


def test_brief_carries_title_format_grammar_and_style():
    b = rct.build_brief(_row())
    assert '朝ごはん' in b.instruction
    assert '〜をください' in b.instruction
    assert '話者の名前' in b.instruction          # dialogue format text
    assert b.style == 'conversational'
    assert rct.build_brief(_row(fmt='diary')).style == 'casual'
    assert rct.build_brief(_row(fmt='notice')).style == 'academic'


def test_styles_satisfy_the_tests_style_check():
    allowed = {'academic', 'conversational', 'business', 'casual', 'technical'}
    assert {s for s, _ in rct.FORMAT_SPECS.values()} <= allowed


# ── per-task model routing ─────────────────────────────────────────────────

def test_model_map_routes_author_tasks(monkeypatch):
    monkeypatch.setenv(cli.CLAUDE_CLI_MODEL_BY_TASK_ENV,
                       'prose_generation=opus,question_*=opus')
    assert cli.model_for_task('prose_generation') == 'opus'
    assert cli.model_for_task('question_literal_detail') == 'opus'
    assert cli.model_for_task('vocab_sense_selection') == cli.CLAUDE_CLI_MODEL
    assert cli.model_for_task(None) == cli.CLAUDE_CLI_MODEL


def test_model_map_typo_fails_loudly(monkeypatch):
    monkeypatch.setenv(cli.CLAUDE_CLI_MODEL_BY_TASK_ENV, 'prose_generation:opus')
    with pytest.raises(ValueError, match='expected'):
        cli.model_for_task('prose_generation')


def test_resolve_model_uses_task_map_and_stays_tagged(monkeypatch):
    from services.llm_service import _resolve_model
    monkeypatch.setenv(cli.CLAUDE_CLI_MODEL_BY_TASK_ENV, 'title_generation=opus')
    assert _resolve_model('qwen/x', None, 'claude_cli', 'title_generation') == 'claude-cli:opus'
    assert _resolve_model('qwen/x', None, 'claude_cli', 'other') == \
        f'claude-cli:{cli.CLAUDE_CLI_MODEL}'
    # OpenRouter is untouched by the map.
    assert _resolve_model('qwen/x', None, 'openrouter', 'title_generation') == 'qwen/x'


def test_configure_env_maps_exactly_the_author_tasks(monkeypatch):
    for var in ('CLAUDE_CLI_MODEL', 'CLAUDE_CLI_MODEL_BY_TASK',
                'TEST_GEN_VOCAB_SENSE_WORKERS'):
        monkeypatch.delenv(var, raising=False)
    args = SimpleNamespace(model='sonnet', author_model='opus', sense_call_workers=2)
    rct.configure_claude_env(args)
    assert os.environ['CLAUDE_CLI_MODEL'] == 'sonnet'
    assert cli.model_for_task('question_main_idea') == 'opus'
    # Not an author task: falls through to CLAUDE_CLI_MODEL (import-time constant).
    assert cli.model_for_task('topic_translation') == cli.CLAUDE_CLI_MODEL
    assert os.environ['TEST_GEN_VOCAB_SENSE_WORKERS'] == '2'


# ── the orchestrator wrappers ──────────────────────────────────────────────

class _FakeTable:
    def __init__(self, log):
        self.log = log

    def update(self, data):
        self.log.append(('update', data))
        return self

    def eq(self, col, val):
        self.log.append(('eq', col, val))
        return self

    def execute(self):
        return SimpleNamespace(data=[])


def _build(monkeypatch, briefs):
    """Construct the subclass with the base __init__ and collaborators faked."""
    from services.test_generation import orchestrator as orch_mod
    import services.llm_service as llm
    import services.vocabulary.pipeline as vp

    calls = {'prose': [], 'translate': [], 'inserted': [], 'db': [], 'vocab': []}
    claude_client = object()

    def fake_base_init(self):
        self.prose_writer = SimpleNamespace(
            client='openrouter-client',
            generate_prose=lambda **kw: calls['prose'].append(kw) or 'あ' * 100,
        )
        self.topic_translator = SimpleNamespace(
            translate=lambda **kw: calls['translate'].append(kw) or ('en', ['k']),
        )
        self.db = SimpleNamespace(
            insert_test=lambda t: calls['inserted'].append(t),
            client=SimpleNamespace(table=lambda name: _FakeTable(calls['db'])),
        )

    def fake_base_generate(self, topic, lang_config=None, category_name=None,
                           tier_id=None, test_type='listening', dry_run=False):
        concept, kws = self.topic_translator.translate(
            topic_concept=topic.concept_english, keywords=topic.keywords,
            target_language='Japanese')
        self.prose_writer.generate_prose(
            topic_concept=concept, word_count_min=0, word_count_max=500,
            extra_instruction=None)
        self.db.insert_test(SimpleNamespace(id=uuid4(), topic_id=topic.id))
        calls['generate'] = {'test_type': test_type, 'concept': concept, 'kws': kws}
        return True

    monkeypatch.setattr(orch_mod.TestGenerationOrchestrator, '__init__', fake_base_init)
    monkeypatch.setattr(orch_mod.TestGenerationOrchestrator, '_generate_test',
                        fake_base_generate)
    monkeypatch.setattr(llm, 'get_client', lambda *a, **k: claude_client)
    monkeypatch.setattr(vp, 'VocabularyExtractionPipeline',
                        lambda openai_client, db_client: calls['vocab'].append(openai_client) or 'vp')
    cls = rct.make_orchestrator_class()
    return cls(briefs, test_type='reading'), calls, claude_client


def test_phrase_detection_is_rebuilt_on_the_claude_client(monkeypatch):
    orch, calls, claude = _build(monkeypatch, {})
    assert orch.prose_writer.client is claude
    assert calls['vocab'] == [claude]
    assert orch.vocab_pipeline == 'vp'


def test_brief_reaches_prose_translation_and_style(monkeypatch):
    row = _row(num=17, fmt='dialogue')
    topic = SimpleNamespace(id=uuid4(), concept_english='Ordering', keywords=[])
    brief = rct.build_brief(row)
    orch, calls, _ = _build(monkeypatch, {str(topic.id): brief})

    assert orch._generate_test(topic=topic, tier_id=1) is True

    prose = calls['prose'][0]
    assert (prose['word_count_min'], prose['word_count_max']) == (80, 150)
    assert prose['extra_instruction'].startswith(brief.instruction)
    assert calls['translate'] == []                       # plan title used instead
    assert calls['generate']['concept'] == '朝ごはん'
    assert ('update', {'style': 'conversational'}) in calls['db']
    assert orch.test_ids[str(topic.id)] == str(calls['inserted'][0].id)
    assert calls['generate']['test_type'] == 'reading'   # run_single drops it
    assert orch._brief() is None                          # cleared afterwards


def test_topic_without_brief_takes_the_unchanged_path(monkeypatch):
    topic = SimpleNamespace(id=uuid4(), concept_english='Other', keywords=['k'])
    orch, calls, _ = _build(monkeypatch, {})
    orch._generate_test(topic=topic, tier_id=3)
    assert calls['translate'] and calls['prose'][0]['extra_instruction'] is None
    assert (calls['prose'][0]['word_count_min'], calls['prose'][0]['word_count_max']) == (0, 500)
    assert not any(op[0] == 'update' for op in calls['db'])


def test_dedup_nudge_is_kept_after_the_brief(monkeypatch):
    row = _row()
    topic = SimpleNamespace(id=uuid4(), concept_english='x', keywords=[])
    brief = rct.build_brief(row)
    orch, calls, _ = _build(monkeypatch, {str(topic.id): brief})
    orch._tls.brief = brief
    orch.prose_writer.generate_prose(word_count_min=0, word_count_max=1,
                                     extra_instruction='\nNUDGE')
    assert calls['prose'][0]['extra_instruction'] == brief.instruction + '\nNUDGE'
