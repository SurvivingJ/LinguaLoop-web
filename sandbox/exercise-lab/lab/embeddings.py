"""
Deterministic, network-free embeddings for the exercise-lab sandbox.

WHY THIS EXISTS
----------------
Distractor selection in production (`semantic_distractors`/`nearest_senses`
RPCs, see docs/recon-data-surface.md §1 `dim_word_senses`) ranks candidate
senses by cosine similarity over OpenAI `text-embedding-3-small` vectors,
embedding the string `"{lemma}: {definition}"` specifically so a word's own
senses cluster together (recon note, same section). This sandbox has a hard
rule: never call an LLM/embedding API. Every vector produced here is a
LOCAL, DETERMINISTIC PROXY computed from the text alone, with zero learned
weights and zero semantic understanding.

# FIDELITY GAP (read this before trusting any distractor-quality result):
# A hashed character n-gram TF-IDF vector is an ORTHOGRAPHIC signal, not a
# semantic one:
#   - It OVERSTATES similarity between words that merely share
#     substrings/spelling. zh 打电话 ("make a phone call") and 打篮球
#     ("play basketball") will look closer than they semantically are,
#     purely because they share the character 打.
#   - It UNDERSTATES similarity between true synonyms spelled differently.
#     en "happy" and "glad" share almost no character n-grams and will look
#     nearly unrelated, despite being close synonyms.
# Any conclusion drawn from this backend describes ORTHOGRAPHIC confusability,
# not semantic confusability. A later agent MUST swap in real
# `text-embedding-3-small` vectors (via the same EmbeddingBackend interface)
# before trusting any distractor-quality number produced against real
# production data. See README "Fidelity Gaps" for the full collected list.

Checked offline availability of a local sentence-transformer model before
writing this (see check_local_sentence_transformer_available() below): NOT
installed in this repo's venv as of 2026-09-17 (`pip list` has no
`sentence-transformers` or `torch`) - so there is no better offline option
to fall back to here, only the network-free TF-IDF proxy.

Pluggable interface: EmbeddingBackend. A later agent swaps in a backend that
calls a real embedding API (OUTSIDE this sandbox's hard rules - that work
does not belong in exercise-lab) without touching any caller code, as long
as it exposes `dim`, `name`, `fit()`, `embed()`, `embed_batch()`.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Protocol, Sequence, runtime_checkable

import numpy as np


@runtime_checkable
class EmbeddingBackend(Protocol):
    dim: int
    name: str

    def fit(self, corpus: Sequence[str]) -> None: ...
    def embed(self, text: str) -> np.ndarray: ...
    def embed_batch(self, texts: Sequence[str]) -> np.ndarray: ...


def _char_ngrams(text: str, sizes: tuple[int, ...] = (2, 3)) -> list[str]:
    text = (text or "").strip().lower()
    grams: list[str] = []
    for n in sizes:
        if len(text) == 0:
            continue
        if len(text) < n:
            grams.append(text)
            continue
        grams.extend(text[i : i + n] for i in range(len(text) - n + 1))
    return grams


def _hash_bucket(gram: str, dim: int) -> int:
    # blake2b, not Python's builtin hash(): the latter is salted per-process
    # (PYTHONHASHSEED) and would make embeddings non-reproducible across runs.
    h = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
    return struct.unpack(">Q", h)[0] % dim


class HashedCharNgramTfidf:
    """
    Dependency-free (numpy only) TF-IDF proxy over hashed character n-grams.
    Feature hashing avoids persisting a vocabulary table (which would need
    its own migration-like bookkeeping in a "sandbox"), at the cost of hash
    collisions - a second, smaller fidelity gap on top of the orthographic-
    vs-semantic one documented at the top of this file.
    """

    name = "hashed_char_ngram_tfidf_v1"

    def __init__(self, dim: int = 512, ngram_sizes: tuple[int, ...] = (2, 3)):
        self.dim = dim
        self.ngram_sizes = ngram_sizes
        self._df = np.zeros(dim, dtype=np.float64)
        self._n_docs = 0
        self._idf = np.ones(dim, dtype=np.float64)

    def fit(self, corpus: Sequence[str]) -> None:
        self._df[:] = 0.0
        self._n_docs = 0
        for text in corpus:
            if not text:
                continue
            self._n_docs += 1
            buckets = {_hash_bucket(g, self.dim) for g in _char_ngrams(text, self.ngram_sizes)}
            for b in buckets:
                self._df[b] += 1
        # standard smoothed idf
        self._idf = np.log((1.0 + self._n_docs) / (1.0 + self._df)) + 1.0

    def _raw_tf(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float64)
        for g in _char_ngrams(text, self.ngram_sizes):
            vec[_hash_bucket(g, self.dim)] += 1.0
        return vec

    def embed(self, text: str) -> np.ndarray:
        vec = self._raw_tf(text) * self._idf
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.astype(np.float32)

    def embed_batch(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.stack([self.embed(t) for t in texts])


def pack_embedding(vec: np.ndarray) -> bytes:
    """SQLite has no vector type; pack float32s as a BLOB. This is the
    sandbox stand-in for pgvector's `vector(1536)` column, minus the type
    and minus any index (see schema.sql header, deviation #1)."""
    return np.asarray(vec, dtype=np.float32).tobytes()


def unpack_embedding(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32).copy()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def check_local_sentence_transformer_available() -> bool:
    """
    Detects whether a local, already-downloaded sentence-transformer model
    could be used OFFLINE instead of the TF-IDF proxy. Returns False in this
    repo's venv (verified by `pip list` on 2026-09-17: no
    `sentence-transformers` or `torch` package present) - documented rather
    than silently skipped, per the task's "check; do not download" rule.
    Re-run this after any venv change; do not hardcode the answer.
    """
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        return False
    return True
