"""Topic-generation agents call the shared LLM entry point and embed in batches."""

import json
from unittest.mock import MagicMock

import pytest

from services import llm_service
from services.topic_generation.agents.archivist import ArchivistAgent
from services.topic_generation.agents.base import BaseAgent


@pytest.fixture
def calls(monkeypatch):
    seen = []

    def fake_call_llm(prompt, **kwargs):
        seen.append((prompt, kwargs))
        return {'candidates': []} if kwargs['response_format'] == 'json_object' else 'YES'

    monkeypatch.setattr(llm_service, 'call_llm', fake_call_llm)
    return seen


def test_text_call_goes_through_call_llm_with_the_agent_model(calls, monkeypatch):
    monkeypatch.setattr(llm_service, 'LLM_DEFAULT_PROVIDER', 'openrouter')
    agent = BaseAgent(model='vendor/model-x', api_key='k', name='Gatekeeper')

    assert agent._call_llm('hello', temperature=0.1) == 'YES'

    prompt, kwargs = calls[0]
    assert prompt == 'hello'
    assert kwargs['model'] == 'vendor/model-x'
    assert kwargs['provider'] == 'openrouter'
    assert kwargs['response_format'] == 'text'
    assert kwargs['temperature'] == 0.1
    assert kwargs['pipeline'] == 'topic_generation'
    assert kwargs['task_name'] == 'gatekeeper'
    assert agent.api_call_count == 1


def test_json_mode_returns_a_json_string_and_model_override_wins(calls):
    agent = BaseAgent(model='vendor/model-x', api_key='k', name='Explorer')
    raw = agent._call_llm('p', json_mode=True, model='vendor/other')
    assert json.loads(raw) == {'candidates': []}
    assert calls[0][1]['model'] == 'vendor/other'
    assert calls[0][1]['response_format'] == 'json_object'
    assert calls[0][1]['allow_internal_repair'] is False


def test_cli_default_provider_is_followed(calls, monkeypatch):
    monkeypatch.setattr(llm_service, 'LLM_DEFAULT_PROVIDER', 'claude_cli')
    BaseAgent(model='m', api_key='k')._call_llm('p')
    assert calls[0][1]['provider'] == 'claude_cli'


def _archivist(similar=None):
    db = MagicMock()
    db.get_active_lenses.return_value = []
    db.find_similar_topics.return_value = similar or []
    embedder = MagicMock()
    embedder.embed_batch.side_effect = lambda texts: [[float(len(t))] for t in texts]
    embedder.embed_single.side_effect = lambda text: [float(len(text))]
    return ArchivistAgent(db, embedder), db, embedder


def test_signatures_are_embedded_in_one_call_and_reused_by_check_novelty():
    archivist, db, embedder = _archivist()
    vectors = archivist.embed_signatures(['a', 'bbb'])
    assert vectors == [[1.0], [3.0]]
    assert embedder.embed_batch.call_count == 1

    is_novel, reason, embedding = archivist.check_novelty(
        1, 'bbb', 0.9, scope='global', embedding=vectors[1])
    assert (is_novel, reason, embedding) == (True, None, [3.0])
    embedder.embed_single.assert_not_called()
    assert db.find_similar_topics.call_args.kwargs['embedding'] == [3.0]


def test_precomputed_and_inline_embeddings_reach_the_same_verdict():
    similar = [{'similarity': 0.95, 'concept_english': 'existing', 'category_id': 7}]
    archivist, _, _ = _archivist(similar)
    inline = archivist.check_novelty(1, 'bbb', 0.9, scope='global')
    batched = archivist.check_novelty(
        1, 'bbb', 0.9, scope='global', embedding=archivist.embed_signatures(['bbb'])[0])
    assert inline == batched
    assert inline[0] is False


def test_embed_signatures_rejects_a_short_batch():
    archivist, _, embedder = _archivist()
    embedder.embed_batch.side_effect = lambda texts: [[1.0]]
    with pytest.raises(ValueError):
        archivist.embed_signatures(['a', 'b'])
    assert archivist.embed_signatures([]) == []
