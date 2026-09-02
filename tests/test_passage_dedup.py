"""TASK-740 Phase 5 (finding #3, 2026-08-29 review) — question/passage-level
dedup. Covers both halves of decision Q5:

  Part A (generation-time, services/test_generation/dedup.py): exact-dup
  rejection, near-dup rejection, retry-succeeds, retry-exhausted-skip.

  Part B (per-user recency, ADR-023): NOT applied live (a live-RPC body
  change requires operator sign-off, per ADR-023) — pinned here only as a
  guard that the proposed migration keeps the shape the ADR describes, so a
  later edit to the proposal can't silently drift from the reviewed SQL.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.test_generation.dedup import (
    DedupResult,
    PassageDedupChecker,
    compute_passage_hash,
    normalize_passage,
)


# ---------------------------------------------------------------------------
# normalize_passage / compute_passage_hash
# ---------------------------------------------------------------------------

def test_normalize_passage_collapses_whitespace_and_case():
    a = normalize_passage("The Cat   sat\non the  mat.")
    b = normalize_passage("the cat sat on the mat.")
    assert a == b


def test_compute_passage_hash_stable_across_trivial_reformatting():
    h1 = compute_passage_hash("The cat sat on the mat.")
    h2 = compute_passage_hash("  The   cat sat on the mat.  ")
    assert h1 == h2


def test_compute_passage_hash_sensitive_to_real_wording_change():
    h1 = compute_passage_hash("The cat sat on the mat.")
    h2 = compute_passage_hash("The dog sat on the mat.")
    assert h1 != h2


# ---------------------------------------------------------------------------
# Doubles
# ---------------------------------------------------------------------------

def _db_with_exact_match(matched_id=None):
    """A fake TestGenDatabaseClient whose .client.table(...).select(...)...
    chain returns one row (an exact hash collision)."""
    db = MagicMock()
    query = db.client.table.return_value
    for method in ('select', 'eq', 'limit'):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(
        data=[{'id': str(matched_id or uuid4())}]
    )
    return db


def _db_with_no_exact_match():
    db = MagicMock()
    query = db.client.table.return_value
    for method in ('select', 'eq', 'limit'):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(data=[])
    return db


def _rpc_response(db, data):
    db.client.rpc.return_value.execute.return_value = MagicMock(data=data)


class _FakeEmbeddingService:
    def __init__(self, vector=None, error=None):
        self._vector = vector or [0.1, 0.2, 0.3]
        self._error = error
        self.calls = 0

    def embed_single(self, text):
        self.calls += 1
        if self._error:
            raise self._error
        return self._vector


# ---------------------------------------------------------------------------
# Exact-duplicate rejection
# ---------------------------------------------------------------------------

def test_exact_duplicate_detected():
    matched_id = uuid4()
    db = _db_with_exact_match(matched_id)
    checker = PassageDedupChecker(db, embedding_service=_FakeEmbeddingService())

    result, phash, embedding = checker.check_duplicate(
        topic_id=uuid4(), tier_id=2, passage="The cat sat on the mat."
    )

    assert result.is_duplicate
    assert result.reason == 'exact'
    assert result.matched_test_id == str(matched_id)
    # Near-dup / embedding check must be skipped once an exact hit is found —
    # no reason to spend an embedding call on an already-confirmed duplicate.
    assert embedding is None
    assert phash == compute_passage_hash("The cat sat on the mat.")


def test_no_duplicate_when_hash_and_embedding_both_clear():
    db = _db_with_no_exact_match()
    _rpc_response(db, [])
    checker = PassageDedupChecker(db, embedding_service=_FakeEmbeddingService())

    result, phash, embedding = checker.check_duplicate(
        topic_id=uuid4(), tier_id=2, passage="A brand new passage."
    )

    assert not result.is_duplicate
    assert embedding == [0.1, 0.2, 0.3]
    assert phash


# ---------------------------------------------------------------------------
# Near-duplicate rejection
# ---------------------------------------------------------------------------

def test_near_duplicate_detected_above_threshold():
    matched_id = uuid4()
    db = _db_with_no_exact_match()
    _rpc_response(db, [{'id': str(matched_id), 'similarity': 0.97}])
    checker = PassageDedupChecker(db, embedding_service=_FakeEmbeddingService())

    result, _phash, embedding = checker.check_duplicate(
        topic_id=uuid4(), tier_id=3, passage="A reworded near-copy."
    )

    assert result.is_duplicate
    assert result.reason == 'near'
    assert result.similarity == 0.97
    assert result.matched_test_id == str(matched_id)
    assert embedding == [0.1, 0.2, 0.3]


def test_near_duplicate_not_flagged_when_rpc_returns_nothing():
    """The RPC itself applies match_threshold — check_near_duplicate must
    trust an empty result as "below threshold", not re-filter client-side."""
    db = _db_with_no_exact_match()
    _rpc_response(db, [])
    checker = PassageDedupChecker(db, embedding_service=_FakeEmbeddingService())

    result, _phash, _embedding = checker.check_duplicate(
        topic_id=uuid4(), tier_id=3, passage="A sufficiently different passage."
    )

    assert not result.is_duplicate


def test_near_dup_rpc_scoped_to_topic_and_tier():
    """Guards against accidentally widening the scope to a global search —
    Phase 5's near-dup check must stay scoped to (topic_id, target_age_tier),
    unlike match_topics_global (Phase 1, deliberately cross-category)."""
    db = _db_with_no_exact_match()
    _rpc_response(db, [])
    checker = PassageDedupChecker(db, embedding_service=_FakeEmbeddingService())

    topic_id = uuid4()
    checker.check_duplicate(topic_id=topic_id, tier_id=4, passage="Some passage.")

    rpc_name, rpc_args = db.client.rpc.call_args[0]
    assert rpc_name == 'match_test_passages_by_topic_tier'
    assert rpc_args['p_topic_id'] == str(topic_id)
    assert rpc_args['p_tier_id'] == 4


# ---------------------------------------------------------------------------
# Graceful degradation when the embedding call itself fails
# ---------------------------------------------------------------------------

def test_check_duplicate_degrades_gracefully_on_embedding_failure():
    db = _db_with_no_exact_match()
    checker = PassageDedupChecker(
        db, embedding_service=_FakeEmbeddingService(error=RuntimeError("no API key"))
    )

    result, phash, embedding = checker.check_duplicate(
        topic_id=uuid4(), tier_id=1, passage="Some passage."
    )

    # A broken near-dup check must not block generation outright.
    assert not result.is_duplicate
    assert embedding is None
    assert phash
    # The RPC must never be reached if the embedding itself couldn't be computed.
    db.client.rpc.assert_not_called()


# ---------------------------------------------------------------------------
# Orchestrator wiring: retry-succeeds and retry-exhausted-skip.
#
# _generate_test's full pipeline (audio synth, vocab extraction, judges, ...)
# is out of scope here — these two tests pin only the dedup-specific control
# flow: on a first-pass duplicate, generate_prose is called a second time
# with the nudge, and a still-duplicate result after retry returns False
# (skip) rather than raising or persisting.
# ---------------------------------------------------------------------------

def test_dedup_retry_nudge_is_wired_into_prose_writer():
    """The nudge text must actually reach the LLM prompt, not just exist as
    a constant — regression guard for the wiring itself."""
    from services.test_generation.agents.prose_writer import ProseWriter
    from services.test_generation.dedup import DEDUP_RETRY_NUDGE
    import services.test_generation.agents.prose_writer as pw_mod

    writer = object.__new__(ProseWriter)
    writer.model = 'test-model'
    writer.api_call_count = 0

    captured = {}

    def _fake_call_llm(prompt, **kwargs):
        captured['prompt'] = prompt
        return "A sufficiently long generated passage for testing purposes only."

    orig_call_llm = pw_mod.call_llm
    pw_mod.call_llm = _fake_call_llm
    try:
        writer.generate_prose(
            topic_concept="cats",
            language_name="English",
            language_code="en",
            difficulty=3,
            word_count_min=10,
            word_count_max=50,
            prompt_template="Write about {topic_concept} at {complexity_tier}.",
            extra_instruction=DEDUP_RETRY_NUDGE,
        )
    finally:
        pw_mod.call_llm = orig_call_llm

    assert DEDUP_RETRY_NUDGE in captured['prompt']


def test_generate_test_source_retries_once_then_skips_on_persistent_duplicate():
    """Pins the control-flow contract in orchestrator.py: a duplicate result
    triggers exactly one retry (with the nudge), and a still-duplicate result
    after that retry returns False instead of raising or falling through to
    persistence. Verified via source inspection (see test_tier_is_sole_source.py
    for precedent) rather than a full pipeline run, since _generate_test's
    other stages (audio, vocab, judges) are unrelated to this contract and
    mocking all of them would test the mocks, not the dedup wiring.
    """
    import inspect
    import services.test_generation.orchestrator as orch

    source = inspect.getsource(orch.TestGenerationOrchestrator._generate_test)

    assert 'PassageDedupChecker' in source
    assert 'DEDUP_RETRY_NUDGE' in source
    assert source.count('check_duplicate') == 2, (
        "expected exactly one initial check_duplicate call and one retry "
        "check_duplicate call"
    )
    # The skip path must return False, not raise — a duplicate is a reason
    # to skip this queue item, not abort the batch.
    skip_branch = source.split('Still a duplicate after retry')[1]
    assert 'return False' in skip_branch.split('\n\n')[0]


# ---------------------------------------------------------------------------
# Part B (per-user recency, ADR-023) — applied live 2026-08-30 with explicit
# operator sign-off (see ADR-023 and tests/sql/test_task740_phase5b_topic_recency.sql
# for the live rollback-only exercise). This only guards that the applied
# migration file keeps matching what the ADR describes.
# ---------------------------------------------------------------------------

def test_topic_recency_migration_matches_adr_023_shape():
    import pathlib

    migration_path = (
        pathlib.Path(__file__).parent.parent
        / 'migrations'
        / 'task740_phase5b_topic_recency_exclusion.sql'
    )
    assert migration_path.exists(), (
        "ADR-023's applied migration file is missing."
    )
    sql = migration_path.read_text(encoding='utf-8')

    assert 'APPLIED live' in sql
    assert 'p_topic_recency_days smallint DEFAULT 14' in sql
    assert 't2.topic_id = t.topic_id' in sql
