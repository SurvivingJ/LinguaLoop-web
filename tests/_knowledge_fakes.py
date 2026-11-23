"""Fakes and fixtures shared by the Knowledge Report tests (TASK-1037 – TASK-1041).

``FakeDB`` stands in for the service-role Supabase client: PostgREST-style table queries over
in-memory rows (select / eq / gte / order / limit / upsert) and ``rpc()`` with canned results per
function name, recording every call (pattern: tests/test_session_merges.py ``_RpcDB``).
"""
from __future__ import annotations

import copy
from types import SimpleNamespace

from services.vocabulary import knowledge_estimate as ke

USER = '6f1c2a5e-0d7b-4f0e-9a43-2b8f9e6c1d00'
OTHER_USER = '0a9b8c7d-6e5f-4a3b-8c2d-1e0f9a8b7c6d'

FRAME_JA = [577, 425, 621, 655, 537, 283, 77]
FRAME_ZH = [303, 617, 742, 691, 664, 435, 171]
FRAMES = {'3:2': FRAME_JA, '3:1': FRAME_JA, '1:2': FRAME_ZH, '2:2': [412, 517, 737, 794, 722, 425, 147]}
DE6_JA = [[26, 16, 7], [23, 16, 5], [26, 14, 9], [24, 12, 9], [25, 9, 13], [25, 8, 15], [23, 0, 21]]

REC = [(12, 14), (10, 10), (9, 10), (8, 8), (7, 7), (6, 6), (5, 5), (5, 5), (4, 4), (3, 4), (3, 3), (2, 2),
       (1, 2), (1, 1), (1, 1), (1, 1), (1, 1)]
DIS = [(7, 9), (4, 9), (2, 3), (1, 2), (0, 2), (0, 2), (1, 1), (1, 1), (1, 1), (0, 1), (0, 1)]
PROD = [(18, 23), (12, 14), (0, 6), (3, 3), (1, 3), (2, 2), (2, 2), (0, 1), (0, 1)]


def de6_summary_rpc(**overrides) -> dict:
    """``knowledge_report_summary`` for de6fd05b/ja as tech §6.1 (MEASURED values; "…" filled in)."""
    payload = {
        'as_of': '2026-11-17T12:00:00+00:00', 'language_id': 3, 'method_version': 1,
        'tracked': {'words': 251, 'meanings': 251, 'rows': 251},
        'states': {'missed_last': 10, 'rated_known': 69, 'checked': 30, 'not_checked': 142},
        'rated_known_words': 69, 'rated_known_checked2_words': 22,
        'idle60_meanings': 95, 'last_seen_at': '2026-11-15T08:30:00+00:00',
        'activity': {'d30': {'practised_meanings': 41, 'direct_outcomes': 164, 'met_in_texts': 44},
                     'd90': {'practised_meanings': 83, 'direct_outcomes': 318, 'met_in_texts': 142}},
        'missed_recent': {'meanings': 10, 'flagged': 1},
        'groups': [{'band': 0, 'tracked_words': 3, 'rated_known_words': 0},
                   {'band': 1, 'tracked_words': 18, 'rated_known_words': 2},
                   {'band': 2, 'tracked_words': 20, 'rated_known_words': 3},
                   {'band': 3, 'tracked_words': 30, 'rated_known_words': 6},
                   {'band': 4, 'tracked_words': 40, 'rated_known_words': 9},
                   {'band': 5, 'tracked_words': 50, 'rated_known_words': 14},
                   {'band': 6, 'tracked_words': 50, 'rated_known_words': 17},
                   {'band': 7, 'tracked_words': 40, 'rated_known_words': 18}],
        'calibration': {'definition_language_id': 2, 'window_days': 180, 'bands': copy.deepcopy(DE6_JA),
                        'alltime_n': [26, 23, 26, 24, 25, 25, 23],
                        'first_answer_at': '2026-09-13T09:00:00+00:00',
                        'last_answer_at': '2026-11-15T10:00:00+00:00', 'answers': 172,
                        'since': [], 'rated_known_in_frame': 60},
        'families': [dict(family='form_recognition', **ke.sufficient_stats(REC)),
                     dict(family='semantic_discrimination', **ke.sufficient_stats(DIS)),
                     dict(family='form_production', **ke.sufficient_stats(PROD))],
        'watchlist': {'items': 0, 'rated_known': 0, 'seen_not_rated': 0, 'no_evidence': 0},
    }
    payload.update(overrides)
    return payload


