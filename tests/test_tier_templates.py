"""ADR-040 tier-keyed question templates (TASK-925)."""

from unittest.mock import MagicMock

import pytest

from services import prompt_service
from services.test_generation import stem_rotation
from services.test_generation.database_client import TestDatabaseClient as DatabaseClient


class Q:
    """Minimal PostgREST query double recording filters."""

    def __init__(self, rows_for):
        self.filters, self.rows_for = [], rows_for

    def select(self, *_a):
        return self

    def eq(self, k, v):
        self.filters.append(('eq', k, v)); return self

    def is_(self, k, v):
        self.filters.append(('is', k, v)); return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        return MagicMock(data=self.rows_for(self.filters))


def make_db(rows, has_column=True):
    """rows: list of dicts with task_name, language_id, tier_id, version, template_text, model, provider."""
    def rows_for(filters):
        out = []
        for r in rows:
            ok = True
            for kind, k, v in filters:
                if kind == 'eq' and r.get(k) != v:
                    ok = False
                if kind == 'is' and r.get(k) is not None:
                    ok = False
            if ok:
                out.append(r)
        return sorted(out, key=lambda r: -r['version'])

    class DB:
        def table(self, name):
            q = Q(rows_for)
            if not has_column:
                def boom(*a):
                    if a and a[0] == 'tier_id':
                        raise RuntimeError('column tier_id does not exist')
                    return q
                q.select = boom
            if name == 'dim_languages':
                q.rows_for = lambda f: [{'language_code': 'ja'}]
            return q
    return DB()


BASE = {'task_name': 'question_vocabulary_context', 'language_id': 3, 'tier_id': None,
        'version': 3, 'template_text': 'BASE', 'model': 'm', 'provider': 'p', 'is_active': True}
TIER1 = dict(BASE, tier_id=1, version=9, template_text='TIER1', model='other-model')


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    prompt_service._TIER_COLUMN.clear()
    monkeypatch.delenv('TEST_GEN_TIER_TEMPLATES', raising=False)


def client(db):
    c = DatabaseClient.__new__(DatabaseClient)
    c.client = db
    return c


def test_switch_off_serves_base_even_with_newer_tier_row():
    c = client(make_db([BASE, TIER1]))
    assert c.get_prompt_template('question_vocabulary_context', 3, tier_id=1) == 'BASE'


def test_switch_on_serves_tier_row(monkeypatch):
    monkeypatch.setenv('TEST_GEN_TIER_TEMPLATES', 'ja')
    c = client(make_db([BASE, TIER1]))
    assert c.get_prompt_template('question_vocabulary_context', 3, tier_id=1) == 'TIER1'
    assert c.get_prompt_template('question_vocabulary_context', 3, tier_id=4) == 'BASE'


def test_switch_for_other_language_only(monkeypatch):
    monkeypatch.setenv('TEST_GEN_TIER_TEMPLATES', 'zh,en')
    c = client(make_db([BASE, TIER1]))
    assert c.get_prompt_template('question_vocabulary_context', 3, tier_id=1) == 'BASE'


def test_model_resolution_ignores_tier_rows(monkeypatch):
    monkeypatch.setenv('TEST_GEN_TIER_TEMPLATES', 'on')
    cfg = prompt_service.get_template_config(make_db([BASE, TIER1]), 'question_vocabulary_context', 3)
    assert cfg['model'] == 'm' and cfg['template'] == 'BASE'
    assert prompt_service.get_template_text(make_db([BASE, TIER1]), 'question_vocabulary_context', 3) == 'BASE'


def test_works_before_migration():
    db = make_db([BASE], has_column=False)
    assert prompt_service.get_template_config(db, 'question_vocabulary_context', 3)['template'] == 'BASE'


def test_tier_templates_enabled_parsing(monkeypatch):
    for v, lang, want in [('off', 'ja', False), ('on', 'ja', True), ('all', 'zh', True),
                          ('ja,en', 'en', True), ('ja,en', 'zh', False), ('', 'ja', False)]:
        monkeypatch.setenv('TEST_GEN_TIER_TEMPLATES', v)
        assert prompt_service.tier_templates_enabled(lang) is want


def test_banded_stem_pools(monkeypatch):
    base = stem_rotation.pool_for('ja', 'main_idea', 2)
    assert base == stem_rotation.STEM_POOLS['ja']['main_idea']
    monkeypatch.setenv('TEST_GEN_TIER_TEMPLATES', 'ja')
    assert stem_rotation.pool_for('ja', 'main_idea', 2) == stem_rotation.TIER_STEM_POOLS['ja']['main_idea']['1-2']
    assert stem_rotation.pool_for('ja', 'main_idea', 3) == stem_rotation.TIER_STEM_POOLS['ja']['main_idea']['3-3']
    assert stem_rotation.pool_for('ja', 'main_idea', 5) == stem_rotation.STEM_POOLS['ja']['main_idea']
    stem = stem_rotation.select_stem('ja', 'main_idea', 'topic:1', tier=1)
    assert stem in stem_rotation.TIER_STEM_POOLS['ja']['main_idea']['1-2']


def test_beginner_ja_stems_are_kana_only():
    import re
    for stem in stem_rotation.TIER_STEM_POOLS['ja']['main_idea']['1-2']:
        assert not re.search(r'[一-鿿]', stem), stem
