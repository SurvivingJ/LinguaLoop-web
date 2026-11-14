"""Japanese tagger is built once; IRT first-attempt paging has a stable order."""

import sys
import threading
import types

import services.irt.calibrator as calibrator
import services.test_generation.difficulty_scorer as scorer


def test_japanese_tagger_is_built_once_across_threads(monkeypatch):
    built = []

    class FakeTagger:
        def __init__(self):
            built.append(self)

        def __call__(self, text):
            return [types.SimpleNamespace(surface=ch) for ch in text]

    monkeypatch.setitem(sys.modules, 'fugashi', types.SimpleNamespace(Tagger=FakeTagger))
    monkeypatch.setattr(scorer, '_ja_tagger', None)

    results = []
    threads = [
        threading.Thread(target=lambda: results.append(scorer._tokenize_ja('猫 犬')))
        for _ in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(built) == 1
    assert results == [['猫', '犬']] * 8


def test_first_attempt_pages_are_ordered_by_primary_key(monkeypatch):
    monkeypatch.setattr(calibrator, 'DEFAULT_BATCH_SIZE', 2)
    data = [{'user_id': 'u', 'exercise_id': f'e{i}', 'is_correct': True} for i in range(5)]
    seen = []

    class Query:
        def __init__(self):
            self.calls = []

        def __getattr__(self, name):
            def chain(*args, **_kw):
                self.calls.append((name, args))
                return self
            return chain

        def execute(self):
            seen.append(self.calls)
            start, end = next(a for n, a in self.calls if n == 'range')
            return types.SimpleNamespace(data=data[start:end + 1])

    db = types.SimpleNamespace(table=lambda _name: Query())
    assert calibrator._load_first_attempts(db, 2) == data
    assert len(seen) == 3
    for calls in seen:
        names = [n for n, _ in calls]
        assert ('order', ('id',)) in calls
        assert names.index('order') < names.index('range')