def empty_summary_rpc(language_id: int = 3) -> dict:
    """A learner/language with no data: zero counts and empty arrays (never NULL, §6.1)."""
    return {
        'as_of': '2026-11-17T12:00:00+00:00', 'language_id': language_id, 'method_version': 1,
        'tracked': {'words': 0, 'meanings': 0, 'rows': 0},
        'states': {'missed_last': 0, 'rated_known': 0, 'checked': 0, 'not_checked': 0},
        'rated_known_words': 0, 'rated_known_checked2_words': 0, 'idle60_meanings': 0,
        'last_seen_at': None,
        'activity': {'d30': {'practised_meanings': 0, 'direct_outcomes': 0, 'met_in_texts': 0},
                     'd90': {'practised_meanings': 0, 'direct_outcomes': 0, 'met_in_texts': 0}},
        'missed_recent': {'meanings': 0, 'flagged': 0}, 'groups': [],
        'calibration': {'definition_language_id': None, 'window_days': 180,
                        'bands': [[0, 0, 0]] * 7, 'alltime_n': [0] * 7, 'first_answer_at': None,
                        'last_answer_at': None, 'answers': 0, 'since': [], 'rated_known_in_frame': 0},
        'families': [], 'watchlist': {'items': 0, 'rated_known': 0, 'seen_not_rated': 0, 'no_evidence': 0},
    }


class _Query:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.filters, self.order_by, self.limit_n = [], None, None
        self.upsert_row = None
        self.on_conflict = None

    def select(self, *_a, **_kw):
        return self

    def eq(self, col, val):
        self.filters.append((col, '==', val))
        return self

    def gte(self, col, val):
        self.filters.append((col, '>=', val))
        return self

    def order(self, col, desc=False):
        self.order_by = (col, desc)
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    def upsert(self, row, on_conflict=None):
        self.upsert_row, self.on_conflict = row, on_conflict
        return self

    def _match(self, row):
        for col, op, val in self.filters:
            have = row.get(col)
            if op == '==' and str(have) != str(val):
                return False
            if op == '>=' and (have is None or str(have) < str(val)):
                return False
        return True

    def execute(self):
        self.db.queries.append((self.name, list(self.filters), self.limit_n))
        if self.name in self.db.table_errors:
            raise self.db.table_errors[self.name]
        if self.upsert_row is not None:
            self.db.upserts.append((self.name, dict(self.upsert_row), self.on_conflict))
            keys = [k.strip() for k in (self.on_conflict or '').split(',') if k.strip()]
            rows = self.db.tables.setdefault(self.name, [])
            for i, existing in enumerate(rows):
                if keys and all(existing.get(k) == self.upsert_row.get(k) for k in keys):
                    rows[i] = dict(self.upsert_row)
                    break
            else:
                rows.append(dict(self.upsert_row))
            return SimpleNamespace(data=[self.upsert_row])
        rows = [dict(r) for r in self.db.tables.get(self.name, []) if self._match(r)]
        if self.order_by:
            col, desc = self.order_by
            rows.sort(key=lambda r: str(r.get(col)), reverse=desc)
        if self.limit_n is not None:
            rows = rows[:self.limit_n]
        return SimpleNamespace(data=rows)


class FakeDB:
    def __init__(self, tables=None, rpc_results=None, rpc_errors=None, table_errors=None):
        self.tables = {k: [dict(r) for r in v] for k, v in (tables or {}).items()}
        self.rpc_results = dict(rpc_results or {})
        self.rpc_errors = dict(rpc_errors or {})
        self.table_errors = dict(table_errors or {})
        self.rpcs = []
        self.queries = []
        self.upserts = []

    def table(self, name):
        return _Query(self, name)

    def rpc(self, name, params):
        self.rpcs.append((name, copy.deepcopy(params)))

        def execute():
            if name in self.rpc_errors:
                err = self.rpc_errors[name]
                raise err if isinstance(err, BaseException) else RuntimeError(err)
            result = self.rpc_results.get(name)
            if callable(result):
                result = result(params)
            return SimpleNamespace(data=copy.deepcopy(result))
        return SimpleNamespace(execute=execute)

    def rpc_calls(self, name):
        return [p for n, p in self.rpcs if n == name]


def tier_row(user_id=USER, analytics=False):
    return {'id': user_id, 'dim_subscription_tiers': {'can_access_analytics': analytics}}
