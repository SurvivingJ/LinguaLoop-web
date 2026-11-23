"""Filtering Supabase fake + a multi-entry scenario for the dual-translation
card wiring (``services.dual_translation.cards.generate_cards_for_queued_entries``).

The ``_FakeDB`` in test_dual_translation_cards.py returns whole tables whatever
the filters, so it cannot tell several queued entries apart. This one honours
the filters, projections, ordering and paging the card wiring uses, applies
inserts/updates to its tables, emulates PostgREST's max-rows cap, and counts
round trips (``execute()`` calls).
"""

import copy


class FakeResult:
    def __init__(self, data):
        self.data = data


class FilteringQuery:
    def __init__(self, db, name):
        self._db = db
        self._name = name
        self._cols = None
        self._filters = []
        self._orders = []
        self._limit = None
        self._range = None
        self._op = 'select'
        self._payload = None

    def select(self, cols='*', **k):
        self._cols = None if cols.strip() == '*' else [c.strip() for c in cols.split(',')]
        return self

    def eq(self, col, val):
        self._filters.append(lambda r: r.get(col) == val)
        return self

    def in_(self, col, vals):
        vals = list(vals)
        self._filters.append(lambda r: r.get(col) in vals)
        return self

    def gte(self, col, val):
        self._filters.append(lambda r: r.get(col) is not None and r.get(col) >= val)
        return self

    def lte(self, col, val):
        self._filters.append(lambda r: r.get(col) is not None and r.get(col) <= val)
        return self

    def order(self, col, desc=False, **k):
        self._orders.append((col, desc))
        return self

    def limit(self, n):
        self._limit = n
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def insert(self, payload):
        self._op, self._payload = 'insert', payload
        return self

    def update(self, payload):
        self._op, self._payload = 'update', payload
        return self

    def _rows(self):
        rows = [r for r in self._db.tables.get(self._name, [])
                if all(f(r) for f in self._filters)]
        for col, desc in reversed(self._orders):
            rows.sort(key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
        if self._range is not None:
            rows = rows[self._range[0]:self._range[1] + 1]
        if self._limit is not None:
            rows = rows[:self._limit]
        return rows[:self._db.max_rows]

    def execute(self):
        self._db.round_trips += 1
        self._db.log.append((self._name, self._op))
        if self._db.fail is not None:
            # fail(table, op, payload, ids of the rows an update would touch)
            hit_ids = [r.get('id') for r in self._db.tables.get(self._name, [])
                       if all(f(r) for f in self._filters)] if self._op == 'update' else []
            self._db.fail(self._name, self._op, self._payload, hit_ids)
        if self._op == 'insert':
            payload = self._payload if isinstance(self._payload, list) else [self._payload]
            stored = []
            for row in payload:
                self._db.next_id += 1
                stored.append({'id': self._db.next_id, **copy.deepcopy(row)})
            self._db.tables.setdefault(self._name, []).extend(stored)
            return FakeResult(stored)
        if self._op == 'update':
            hit = [r for r in self._db.tables.get(self._name, [])
                   if all(f(r) for f in self._filters)]
            for r in hit:
                r.update(copy.deepcopy(self._payload))
            return FakeResult(hit)
        rows = self._rows()
        if self._cols is not None:
            rows = [{c: r[c] for c in self._cols if c in r} for r in rows]
        return FakeResult(copy.deepcopy(rows))


class FilteringDB:
    def __init__(self, tables, *, max_rows=1000, fail=None):
        self.tables = copy.deepcopy(tables)
        self.max_rows = max_rows
        self.fail = fail
        self.round_trips = 0
        self.log = []
        self.next_id = 5000

    def table(self, name):
        return FilteringQuery(self, name)


def scenario_tables():
    """One learner (u1) with queued entries covering every branch: carded,
    already carded, no error at all, latest error on an unresolvable passage,
    a duplicate subtype in another L2, a sentence window with full L1 refs,
    a window with a rejected ref, and a latest error in another L2 (B-02)."""
    return {
        'dt_error_profile_entry': [
            {'id': 100, 'user_id': 'u1', 'subtype': 'article', 'l1_language_id': 2,
             'l2_language_id': 1, 'remediation_status': 'queued'},
            {'id': 101, 'user_id': 'u1', 'subtype': 'tense', 'l1_language_id': 2,
             'l2_language_id': 1, 'remediation_status': 'queued'},
            {'id': 102, 'user_id': 'u1', 'subtype': 'collocation', 'l1_language_id': 2,
             'l2_language_id': 1, 'remediation_status': 'queued'},
            {'id': 103, 'user_id': 'u1', 'subtype': 'preposition', 'l1_language_id': 2,
             'l2_language_id': 1, 'remediation_status': 'queued'},
            {'id': 104, 'user_id': 'u1', 'subtype': 'article', 'l1_language_id': 2,
             'l2_language_id': 3, 'remediation_status': 'queued'},
            {'id': 105, 'user_id': 'u1', 'subtype': 'word_choice', 'l1_language_id': 2,
             'l2_language_id': 1, 'remediation_status': 'queued'},
            {'id': 106, 'user_id': 'u1', 'subtype': 'tense', 'l1_language_id': 2,
             'l2_language_id': 3, 'remediation_status': 'queued'},
            {'id': 107, 'user_id': 'u1', 'subtype': 'register', 'l1_language_id': 2,
             'l2_language_id': 1, 'remediation_status': 'queued'},
            # not queued / not this learner: never touched
            {'id': 108, 'user_id': 'u1', 'subtype': 'article', 'l1_language_id': 1,
             'l2_language_id': 1, 'remediation_status': 'drilling'},
            {'id': 109, 'user_id': 'u2', 'subtype': 'article', 'l1_language_id': 2,
             'l2_language_id': 1, 'remediation_status': 'queued'},
        ],
        'dt_card': [
            {'id': 1, 'user_id': 'u1', 'profile_entry_id': 107, 'card_type': 'cloze',
             'subtype': 'register', 'state': 'review'},
        ],
        'dt_passage': [
            {'id': 9, 'l2_language_id': 1, 'l2_text': 'The cat sat on the mat. It was sleepy.',
             'source_ref_id': 'T1', 'sentence_start': 0, 'sentence_end': 1},
            {'id': 10, 'l2_language_id': 1, 'l2_text': 'He go to school yesterday.',
             'source_ref_id': 'T2', 'sentence_start': None, 'sentence_end': None},
            {'id': 11, 'l2_language_id': 3, 'l2_text': 'She buyed a book. Then she read.',
             'source_ref_id': 'T3', 'sentence_start': 2, 'sentence_end': 3},
            {'id': 12, 'l2_language_id': 1, 'l2_text': 'I eat apple every day.',
             'source_ref_id': 'T1', 'sentence_start': 4, 'sentence_end': 4},
        ],
        'dt_submission': [
            {'id': 5, 'user_id': 'u1', 'passage_id': 9, 'l1_language_id': 2},
            {'id': 6, 'user_id': 'u1', 'passage_id': 10, 'l1_language_id': 2},
            {'id': 7, 'user_id': 'u1', 'passage_id': 11, 'l1_language_id': 2},
            {'id': 8, 'user_id': 'u2', 'passage_id': 9, 'l1_language_id': 2},
            {'id': 13, 'user_id': 'u1', 'passage_id': 99, 'l1_language_id': 2},
            {'id': 14, 'user_id': 'u1', 'passage_id': 12, 'l1_language_id': 2},
        ],
        'dt_error_instance': [
            {'id': 900, 'submission_id': 5, 'subtype': 'article', 'span_reference': [0, 7],
             'corrected_form': 'The cat', 'learner_form': 'cat',
             'created_at': '2026-07-01T10:00:00+00:00'},
            {'id': 901, 'submission_id': 5, 'subtype': 'article', 'span_reference': [15, 22],
             'corrected_form': 'the mat', 'learner_form': 'mat',
             'created_at': '2026-07-03T10:00:00+00:00'},
            {'id': 902, 'submission_id': 8, 'subtype': 'article', 'span_reference': [0, 7],
             'corrected_form': 'The cat', 'learner_form': 'A cat',
             'created_at': '2026-07-09T10:00:00+00:00'},
            {'id': 903, 'submission_id': 6, 'subtype': 'tense', 'span_reference': [3, 5],
             'corrected_form': 'went', 'learner_form': 'go',
             'created_at': '2026-07-02T10:00:00+00:00'},
            {'id': 904, 'submission_id': 7, 'subtype': 'tense', 'span_reference': [4, 9],
             'corrected_form': 'bought', 'learner_form': 'buyed',
             'created_at': '2026-07-05T10:00:00+00:00'},
            {'id': 905, 'submission_id': 13, 'subtype': 'preposition', 'span_reference': [0, 2],
             'corrected_form': 'at', 'learner_form': 'in',
             'created_at': '2026-07-04T10:00:00+00:00'},
            {'id': 906, 'submission_id': 14, 'subtype': 'word_choice', 'span_reference': [6, 11],
             'corrected_form': 'apples', 'learner_form': 'apple',
             'created_at': '2026-07-06T10:00:00+00:00'},
        ],
        'test_sentences': [
            {'id': 's1', 'test_id': 'T1', 'idx': 0},
            {'id': 's2', 'test_id': 'T1', 'idx': 1},
            {'id': 's5', 'test_id': 'T1', 'idx': 4},
            {'id': 's32', 'test_id': 'T3', 'idx': 2},
            {'id': 's33', 'test_id': 'T3', 'idx': 3},
        ],
        'test_sentence_references': [
            {'sentence_id': 's1', 'l1_language_id': 2, 'is_active': True,
             'review_verdict': 'pass', 'l1_text': 'The cat sat on the mat.'},
            {'sentence_id': 's2', 'l1_language_id': 2, 'is_active': True,
             'review_verdict': 'rewritten', 'l1_text': 'It was sleepy. '},
            {'sentence_id': 's1', 'l1_language_id': 1, 'is_active': True,
             'review_verdict': 'pass', 'l1_text': 'Le chat.'},
            {'sentence_id': 's5', 'l1_language_id': 2, 'is_active': True,
             'review_verdict': 'pass', 'l1_text': 'I eat apples every day.'},
            {'sentence_id': 's32', 'l1_language_id': 2, 'is_active': True,
             'review_verdict': 'pass', 'l1_text': 'She bought a book.'},
            {'sentence_id': 's33', 'l1_language_id': 2, 'is_active': True,
             'review_verdict': 'fail', 'l1_text': 'Then she read.'},
        ],
    }


def uniform_tables(k, *, extra_submissions=0):
    """``k`` queued entries for u1, each with its own subtype, error, passage
    and two-sentence window with L1 references. ``extra_submissions`` adds
    error-free submissions listed BEFORE the real ones (to push past a
    max-rows cap)."""
    tables = {'dt_error_profile_entry': [], 'dt_card': [], 'dt_passage': [],
              'dt_submission': [], 'dt_error_instance': [], 'test_sentences': [],
              'test_sentence_references': []}
    for j in range(extra_submissions):
        tables['dt_submission'].append(
            {'id': 10_000 + j, 'user_id': 'u1', 'passage_id': 1, 'l1_language_id': 2})
    for i in range(k):
        test_id = f'T{i}'
        tables['dt_error_profile_entry'].append(
            {'id': 100 + i, 'user_id': 'u1', 'subtype': f'sub{i}', 'l1_language_id': 2,
             'l2_language_id': 1, 'remediation_status': 'queued'})
        tables['dt_passage'].append(
            {'id': 200 + i, 'l2_language_id': 1, 'l2_text': f'The cat sat {i}. It slept.',
             'source_ref_id': test_id, 'sentence_start': 0, 'sentence_end': 1})
        tables['dt_submission'].append(
            {'id': 300 + i, 'user_id': 'u1', 'passage_id': 200 + i, 'l1_language_id': 2})
        tables['dt_error_instance'].append(
            {'id': 400 + i, 'submission_id': 300 + i, 'subtype': f'sub{i}',
             'span_reference': [4, 7], 'corrected_form': 'cat', 'learner_form': 'dog',
             'created_at': f'2026-07-{i + 1:02d}T00:00:00+00:00'})
        for idx in (0, 1):
            sid = f'{test_id}-{idx}'
            tables['test_sentences'].append({'id': sid, 'test_id': test_id, 'idx': idx})
            tables['test_sentence_references'].append(
                {'sentence_id': sid, 'l1_language_id': 2, 'is_active': True,
                 'review_verdict': 'pass', 'l1_text': f'L1 {i}.{idx}'})
    return tables


def written(db):
    """What a run left behind: new dt_card rows (insertion order, minus the
    fake's ids) and every entry's status."""
    new_cards = [{k: v for k, v in r.items() if k != 'id'}
                 for r in db.tables['dt_card'] if r['id'] != 1]
    statuses = {e['id']: e['remediation_status'] for e in db.tables['dt_error_profile_entry']}
    return new_cards, statuses
