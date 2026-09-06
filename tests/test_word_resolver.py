"""Unit tests for services/vocabulary/word_resolver.py.

`resolve_or_create_sense` is the request-safe "resolve existing
dim_word_senses entry or generate a new one" path for a single raw word with
no surrounding transcript (word-list-import plan, Step 2 — see
wiki/tasklist/word-list-import.plan.md). Unlike the interactive
sense-linking skill, this must be safely callable from inside a live Flask
request, so these tests pin its three call shapes:

(a) word already has a vocab row + an existing standard sense -> returns
    that sense id, with NO LLM call (SenseGenerator.generate_sense's
    prefer_existing short-circuit — real SenseGenerator/real llm_call hook
    used here, not a stub, specifically so "no LLM call" is a genuine
    assertion rather than a tautology of a stubbed generator).
(b) word has a vocab row but no sense yet -> exactly one LLM call
    generates the sense.
(c) word is entirely new -> a dim_vocabulary row is created first, then
    (b)'s generation path runs.

`get_or_create_vocab_id` — the dim_vocabulary get-or-create logic extracted
from TestGenerationOrchestrator._get_or_create_vocab_id so both callers
share one implementation — is exercised directly too, including the
look-before-insert and 23505-race paths. tests/test_vocab_shortfall_recording.py
covers the orchestrator-side caller of this same extracted function.

No real network or DB calls: a minimal in-memory fake stands in for the
Supabase query builder, and `sense_generator.llm_call` is monkeypatched.
"""

import threading

import pytest
from postgrest.exceptions import APIError

import services.vocabulary.sense_generator as sg
import services.vocabulary.word_resolver as wr
from services.vocabulary.processors.base import LemmaToken

# ---------------------------------------------------------------------------
# Fakes — minimal in-memory stand-in for the Supabase query-builder surface
# ---------------------------------------------------------------------------


class _Resp:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """One chained Supabase query-builder call, backed by an in-memory list
    of row dicts shared with the owning FakeDB table."""

    def __init__(self, rows, next_id):
        self._rows = rows
        self._next_id = next_id  # single-item list used as a mutable box
        self._filters = []
        self._limit = None
        self._single = False
        self._op = None
        self._payload = None

    # -- filter/shape builders (all return self) ----------------------
    def select(self, *_a, **_kw):
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def in_(self, col, vals):
        self._filters.append((col, set(vals)))
        return self

    def order(self, *_a, **_kw):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def single(self):
        self._single = True
        return self

    def or_(self, *_a, **_kw):
        return self

    def update(self, payload):
        self._op = ('update', payload)
        return self

    def insert(self, payload):
        self._op = ('insert', payload)
        return self

    def upsert(self, payload, on_conflict=None):
        self._op = ('upsert', payload)
        return self

    # -- terminal -------------------------------------------------------
    def _match(self, row):
        for col, val in self._filters:
            if isinstance(val, set):
                if row.get(col) not in val:
                    return False
            elif row.get(col) != val:
                return False
        return True

    def execute(self):
        if self._op:
            kind, payload = self._op
            if kind in ('insert', 'upsert'):
                items = payload if isinstance(payload, list) else [payload]
                written = []
                for item in items:
                    row = dict(item)
                    row['id'] = self._next_id[0]
                    self._next_id[0] += 1
                    self._rows.append(row)
                    written.append(row)
                return _Resp(written)
            if kind == 'update':
                matched = [r for r in self._rows if self._match(r)]
                for r in matched:
                    r.update(payload)
                return _Resp(matched)

        matched = [r for r in self._rows if self._match(r)]
        if self._limit is not None:
            matched = matched[: self._limit]
        if self._single:
            return _Resp(matched[0] if matched else None)
        return _Resp(matched)


class FakeDB:
    """Minimal in-memory stand-in for the Supabase client surface used by
    get_or_create_vocab_id and SenseGenerator's read/insert/upsert calls."""

    def __init__(self):
        self._tables: dict = {}
        self._next_ids: dict = {}

    def seed(self, table, rows):
        self._tables[table] = [dict(r) for r in rows]
        self._next_ids[table] = [max([r.get('id', 0) for r in rows], default=0) + 1]

    def table(self, name):
        rows = self._tables.setdefault(name, [])
        next_id = self._next_ids.setdefault(name, [1])
        return _FakeQuery(rows, next_id)


class _LangConfig:
    def __init__(self, id_, code):
        self.id = id_
        self.language_code = code


