"""TASK-740 Phase 3 guardrail: global (cross-category) topic novelty search.

Review 2026-08-29 finding #1: a near-duplicate topic can sail through as
"novel" because the similarity pool used by check_novelty()/find_similar_topics()
never crossed category_id (the recurring "cat t-shirt" topic reappearing under
a different category). match_topics_global (migrations/
task740_collapse_difficulty_to_tier_schema.sql) is the category-unscoped twin
of match_topics; this file pins the Python wiring on top of it:

  - TopicDatabaseClient.find_similar_topics(scope='global') calls
    match_topics_global instead of match_topics, and does NOT require a real
    category_id to do so.
  - ArchivistAgent.check_novelty(scope='global') no longer strictly requires
    category_id to run the search — a near-duplicate topic filed under a
    DIFFERENT category_id must now be caught as non-novel, which it was not
    under the old category-scoped-only path.
"""

from unittest.mock import MagicMock

import pytest

from services.topic_generation.database_client import TopicDatabaseClient
from services.topic_generation.agents.archivist import ArchivistAgent


def _make_client_with_mock_supabase():
    client = TopicDatabaseClient.__new__(TopicDatabaseClient)  # skip __init__ (no real Supabase)
    client.client = MagicMock()
    client._lens_cache = None
    client._language_cache = None
    client._status_cache = None
    return client


# ---------------------------------------------------------------------------
# database_client.find_similar_topics: scope routes to the right RPC
# ---------------------------------------------------------------------------

def test_find_similar_topics_default_scope_calls_match_topics():
    client = _make_client_with_mock_supabase()
    rpc_result = MagicMock()
    rpc_result.execute.return_value = MagicMock(data=[])
    client.client.rpc.return_value = rpc_result

    client.find_similar_topics(category_id=5, embedding=[0.1], threshold=0.85)

    client.client.rpc.assert_called_once()
    rpc_name, rpc_args = client.client.rpc.call_args[0]
    assert rpc_name == 'match_topics'
    assert rpc_args['query_category'] == 5


def test_find_similar_topics_global_scope_calls_match_topics_global_without_category():
    client = _make_client_with_mock_supabase()
    rpc_result = MagicMock()
    rpc_result.execute.return_value = MagicMock(data=[
        {'id': 'abc', 'concept_english': 'cat t-shirt', 'category_id': 99, 'similarity': 0.93}
    ])
    client.client.rpc.return_value = rpc_result

    results = client.find_similar_topics(
        category_id=5, embedding=[0.1], threshold=0.85, scope='global'
    )

    client.client.rpc.assert_called_once()
    rpc_name, rpc_args = client.client.rpc.call_args[0]
    assert rpc_name == 'match_topics_global'
    assert 'query_category' not in rpc_args
    assert results[0]['category_id'] == 99


# ---------------------------------------------------------------------------
# archivist.check_novelty: cross-category duplicate caught under scope='global'
# ---------------------------------------------------------------------------

def _make_archivist():
    db = MagicMock()
    db.get_active_lenses.return_value = []
    embedder = MagicMock()
    embedder.embed_single.return_value = [0.1, 0.2, 0.3]
    return ArchivistAgent(db_client=db, embedder=embedder), db


def test_check_novelty_category_scope_misses_cross_category_duplicate():
    """Pins the OLD behavior for scope='category' (still the default): a
    duplicate filed under a different category_id is invisible because the
    mocked DB only returns matches for the category it was actually asked
    about."""
    archivist, db = _make_archivist()

    def fake_find_similar(category_id, embedding, threshold, scope='category'):
        # Category-scoped search: the "cat t-shirt" duplicate lives in a
        # different category (99), so a search scoped to category 5 finds
        # nothing.
        if scope == 'global':
            return [{'id': 'x', 'concept_english': 'cat t-shirt', 'category_id': 99, 'similarity': 0.93}]
        return []

    db.find_similar_topics.side_effect = fake_find_similar

    is_novel, reason, _ = archivist.check_novelty(
        category_id=5, semantic_signature="cat t-shirt design", scope='category'
    )

    assert is_novel is True, "category-scoped search should miss the cross-category duplicate"


def test_check_novelty_global_scope_catches_cross_category_duplicate():
    archivist, db = _make_archivist()

    def fake_find_similar(category_id, embedding, threshold, scope='category'):
        if scope == 'global':
            return [{'id': 'x', 'concept_english': 'cat t-shirt', 'category_id': 99, 'similarity': 0.93}]
        return []

    db.find_similar_topics.side_effect = fake_find_similar

    is_novel, reason, _ = archivist.check_novelty(
        category_id=5, semantic_signature="cat t-shirt design", scope='global'
    )

    assert is_novel is False, "global search must catch the near-duplicate from a different category"
    assert '99' in reason  # diagnostics: which category it collided with
    call_kwargs = db.find_similar_topics.call_args.kwargs
    assert call_kwargs['category_id'] == 5
    assert call_kwargs['scope'] == 'global'


def test_check_novelty_global_scope_does_not_require_category_id():
    archivist, db = _make_archivist()
    db.find_similar_topics.return_value = []

    is_novel, reason, _ = archivist.check_novelty(
        category_id=None, semantic_signature="cat t-shirt design", scope='global'
    )

    assert is_novel is True
    db.find_similar_topics.assert_called_once()


def test_check_novelty_category_scope_still_requires_category_id():
    archivist, db = _make_archivist()

    with pytest.raises(ValueError):
        archivist.check_novelty(category_id=None, semantic_signature="x", scope='category')
