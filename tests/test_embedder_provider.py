"""EmbeddingService provider switch (EMBEDDINGS_PROVIDER)."""

import pytest

from services.topic_generation.agents import embedder as emb


def test_openrouter_provider_uses_openrouter_endpoint_and_key(monkeypatch):
    seen = {}
    monkeypatch.setenv('EMBEDDINGS_PROVIDER', 'openrouter')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'or-key')
    monkeypatch.setattr(emb, 'get_client', lambda **kw: seen.update(kw) or object())
    e = emb.EmbeddingService()
    assert seen == {'base_url': 'https://openrouter.ai/api/v1', 'api_key': 'or-key'}
    assert e.model == 'openai/text-embedding-3-small'


def test_openrouter_provider_needs_its_key(monkeypatch):
    monkeypatch.setenv('EMBEDDINGS_PROVIDER', 'openrouter')
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    with pytest.raises(ValueError, match='OPENROUTER_API_KEY'):
        emb.EmbeddingService()


def test_default_provider_is_openai(monkeypatch):
    seen = {}
    monkeypatch.delenv('EMBEDDINGS_PROVIDER', raising=False)
    monkeypatch.setattr(emb, 'get_client', lambda **kw: seen.update(kw) or object())
    e = emb.EmbeddingService(api_key='sk-test')
    assert seen['base_url'] == 'https://api.openai.com/v1' and e.model == 'text-embedding-3-small'