class FakeDBClient:
    """Duck-typed TestDatabaseClient: `.client`, `.get_language_config_by_code`,
    `.get_prompt_template` — the only surface resolve_or_create_sense and
    SenseGenerator need from it."""

    def __init__(self, db, language_id=1, language_code='en'):
        self.client = db
        self._language_id = language_id
        self._language_code = language_code

    def get_language_config_by_code(self, code):
        if code != self._language_code:
            return None
        return _LangConfig(self._language_id, code)

    def get_prompt_template(self, _name, _language_id, required=False):
        return "Define {lemma} for the sentence: {sentence} ({simple_register})"


class _FakeProcessor:
    """Stands in for a real language processor — tokenizes any input word
    into one fixed LemmaToken so tests don't need spaCy/jieba/fugashi."""

    def __init__(self, lemma, pos='NOUN'):
        self._lemma = lemma
        self._pos = pos

    def extract_lemma_tokens(self, word):
        return [LemmaToken(
            index=0, surface=word, lemma=self._lemma, pos=self._pos,
            is_stop=False, is_content=True, reading='',
        )]


class _FakePipeline:
    """Stands in for VocabularyExtractionPipeline: resolve_or_create_sense
    only calls get_processor(), so that's all this needs to provide."""

    def __init__(self, *_a, **_kw):
        pass

    def get_processor(self, _language_code):
        return _FakeProcessor('run')


VALID_PAYLOAD = {
    '1': 'A simple definition.',
    '2': 'A standard definition.',
    '3': 'An example sentence.',
    '4': 0,          # -> POS 'other', skips the dim_vocabulary POS-update branch
    '5': 0.9,
    '6': False,
}


@pytest.fixture(autouse=True)
def _fake_pipeline(monkeypatch):
    """Every test in this file resolves a single English word — tokenize it
    with a fixed fake processor instead of loading spaCy."""
    monkeypatch.setattr(wr, 'VocabularyExtractionPipeline', _FakePipeline)


@pytest.fixture(autouse=True)
def _no_real_embedding_calls(monkeypatch):
    """_write_two_levels best-effort embeds freshly written senses via a real
    OpenAI-backed EmbeddingService. Neutralized here: it's an unrelated
    enrichment step (embedding vectors), not part of this function's
    contract, and must never attempt a real network call from a unit test."""
    monkeypatch.setattr(sg.SenseGenerator, '_embed_new_senses', lambda self, *a, **kw: None)


def _no_llm_allowed(_prompt, **_kw):
    raise AssertionError("llm_call must not be invoked for this case")


# ---------------------------------------------------------------------------
# get_or_create_vocab_id — the extracted dim_vocabulary get-or-create logic
# ---------------------------------------------------------------------------

def test_get_or_create_returns_existing_row_without_inserting():
    db = FakeDB()
    db.seed('dim_vocabulary', [{'id': 42, 'lemma': 'run', 'language_id': 1}])

    vid = wr.get_or_create_vocab_id(db, {'lemma': 'run', 'pos': 'VERB'}, 1, 'en')

    assert vid == 42
    assert len(db._tables['dim_vocabulary']) == 1  # nothing inserted


def test_get_or_create_inserts_a_brand_new_lemma():
    db = FakeDB()

    vid = wr.get_or_create_vocab_id(db, {'lemma': 'sprint', 'pos': 'VERB'}, 1, 'en')

    rows = db._tables['dim_vocabulary']
    assert len(rows) == 1
    assert rows[0]['lemma'] == 'sprint'
    assert rows[0]['id'] == vid


def test_get_or_create_recovers_from_a_concurrent_insert_race():
    """A second caller wins the insert (23505) between our select and our
    insert — the shared function must re-read rather than raise."""
    db = FakeDB()

    real_table = db.table

    def racy_table(name):
        query = real_table(name)
        if name == 'dim_vocabulary':
            original_execute = query.execute

            def racy_execute():
                if query._op and query._op[0] == 'insert':
                    # Simulate another worker having already inserted it
                    # between our select and this insert.
                    db._tables['dim_vocabulary'].append(
                        {'id': 7, 'lemma': 'sprint', 'language_id': 1}
                    )
                    raise APIError({'code': '23505', 'message': 'duplicate key'})
                return original_execute()

            query.execute = racy_execute
        return query

    db.table = racy_table

    vid = wr.get_or_create_vocab_id(db, {'lemma': 'sprint', 'pos': 'VERB'}, 1, 'en')
    assert vid == 7


