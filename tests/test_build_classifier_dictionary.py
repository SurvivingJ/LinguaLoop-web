"""scripts/build_classifier_dictionary.py: the zh rebuild deletes every classifier row, so it
must write only when --apply is given (the default and --dry-run are previews)."""

import pytest

from scripts import build_classifier_dictionary as mod


class _Table:
    def __init__(self, db, name):
        self.db, self.name, self.op = db, name, 'select'

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def delete(self):
        self.op = 'delete'
        return self

    def insert(self, rows):
        self.op = 'insert'
        return self

    def execute(self):
        if self.op in ('delete', 'insert'):
            self.db.writes.append((self.op, self.name))
            return type('R', (), {'data': []})()
        if self.name == 'dim_classifier_distractor_groups':
            data = [{'id': 1, 'label': 'general'}]
        else:
            data = []
        return type('R', (), {'data': data})()


class _FakeDb:
    def __init__(self):
        self.writes = []

    def table(self, name):
        return _Table(self, name)


@pytest.fixture
def fake(monkeypatch):
    db = _FakeDb()
    monkeypatch.setattr(mod, 'get_supabase_admin', lambda: db)
    monkeypatch.setattr(mod.SupabaseFactory, 'is_initialized', staticmethod(lambda: True))
    monkeypatch.setattr(mod, '_merge_approved_curation', lambda: None)
    monkeypatch.setattr(mod, '_build_classifier_rows',
                        lambda group_id_map: [{'hanzi': 'x', 'difficulty_tier': 1}])
    monkeypatch.setattr(mod, '_build_pair_rows', lambda cmap, smap: ([{'p': 1}], []))
    return db


@pytest.mark.parametrize('argv', [[], ['--dry-run']])
def test_without_apply_nothing_is_deleted_or_inserted(fake, argv):
    mod.main(argv)
    assert fake.writes == []


def test_with_apply_it_deletes_and_reinserts(fake):
    mod.main(['--apply'])
    assert fake.writes == [
        ('delete', 'dim_classifier_noun_pairs'),
        ('delete', 'dim_classifiers'),
        ('insert', 'dim_classifiers'),
        ('insert', 'dim_classifier_noun_pairs'),
    ]


def test_apply_and_dry_run_together_is_an_error(fake):
    with pytest.raises(SystemExit) as exc:
        mod.main(['--apply', '--dry-run'])
    assert exc.value.code == 2
    assert fake.writes == []
