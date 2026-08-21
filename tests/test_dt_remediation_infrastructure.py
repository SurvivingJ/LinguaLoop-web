"""Dual Translation remediation infrastructure — TASK-731.

Covers the two backend halves of the fix:

  1. The nightly synthesis job is actually REGISTERED with APScheduler, at a
     slot that does not overlap the 04:00-04:15 chain. Before TASK-731 the
     codebase documented this job as "the nightly job" but nothing scheduled
     it, so `dt_error_profile_entry` sat empty against live
     `dt_error_instance` rows and no card was ever built.
  2. The job serialises itself across gunicorn workers on a Postgres advisory
     lock with a key distinct from the Study-Plan and IRT jobs.

Plus an end-to-end pass over the materialisation path (promoted profile entry
-> dt_card rows -> due queue -> gradeable) on the established `_FakeDB` harness.

Convention note (TASK-729): a happy-path assertion is not evidence a guard
fires. Each guard here is tested by its NEGATIVE case — the lock test asserts
`run` is never called when the lock is held, the release test asserts the
unlock happens on the exception path, and the schedule test asserts the
non-overlap rather than merely that some job exists.
"""

import re
from pathlib import Path

import pytest

from services.dual_translation import cards


REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """Chainable stand-in for supabase-py's query builder, matching the
    ``_FakeQuery`` in test_dual_translation_routes.py."""

    def __init__(self, data, recorder, table_name):
        self._data = data
        self._recorder = recorder
        self._table_name = table_name

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def or_(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def insert(self, payload):
        self._recorder.append(('insert', self._table_name, payload))
        return self

    def update(self, payload):
        self._recorder.append(('update', self._table_name, payload))
        return self

    def upsert(self, payload, **k):
        self._recorder.append(('upsert', self._table_name, payload))
        return self

    def execute(self):
        return _FakeResult(self._data)


class _FakeRpc:
    def __init__(self, data):
        self._data = data

    def execute(self):
        return _FakeResult(self._data)


class _FakeDB:
    def __init__(self, tables):
        self._tables = tables
        self.calls = []
        self.rpc_calls = []
        self.rpc_returns = {}

    def table(self, name):
        return _FakeQuery(self._tables.get(name, []), self.calls, name)

    def rpc(self, name, params):
        # supabase-py's rpc() returns a builder that must be .execute()d.
        # Returning a bare result here would make every lock call raise
        # AttributeError and silently take the helper's fail-open path — which
        # is exactly the false green this suite is meant to prevent.
        self.rpc_calls.append(name)
        return _FakeRpc(self.rpc_returns.get(name, [True]))


# ===========================================================================
# 1. The job is scheduled — and does not collide with the 04:00-04:15 chain
# ===========================================================================

class TestSchedulerRegistration:
    """The regression this whole task exists for: `_initialize_scheduler` must
    actually register the DT synthesis job."""

    def _jobs(self):
        """Register the real scheduler against a stub app and return its jobs.

        Uses APScheduler's own registry rather than parsing app.py, so a job
        that is written but (say) never reached still fails this test.
        """
        from apscheduler.schedulers.background import BackgroundScheduler
        import app as app_module

        captured = {}

        class _StubLogger:
            def info(self, *a, **k):
                pass

            def warning(self, *a, **k):
                pass

            def exception(self, *a, **k):
                pass

            def error(self, *a, **k):
                pass

        class _StubApp:
            logger = _StubLogger()

        stub = _StubApp()

        # Keep the scheduler from actually firing anything.
        real_start = BackgroundScheduler.start
        BackgroundScheduler.start = lambda self, *a, **k: captured.setdefault('sched', self)
        try:
            app_module._initialize_scheduler(stub)
        finally:
            BackgroundScheduler.start = real_start

        return {j.id: j for j in stub.scheduler.get_jobs()}

    def test_dt_synthesis_job_is_registered(self, monkeypatch):
        monkeypatch.delenv('DISABLE_SCHEDULER', raising=False)
        jobs = self._jobs()
        assert 'dt_error_synthesis_nightly' in jobs, (
            'DT nightly synthesis is not registered with APScheduler. This is '
            'the TASK-731 regression: routes/dual_translation.py documents it '
            'as "the nightly job" but nothing ran it, so no error cluster was '
            'ever promoted and no dt_card was ever built.'
        )

    def test_dt_synthesis_runs_before_the_04xx_chain(self, monkeypatch):
        """03:50, ahead of IRT (04:00) through queue-drain (04:15). The window
        matters: promotions must land before the morning's first GET /next."""
        monkeypatch.delenv('DISABLE_SCHEDULER', raising=False)
        jobs = self._jobs()

        def hhmm(job_id):
            fields = {f.name: str(f) for f in jobs[job_id].trigger.fields}
            return int(fields['hour']), int(fields['minute'])

        dt_hour, dt_minute = hhmm('dt_error_synthesis_nightly')
        assert (dt_hour, dt_minute) == (3, 50)

        # Strictly earlier than every job in the 04:xx chain.
        for other in (
            'irt_calibration_nightly',
            'exercise_time_estimate_refresh',
            'slug_health_nightly',
            'generation_queue_drain_nightly',
        ):
            assert (dt_hour, dt_minute) < hhmm(other), f'overlaps {other}'

    def test_disable_scheduler_still_honoured(self, monkeypatch):
        """The opt-out must keep working — tests and CLI runs rely on it."""
        import app as app_module

        monkeypatch.setenv('DISABLE_SCHEDULER', 'true')

        class _StubLogger:
            def info(self, *a, **k):
                pass

        class _StubApp:
            logger = _StubLogger()

        stub = _StubApp()
        app_module._initialize_scheduler(stub)
        assert not hasattr(stub, 'scheduler')


# ===========================================================================
# 2. Cross-worker advisory lock
# ===========================================================================

class TestSynthesisAdvisoryLock:

    def test_skips_entirely_when_another_worker_holds_the_lock(self, monkeypatch):
        """The guard's negative case: a held lock must prevent the sweep from
        running at all, not merely log something."""
        from scripts import dt_nightly_synthesis as mod

        db = _FakeDB({})
        db.rpc_returns['pg_try_advisory_lock_for_dt_synthesis'] = [False]
        monkeypatch.setattr(mod, 'get_supabase_admin', lambda: db)

        ran = []
        monkeypatch.setattr(mod, 'run', lambda *a, **k: ran.append(True) or [])

        summary = mod.run_nightly_synthesis()

        assert summary == {'skipped': True, 'reason': 'lock_held'}
        assert ran == [], 'synthesis ran despite the advisory lock being held'
        # Nothing to unlock — we never took it.
        assert 'pg_advisory_unlock_for_dt_synthesis' not in db.rpc_calls

    def test_runs_and_summarises_when_the_lock_is_free(self, monkeypatch):
        from scripts import dt_nightly_synthesis as mod

        db = _FakeDB({})
        db.rpc_returns['pg_try_advisory_lock_for_dt_synthesis'] = [True]
        monkeypatch.setattr(mod, 'get_supabase_admin', lambda: db)
        monkeypatch.setattr(mod, 'run', lambda *a, **k: [
            {'remediation_status': 'queued'},
            {'remediation_status': 'monitoring'},
        ])

        summary = mod.run_nightly_synthesis()

        assert summary['skipped'] is False
        assert summary['profile_rows'] == 2
        assert summary['queued'] == 1
        assert 'pg_advisory_unlock_for_dt_synthesis' in db.rpc_calls

    def test_lock_is_released_even_when_the_sweep_raises(self, monkeypatch):
        """A crash mid-sweep must not strand the lock — otherwise every later
        night silently no-ops on a lock nobody holds a session for."""
        from scripts import dt_nightly_synthesis as mod

        db = _FakeDB({})
        db.rpc_returns['pg_try_advisory_lock_for_dt_synthesis'] = [True]
        monkeypatch.setattr(mod, 'get_supabase_admin', lambda: db)

        def _boom(*a, **k):
            raise RuntimeError('synthesis blew up')

        monkeypatch.setattr(mod, 'run', _boom)

        with pytest.raises(RuntimeError):
            mod.run_nightly_synthesis()

        assert 'pg_advisory_unlock_for_dt_synthesis' in db.rpc_calls

    def test_falls_through_when_the_lock_rpc_is_not_deployed(self, monkeypatch):
        """Same fail-open shape as the study-plan and IRT helpers: a missing
        RPC must not stop the sweep, because the upsert is idempotent."""
        from scripts import dt_nightly_synthesis as mod

        class _NoRpcDB(_FakeDB):
            def rpc(self, name, params):
                raise RuntimeError('function does not exist')

        db = _NoRpcDB({})
        monkeypatch.setattr(mod, 'get_supabase_admin', lambda: db)
        monkeypatch.setattr(mod, 'run', lambda *a, **k: [])

        summary = mod.run_nightly_synthesis()
        assert summary['skipped'] is False


class TestAdvisoryLockKey:

    def _keys_in(self, filename):
        sql = (REPO_ROOT / 'migrations' / filename).read_text(encoding='utf-8')
        return set(re.findall(r'pg_(?:try_)?advisory_(?:un)?lock\((\d+)::bigint\)', sql))

    def test_dt_key_is_distinct_from_the_other_nightly_jobs(self):
        """A shared key would make two unrelated sweeps block each other — the
        DT job would silently never run on a night IRT ran long."""
        dt_keys = self._keys_in('dt_synthesis_advisory_lock.sql')
        assert dt_keys == {'1146377081'}
        assert dt_keys.isdisjoint(self._keys_in('study_plan_advisory_lock.sql'))
        assert '8901234567890123' not in dt_keys  # the IRT calibrator's key

    def test_lock_and_unlock_use_the_same_key(self):
        sql = (REPO_ROOT / 'migrations' / 'dt_synthesis_advisory_lock.sql').read_text(
            encoding='utf-8'
        )
        assert 'pg_try_advisory_lock(1146377081::bigint)' in sql
        assert 'pg_advisory_unlock(1146377081::bigint)' in sql


# ===========================================================================
# 3. End to end: promoted entry -> dt_card rows -> due queue -> gradeable
# ===========================================================================

GOLD_L2 = 'The cat sat on the mat. It was sleepy.'
L1_TEXT = 'El gato se sentó en la alfombra.'


def _e2e_tables():
    """Tables shaped as the real pipeline leaves them the morning after a
    synthesis run promoted one cluster to ``queued``."""
    return {
        'dt_error_profile_entry': [
            {'id': 77, 'subtype': 'article', 'remediation_status': 'queued',
             'l2_language_id': 2},
        ],
        # No dt_card rows yet — this is the state the missing migration hid.
        'dt_card': [],
        'dt_submission': [{'id': 5, 'passage_id': 9, 'l1_language_id': 1,
                           'user_id': 'u1'}],
        'dt_error_instance': [{
            'id': 31, 'submission_id': 5, 'span_reference': [4, 7],
            'corrected_form': 'the cat', 'learner_form': 'cat',
            'subtype': 'article',
        }],
        'dt_passage': [{'id': 9, 'l2_text': GOLD_L2}],
        'dt_passage_reference': [{'l1_text': L1_TEXT}],
    }


class TestCardMaterialisationEndToEnd:

    def test_queued_entry_produces_both_card_types_and_flips_to_drilling(self):
        db = _FakeDB(_e2e_tables())

        carded = cards.generate_cards_for_queued_entries(db, 'u1')

        assert carded == 1
        inserts = [c for c in db.calls if c[0] == 'insert' and c[1] == 'dt_card']
        assert len(inserts) == 1
        rows = inserts[0][2]
        assert {r['card_type'] for r in rows} == {
            cards.CARD_TYPE_CLOZE, cards.CARD_TYPE_ISOLATE_RETRANSLATE
        }
        for r in rows:
            assert r['user_id'] == 'u1'
            assert r['profile_entry_id'] == 77
            assert r['origin_error_id'] == 31
            assert r['state'] == 'new'

        updates = [c for c in db.calls
                   if c[0] == 'update' and c[1] == 'dt_error_profile_entry']
        assert updates and updates[0][2] == {'remediation_status': 'drilling'}

    def test_answer_target_is_corrected_form_end_to_end(self):
        """The pedagogically critical invariant, pinned at the row that
        actually reaches dt_card — not just at the pure builder."""
        db = _FakeDB(_e2e_tables())
        cards.generate_cards_for_queued_entries(db, 'u1')

        rows = [c for c in db.calls
                if c[0] == 'insert' and c[1] == 'dt_card'][0][2]
        for r in rows:
            payload = r['prompt_payload']
            assert payload['answer'] == 'the cat'
            assert 'learner_form' not in payload
            assert 'cat' != payload['answer']
            # The learner's own wrong form must not appear as any value.
            assert 'cat' not in [v for v in payload.values() if v == 'cat']

    def test_already_carded_entry_is_not_duplicated(self):
        """Idempotency guard's negative case: the route calls this on every
        GET /next, so a second pass must insert nothing."""
        tables = _e2e_tables()
        tables['dt_card'] = [{'profile_entry_id': 77}]
        db = _FakeDB(tables)

        carded = cards.generate_cards_for_queued_entries(db, 'u1')

        assert carded == 0
        assert not [c for c in db.calls
                    if c[0] == 'insert' and c[1] == 'dt_card']

    def test_due_queue_serves_the_materialised_cards_interleaved(self):
        """The route path: _fetch_due_cards shape -> interleave -> one card
        with everything the renderer needs."""
        from routes import dual_translation as dt_routes

        tables = _e2e_tables()
        tables['dt_card'] = [
            {'id': 101, 'card_type': 'cloze', 'subtype': 'article',
             'prompt_payload': {'prompt': 'The ____ sat on the mat.',
                                'answer': 'the cat'},
             'state': 'new', 'due_date': None},
            {'id': 102, 'card_type': 'isolate_retranslate', 'subtype': 'tense',
             'prompt_payload': {'l1_context': L1_TEXT,
                                'target_sentence': 'The cat sat on the mat.',
                                'answer': 'the cat'},
             'state': 'new', 'due_date': None},
        ]
        db = _FakeDB(tables)

        due = dt_routes._fetch_due_cards(db, 'u1')
        interleaved = cards.interleave_by_subtype(due)

        assert len(interleaved) == 2
        # Subtypes alternate, never blocked.
        assert [c['subtype'] for c in interleaved] == ['article', 'tense']
        for c in interleaved:
            assert set(c) == {'card_id', 'card_type', 'subtype',
                              'prompt_payload', 'state', 'due_date'}
            assert c['prompt_payload']['answer'] == 'the cat'

    def test_practice_injection_carries_card_id_not_the_synthetic_id(self):
        """The Practice Engine item must carry `card_id` so the FE grades to
        POST /cards/<id>/review. Its string `id` is a synthetic session key and
        must never be used as the card id."""
        item = cards._to_practice_item({
            'id': 101, 'card_type': 'cloze', 'subtype': 'article',
            'prompt_payload': {'prompt': 'a ____ b', 'answer': 'the cat'},
            'state': 'new', 'due_date': None,
        })

        assert item['card_id'] == 101
        assert item['id'] == 'dt-error-101'
        assert item['is_error_exercise'] is True
        assert item['word_sense_id'] is None
        assert item['exercise_type'] == cards.ERROR_EXERCISE_TYPE


# ===========================================================================
# 4. The migration that was written but never applied
# ===========================================================================

class TestMigrationsExist:

    def test_dt_cards_migration_defines_both_tables(self):
        sql = (REPO_ROOT / 'migrations' / 'dt_cards.sql').read_text(encoding='utf-8')
        assert 'CREATE TABLE IF NOT EXISTS public.dt_card' in sql
        assert 'CREATE TABLE IF NOT EXISTS public.dt_card_review' in sql

    def test_dt_card_constrains_card_type_to_the_two_rendered_types(self):
        """If a third card_type is ever added, the renderer must be updated in
        the same change — this test is the tripwire."""
        sql = (REPO_ROOT / 'migrations' / 'dt_cards.sql').read_text(encoding='utf-8')
        assert "card_type IN ('cloze', 'isolate_retranslate')" in sql
        assert {cards.CARD_TYPE_CLOZE, cards.CARD_TYPE_ISOLATE_RETRANSLATE} == {
            'cloze', 'isolate_retranslate'
        }


# ===========================================================================
# 5. Misaligned grader spans (found by live verification, TASK-731)
# ===========================================================================

class TestClozeAnswerLeakGuard:
    """Live data has `dt_error_instance` rows whose `span_reference` points at
    a different clause than `corrected_form`. Blanking the span then hides an
    unrelated clause and leaves the answer sitting in the prompt — a copying
    exercise, not productive recall.

    Verbatim strings below are the real live rows (dt_card 1 and 3, user
    de6fd05b, passage 1) that exposed this.
    """

    ZH_PASSAGE = (
        '我最喜欢的T恤是一件非常特别的衣服。'
        '它不是那种很贵的牌子，也不是最新款式的，但它是我所有衣服里最喜欢的。'
    )

    def test_realigns_a_span_that_misses_its_corrected_form(self):
        # span [23,29] covers '很贵的牌子，' but corrected_form is a different clause.
        error = {
            'span_reference': [23, 29],
            'corrected_form': '也不是最新款式的',
            'learner_form': '也不是最新的风格',
            'subtype': 'word_choice',
        }
        card = cards.build_cloze_card(error, self.ZH_PASSAGE)

        assert card['answer'] == '也不是最新款式的'
        assert card['answer'] not in card['prompt'], 'prompt leaks the answer'
        assert card['prompt'].count(cards.CLOZE_BLANK) == 1
        # The unrelated clause the raw span pointed at must stay visible.
        assert '很贵的牌子' in card['prompt']

    def test_leaking_cloze_is_dropped_but_isolate_still_covers_the_subtype(self):
        """If realignment cannot save the card, it must not be emitted — and the
        cluster must still get remediation from the other card type."""
        # corrected_form appears twice, so realignment refuses to guess; the
        # raw span points elsewhere, so the answer survives in the prompt.
        gold = 'aa bb cc bb dd.'
        error = {
            'span_reference': [0, 2],       # 'aa'
            'corrected_form': 'bb',
            'learner_form': 'zz',
            'subtype': 'word_choice',
        }
        leaking = cards.build_cloze_card(error, gold)
        assert leaking['answer'] in leaking['prompt'], 'fixture no longer leaks'

        built = cards.build_cards(error, gold, 'L1 context')
        types = {c['card_type'] for c in built}
        assert cards.CARD_TYPE_CLOZE not in types
        assert cards.CARD_TYPE_ISOLATE_RETRANSLATE in types

    def test_aligned_span_is_left_alone(self):
        """The guard must not perturb the normal case."""
        gold = 'The cat sat on the mat.'
        error = {
            'span_reference': [4, 7],
            'corrected_form': 'cat',
            'learner_form': 'cats',
            'subtype': 'agreement',
        }
        card = cards.build_cloze_card(error, gold)
        assert card['prompt'] == 'The ____ sat on the mat.'

    def test_ambiguous_realignment_is_refused(self):
        """Two verbatim occurrences: blanking a guessed one could hide the wrong
        instance, so the grader's span is kept."""
        sentence = 'x bb y bb z.'
        assert cards._blank_span_for(sentence, [0, 1], 'bb') == [0, 1]

    def test_realignment_requires_a_verbatim_occurrence(self):
        sentence = 'The cat sat.'
        assert cards._blank_span_for(sentence, [4, 7], 'the cat') == [4, 7]