def test_get_or_create_reuses_a_caller_supplied_cache():
    db = FakeDB()
    cache: dict = {}
    lock = threading.Lock()

    v1 = wr.get_or_create_vocab_id(
        db, {'lemma': 'sprint'}, 1, 'en', cache=cache, cache_lock=lock,
    )
    v2 = wr.get_or_create_vocab_id(
        db, {'lemma': 'sprint'}, 1, 'en', cache=cache, cache_lock=lock,
    )

    assert v1 == v2
    assert len(db._tables['dim_vocabulary']) == 1  # second call hit the cache


# ---------------------------------------------------------------------------
# resolve_or_create_sense — (a) existing vocab row + existing sense
# ---------------------------------------------------------------------------

def test_existing_sense_is_reused_with_no_llm_call(monkeypatch):
    db = FakeDB()
    db.seed('dim_vocabulary', [{'id': 1, 'lemma': 'run', 'language_id': 1}])
    db.seed('dim_word_senses', [{
        'id': 99, 'vocab_id': 1, 'sense_rank': 1,
        'definition_language_id': 1, 'definition_level': 'standard',
        'definition': 'to move fast on foot', 'example_sentence': '',
        'source': 'llm',
    }])
    db_client = FakeDBClient(db)
    monkeypatch.setattr(sg, 'llm_call', _no_llm_allowed)

    sense_id = wr.resolve_or_create_sense('run', 'en', db_client, openai_client=None)

    assert sense_id == 99
    assert isinstance(sense_id, int)
    # No new vocab or sense rows were written.
    assert len(db._tables['dim_vocabulary']) == 1
    assert len(db._tables['dim_word_senses']) == 1


# ---------------------------------------------------------------------------
# resolve_or_create_sense — (b) existing vocab row, no sense yet
# ---------------------------------------------------------------------------

def test_missing_sense_triggers_exactly_one_generation_call(monkeypatch):
    db = FakeDB()
    db.seed('dim_vocabulary', [{'id': 1, 'lemma': 'run', 'language_id': 1}])
    db.seed('dim_word_senses', [])  # vocab exists; no sense at all yet
    db_client = FakeDBClient(db)

    calls = []

    def fake_llm_call(_prompt, **kw):
        calls.append(kw)
        return dict(VALID_PAYLOAD)

    monkeypatch.setattr(sg, 'llm_call', fake_llm_call)

    sense_id = wr.resolve_or_create_sense('run', 'en', db_client, openai_client=None)

    assert len(calls) == 1
    assert isinstance(sense_id, int)
    written = db._tables['dim_word_senses']
    assert len(written) == 2  # simple + standard rows
    assert any(r['definition_level'] == 'standard' and r['id'] == sense_id for r in written)
    # Still exactly one dim_vocabulary row — no duplicate created.
    assert len(db._tables['dim_vocabulary']) == 1


# ---------------------------------------------------------------------------
# resolve_or_create_sense — (c) entirely new word
# ---------------------------------------------------------------------------

def test_brand_new_word_creates_vocab_row_then_sense(monkeypatch):
    db = FakeDB()  # both dim_vocabulary and dim_word_senses start empty
    db_client = FakeDBClient(db)

    calls = []

    def fake_llm_call(_prompt, **kw):
        calls.append(kw)
        return dict(VALID_PAYLOAD)

    monkeypatch.setattr(sg, 'llm_call', fake_llm_call)

    sense_id = wr.resolve_or_create_sense('run', 'en', db_client, openai_client=None)

    assert len(calls) == 1
    assert isinstance(sense_id, int)
    vocab_rows = db._tables['dim_vocabulary']
    assert len(vocab_rows) == 1
    assert vocab_rows[0]['lemma'] == 'run'
    sense_rows = db._tables['dim_word_senses']
    assert len(sense_rows) == 2
    assert all(r['vocab_id'] == vocab_rows[0]['id'] for r in sense_rows)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_empty_word_is_rejected():
    db_client = FakeDBClient(FakeDB())
    with pytest.raises(ValueError):
        wr.resolve_or_create_sense('   ', 'en', db_client, openai_client=None)


def test_unconfigured_language_is_rejected():
    db_client = FakeDBClient(FakeDB(), language_code='en')
    with pytest.raises(ValueError):
        wr.resolve_or_create_sense('run', 'zh', db_client, openai_client=None)
