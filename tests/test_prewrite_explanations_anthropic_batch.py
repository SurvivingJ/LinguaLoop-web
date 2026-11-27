"""services/explanations_anthropic.py and scripts/prewrite_explanations_anthropic_batch.py:
exercise explanations written ahead of time with the Message Batches API (ADR-064).

Fully offline: a fake database (exercises, word_assets), the conftest's
``InMemoryBackend`` for content and explanation files, and a fake Anthropic client
whose batch results arrive in reverse order and answer from each request's own
prompt (so an answer matched to the wrong item is visible in the file). The owner's
spend ledger (``CLAUDE_API_LEDGER``) is redirected to the test's tmp directory.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
import os
import re
from collections import Counter
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from scripts import prewrite_explanations_anthropic_batch as ab
from services import exercise_explanations as xe
from services import explanation_files as xf
from services import explanations_anthropic as xa
from services.exercise_content import store

ZH, EN, JA = 1, 2, 3
SONNET = 'claude-sonnet-5-5'
CUSTOM_ID = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')     # the Batches API's custom_id rule
MODEL_CORRECTION = 'モデルの訂正。'


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------

def spot(n=0):
    return {'sentences': [
        {'is_correct': True, 'text': f'正しい文{n}です。'},
        {'is_correct': False, 'text': f'間違い文{n}が。', 'error_description': '助詞の誤り'},
        {'is_correct': True, 'text': f'もう一つ{n}です。'},
    ]}


def pick_with_notes():
    return {'target_word': '芋', 'sentences': [
        {'is_correct': True, 'text': '芋が育つ。', 'explanation': 'Potatoes grow underground.'},
        {'is_correct': False, 'text': '芋が泳ぐ。', 'explanation': 'Potatoes do not swim.'},
    ]}


def pick_without_notes():
    return {'target_word': '芋', 'sentences': [
        {'is_correct': True, 'text': '芋を掘る。'},
        {'is_correct': False, 'text': '芋が飛ぶ。', 'explanation': 'Potatoes do not fly.'},
    ]}


def not_explainable():
    return {'sentences': [{'is_correct': True, 'text': '一文だけ。'}]}


# ---------------------------------------------------------------------------
# Fake database
# ---------------------------------------------------------------------------

class _Query:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.cols, self.filters, self.window, self.order_col = [], [], None, 'id'

    def select(self, cols):
        self.cols = [c.strip() for c in cols.split(',')]
        return self

    def eq(self, col, val):
        self.filters.append((col, lambda v, val=val: v == val))
        return self

    def in_(self, col, vals):
        vals = list(vals)
        if self.name == 'word_assets' and self.db.max_in is not None \
                and len(vals) > self.db.max_in:
            self.db.too_long = True            # the gateway's URL limit (in_ travels in the URL)
        self.filters.append((col, lambda v, vals=set(vals): v in vals))
        return self

    def order(self, col):
        self.order_col = col
        return self

    def range(self, start, end):
        self.window = (start, end)
        return self

    def _project(self, row):
        out = {}
        for col in self.cols:
            alias, _, expr = col.rpartition(':')
            base, _, key = expr.partition('->')
            value = row.get(base)
            if key:
                value = (value or {}).get(key)
            out[alias or base] = value
        return out

    def execute(self):
        self.db.reads.append(self.name)
        if self.name == 'word_assets':
            if self.db.too_long:
                self.db.too_long = False
                raise RuntimeError('414 Request-URI Too Large')
            if self.db.fail_word_assets:
                self.db.fail_word_assets -= 1
                raise RuntimeError('word_assets read failed')
        rows = [r for r in self.db.tables.get(self.name, [])
                if all(pred(r.get(col)) for col, pred in self.filters)]
        rows.sort(key=lambda r: r[self.order_col])
        if self.window:
            rows = rows[self.window[0]:self.window[1] + 1]
        return SimpleNamespace(data=[self._project(r) for r in rows])


class FakeDB:
    def __init__(self):
        self.tables = {'exercises': [], 'word_assets': []}
        self.reads = []
        self.max_in = None           # longest in_() list word_assets accepts (None: any)
        self.fail_word_assets = 0    # word_assets reads that raise
        self.too_long = False

    def table(self, name):
        return _Query(self, name)


class World:
    """Exercises, their content files, transform assets and explanation files."""

    def __init__(self):
        self.db = FakeDB()
        self.backend = store.backend()
        self._files: dict[tuple[int, int], dict] = {}
        self._n = 0
        self.content: dict[str, dict] = {}

    def add(self, sense_id, etype, content, version=0):
        self._n += 1
        eid = f'00000000-0000-4000-8000-{self._n:012d}'
        self.db.tables['exercises'].append({
            'id': eid, 'word_sense_id': sense_id, 'exercise_type': etype, 'language_id': JA,
            'content_version': version, 'is_active': True})
        self._files.setdefault((sense_id, version), {})[eid] = content
        self.backend.seed(store.content_path(JA, sense_id, version),
                          store.encode_sense_file(sense_id, JA, version,
                                                  self._files[(sense_id, version)]))
        self.content[eid] = content
        return eid

    def correction(self, sense_id, incorrect, corrected):
        rows = self.db.tables['word_assets']
        rows.append({'id': len(rows) + 1, 'sense_id': sense_id,
                     'asset_type': 'prompt3_transforms_A',
                     'content': {'level_7': {'incorrect_sentence': incorrect,
                                             'corrected_sentence': corrected}}})

    def path(self, sense_id):
        return xf.file_path(JA, sense_id, EN, xe.PROMPT_VERSION)

    def file(self, sense_id):
        data = self.backend.objects().get(self.path(sense_id))
        return None if data is None else xf.decode(data)


def entry_payload(text='x'):
    return {'sentences': [{'text': text, 'is_correct': True, 'meaning': '', 'explanation': 'e',
                           'correction': None}], 'prompt_version': xe.PROMPT_VERSION}


# ---------------------------------------------------------------------------
# Fake Anthropic client
# ---------------------------------------------------------------------------

_LINE = re.compile(r'^(\d+)\. \[(\w+)\] (.+)$', re.M)


def answer_for(user_prompt: str) -> str:
    """A valid answer for the prompt's own sentences: each meaning names the sentence it
    was written for, so the file shows whether the answer reached the right item."""
    return json.dumps({'sentences': [
        {'index': int(i), 'meaning': f'M:{text.strip()}',
         'explanation': f'Explanation {i} in English.',
         'correction': MODEL_CORRECTION if tag == 'ERROR' else None}
        for i, tag, text in _LINE.findall(user_prompt)]}, ensure_ascii=False)


def message(text, stop_reason='end_turn', input_tokens=1000, output_tokens=400, model=SONNET,
            request_id=None):
    msg = SimpleNamespace(
        content=[SimpleNamespace(type='thinking', thinking=''),
                 SimpleNamespace(type='text', text=text)],
        stop_reason=stop_reason, model=model,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens))
    if request_id is not None:
        msg._request_id = request_id
    return msg


def _request():
    return httpx2.Request('POST', 'https://api.anthropic.com/v1/messages/batches')


class FakeBatches:
    """``client.messages.batches``. ``outcome``: custom_id -> 'errored' | 'expired' |
    'canceled' | 'unusable' | 'short' | 'max_tokens' | 'fenced' (default: a valid answer).
    ``fail_create_at``: the index of the create call that raises (a lost connection)."""

    def __init__(self, outcome=None, polls_before_end=1, fail_create_at=None, once=False,
                 lose_response_at=None, refuse_create_at=None):
        self.outcome = dict(outcome or {})
        self.refuse_create_at = refuse_create_at  # answered 400 (e.g. no credit): nothing made
        self.once = once                       # an outcome applies to the first answer only
        self.polls_before_end = polls_before_end
        self.fail_create_at = fail_create_at
        self.lose_response_at = lose_response_at  # made on the server, response lost
        self.created: list[tuple[str, list[dict]]] = []
        self.created_at: dict[str, datetime] = {}
        self.create_calls = 0
        self.retrieves: Counter = Counter()

    def create(self, requests):
        requests = list(requests)
        index, self.create_calls = self.create_calls, self.create_calls + 1
        if self.fail_create_at is not None and index == self.fail_create_at:
            raise anthropic.APIConnectionError(request=_request())
        if self.refuse_create_at is not None and index == self.refuse_create_at:
            raise anthropic.BadRequestError(
                'Your credit balance is too low',
                response=httpx2.Response(400, request=_request()), body=None)
        ids = [r['custom_id'] for r in requests]
        assert all(CUSTOM_ID.match(i) for i in ids), ids
        assert len(set(ids)) == len(ids), 'custom_id must be unique within a batch'
        assert all(r['params'] is not None for r in requests)
        batch_id = f'msgbatch_{len(self.created) + 1:02d}'
        self.created.append((batch_id, requests))
        self.created_at[batch_id] = datetime.now(timezone.utc)
        if self.lose_response_at is not None and index == self.lose_response_at:
            raise anthropic.APIConnectionError(request=_request())
        return SimpleNamespace(id=batch_id, processing_status='in_progress')

    def list(self, limit=20):
        out = []
        for batch_id, reqs in reversed(self.created):
            counts = SimpleNamespace(processing=len(reqs), succeeded=0, errored=0, canceled=0,
                                     expired=0)
            out.append(SimpleNamespace(id=batch_id, created_at=self.created_at[batch_id],
                                       request_counts=counts))
        return out[:limit]

    def _requests(self, batch_id):
        return dict(self.created)[batch_id]

    def retrieve(self, batch_id):
        self.retrieves[batch_id] += 1
        n = len(self._requests(batch_id))
        ended = self.retrieves[batch_id] > self.polls_before_end
        counts = SimpleNamespace(processing=0 if ended else n, succeeded=n if ended else 0,
                                 errored=0, canceled=0, expired=0)
        return SimpleNamespace(id=batch_id, processing_status='ended' if ended else 'in_progress',
                               request_counts=counts)

    def results(self, batch_id):
        for req in reversed(self._requests(batch_id)):     # results arrive in any order
            yield self._result(req)

    def _result(self, req):
        cid = req['custom_id']
        kind = self.outcome.pop(cid, 'ok') if self.once else self.outcome.get(cid, 'ok')
        if kind in ('errored', 'expired', 'canceled'):
            return SimpleNamespace(custom_id=cid, result=SimpleNamespace(type=kind))
        text, stop = answer_for(req['params']['messages'][0]['content']), 'end_turn'
        if kind == 'unusable':
            text = 'I am not able to answer in JSON.'
        elif kind == 'short':
            text = json.dumps({'sentences': json.loads(text)['sentences'][:1]})
        elif kind == 'fenced':
            text = f'```json\n{text}\n```'
        elif kind == 'max_tokens':
            stop = 'max_tokens'
        return SimpleNamespace(custom_id=cid,
                               result=SimpleNamespace(type='succeeded', message=message(text, stop)))

    def all_custom_ids(self):
        return [r['custom_id'] for _, reqs in self.created for r in reqs]


class FakeClient:
    def __init__(self, batches=None, create=None):
        self.messages = SimpleNamespace(batches=batches or FakeBatches(), create=create)

    def with_options(self, **_kwargs):
        return self


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    """The owner's ledger goes to tmp; no polling delay; no cached explanations."""
    monkeypatch.setattr(xa, 'LEDGER', str(tmp_path / 'ledger.jsonl'))
    monkeypatch.setattr(ab, 'POLL_S', 0)
    xe.reset_state()
    yield
    xe.reset_state()


def ledger_lines(tmp_path):
    path = tmp_path / 'ledger.jsonl'
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


@pytest.fixture
def world():
    """Sense 10: two spot items, the first with a reviewed correction. Sense 20: a pick
    item whose English notes explain every sentence (skipped) and one without. Sense 30:
    already has its file. Sense 40: only an unexplainable item. Sense 50: one spot item
    at content_version 1. Sense 60: three spot items."""
    w = World()
    w.s10a = w.add(10, xe.SPOT, spot(1))
    w.s10b = w.add(10, xe.SPOT, spot(2))
    w.correction(10, '間違い文1が。', '間違い文1を直した。')
    w.s20a = w.add(20, xe.PICK, pick_with_notes())
    w.s20b = w.add(20, xe.PICK, pick_without_notes())
    w.s30a = w.add(30, xe.SPOT, spot(3))
    assert xf.write_file(JA, 30, EN, xe.PROMPT_VERSION,
                         {w.s30a: {'content_version': 0, 'model': 'earlier',
                                   'payload': entry_payload()}}) == 'written'
    w.s40a = w.add(40, xe.SPOT, not_explainable())
    w.s50a = w.add(50, xe.SPOT, spot(5), version=1)
    w.s60a = w.add(60, xe.SPOT, spot(6))
    w.s60b = w.add(60, xe.SPOT, spot(7))
    w.s60c = w.add(60, xe.SPOT, spot(8))
    w.backend.clear_calls()
    return w


def run(world, monkeypatch, run_dir, *args, client=None):
    """``main`` with the fake database; ``client`` (None: making one is an error)."""
    monkeypatch.setattr(ab.pw, 'admin_db', lambda: world.db)

    def make_client():
        if client is None:
            raise AssertionError('no Anthropic client expected')
        return client
    monkeypatch.setattr(ab.xa, 'make_client', make_client)
    return ab.main(['--language', 'ja', '--nl', 'en', '--run-dir', str(run_dir), *args])


def say_nothing(_msg):
    pass


def prepare_args(**kw):
    ns = ab.build_parser().parse_args([])
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


# ---------------------------------------------------------------------------
# services/explanations_anthropic.py
# ---------------------------------------------------------------------------

def test_request_params_use_the_live_prompt_with_the_reviewed_correction():
    content = spot(1)
    params = xa.request_params(content, JA, EN, xe.SPOT, '間違い文1を直した。', SONNET, 'medium')
    system, user = xe.build_prompt(content['sentences'], JA, EN, xe.SPOT, None, '間違い文1を直した。')
    assert params == {'model': SONNET, 'max_tokens': xa.MAX_TOKENS, 'system': system,
                      'messages': [{'role': 'user', 'content': user}],
                      'output_config': {'effort': 'medium'}}
    assert 'Corrected sentence: 間違い文1を直した。' in user
    # nothing a current model rejects (sampling parameters, a thinking budget)
    assert not {'temperature', 'top_p', 'top_k', 'thinking'} & set(params)


def test_request_params_for_a_pick_item_name_the_target_word():
    params = xa.request_params(pick_without_notes(), JA, EN, xe.PICK, None, SONNET, 'low')
    user = params['messages'][0]['content']
    assert '「芋」' in user and 'Corrected sentence' not in user
    assert params['output_config'] == {'effort': 'low'}


@pytest.mark.parametrize('content', [not_explainable(), {}, None,
                                     {'sentences': [{'is_correct': True, 'text': 'a'},
                                                    {'is_correct': True, 'text': 'b'}]}])
def test_request_params_is_none_for_an_unexplainable_item(content):
    assert xa.request_params(content, JA, EN, xe.SPOT, None, SONNET, 'medium') is None


def _user(content, etype=xe.SPOT, corrected=None):
    return xe.build_prompt(content['sentences'], JA, EN, etype, content.get('target_word'),
                           corrected)[1]


def test_payload_from_message_validates_with_the_live_parser():
    content = spot(1)
    msg = message(answer_for(_user(content)))
    payload = xa.payload_from_message(msg, content, EN, xe.SPOT, '間違い文1を直した。')
    assert payload['prompt_version'] == xe.PROMPT_VERSION
    entries = payload['sentences']
    assert [e['text'] for e in entries] == [s['text'] for s in content['sentences']]
    assert [e['is_correct'] for e in entries] == [True, False, True]
    assert entries[1]['correction'] == '間違い文1を直した。'     # the reviewed one wins
    assert entries[0]['correction'] is None and entries[2]['correction'] is None
    assert entries[0]['meaning'] == 'M:正しい文1です。'
    # without a reviewed correction the model's own is kept
    own = xa.payload_from_message(msg, content, EN, xe.SPOT, None)
    assert own['sentences'][1]['correction'] == MODEL_CORRECTION


def test_payload_from_message_accepts_code_fenced_json():
    content = pick_without_notes()
    text = '```json\n' + answer_for(_user(content, xe.PICK)) + '\n```'
    payload = xa.payload_from_message(message(text), content, EN, xe.PICK, None)
    assert payload is not None and len(payload['sentences']) == 2
    assert all(e['correction'] is None for e in payload['sentences'])


@pytest.mark.parametrize('stop_reason', ['max_tokens', 'refusal', 'pause_turn', None])
def test_payload_from_message_rejects_an_unfinished_answer(stop_reason):
    content = spot(1)
    msg = message(answer_for(_user(content)), stop_reason=stop_reason)
    assert xa.payload_from_message(msg, content, EN, xe.SPOT, None) is None


def test_payload_from_message_accepts_stop_sequence():
    content = spot(1)
    msg = message(answer_for(_user(content)), stop_reason='stop_sequence')
    assert xa.payload_from_message(msg, content, EN, xe.SPOT, None) is not None


def test_payload_from_message_rejects_unusable_answers():
    content = spot(1)
    good = json.loads(answer_for(_user(content)))
    short = {'sentences': good['sentences'][:2]}
    not_english = {'sentences': [dict(e, explanation='日本語の説明です。')
                                 for e in good['sentences']]}
    empty = {'sentences': [dict(e, explanation='') for e in good['sentences']]}
    for text in ('not json at all', json.dumps(short), json.dumps(not_english, ensure_ascii=False),
                 json.dumps(empty), '[]'):
        assert xa.payload_from_message(message(text), content, EN, xe.SPOT, None) is None, text
    only_thinking = SimpleNamespace(content=[SimpleNamespace(type='thinking', thinking='')],
                                    stop_reason='end_turn')
    assert xa.payload_from_message(only_thinking, content, EN, xe.SPOT, None) is None


def test_cost_usd_standard_and_batch_half():
    assert xa.cost_usd(SONNET, 1_000_000, 1_000_000) == pytest.approx(12.0)
    assert xa.cost_usd(SONNET, 1_000_000, 1_000_000, batch=True) == pytest.approx(6.0)
    assert xa.cost_usd('claude-opus-5-5', 1000, 400) == pytest.approx(0.004 + 0.008)
    assert xa.cost_usd('claude-haiku-5-5', 1000, 400, batch=True) == pytest.approx(0.0003 / 2)
    with pytest.raises(KeyError):
        xa.cost_usd('claude-unknown', 1, 1)
    # the batch script's estimate per item is the measured standard price, halved
    assert set(ab.MEASURED_COST_PER_ITEM) == set(xa.PRICES)


class FakeMessages:
    def __init__(self, reply=None, exc=None):
        self.reply, self.exc, self.calls = reply, exc, []

    def create(self, **params):
        self.calls.append(params)
        if self.exc is not None:
            raise self.exc
        return self.reply(params)


def test_generate_success_bills_standard_price_and_writes_the_ledger(tmp_path):
    content = spot(1)
    fake = FakeMessages(reply=lambda p: message(answer_for(p['messages'][0]['content']),
                                                request_id='req_123'))
    client = SimpleNamespace(messages=fake)
    res = xa.generate(client, content, JA, EN, xe.SPOT, '間違い文1を直した。', SONNET,
                      exercise_id='eid-1')
    assert res.error is None and res.payload['prompt_version'] == xe.PROMPT_VERSION
    assert res.payload['sentences'][1]['correction'] == '間違い文1を直した。'
    assert (res.input_tokens, res.output_tokens) == (1000, 400)
    assert res.cost_usd == pytest.approx(xa.cost_usd(SONNET, 1000, 400))      # not halved
    assert res.stop_reason == 'end_turn' and res.request_id == 'req_123'
    assert fake.calls[0]['output_config'] == {'effort': 'medium'}
    [line] = ledger_lines(tmp_path)
    assert line['request_id'] == 'req_123' and line['artifact_id'] == 'eid-1'
    assert line['input_tokens'] == 1000 and line['cost_usd'] == pytest.approx(0.006)


def test_generate_unusable_answer_is_reported_with_its_cost(tmp_path):
    fake = FakeMessages(reply=lambda p: message('nope'))
    res = xa.generate(SimpleNamespace(messages=fake), spot(1), JA, EN, xe.SPOT, None, SONNET)
    assert res.payload is None and res.error == 'unusable answer'
    assert res.cost_usd == pytest.approx(0.006)
    assert len(ledger_lines(tmp_path)) == 1


def test_generate_api_status_error_returns_a_result_with_the_error(tmp_path):
    response = httpx2.Response(529, request=_request(), headers={'request-id': 'req_err'})
    exc = anthropic.APIStatusError('Overloaded', response=response, body=None)
    fake = FakeMessages(exc=exc)
    res = xa.generate(SimpleNamespace(messages=fake), spot(1), JA, EN, xe.SPOT, None, SONNET,
                      exercise_id='eid-2')
    assert res.payload is None and res.cost_usd == 0.0
    assert res.error.startswith('529: ') and 'Overloaded' in res.error
    [line] = ledger_lines(tmp_path)
    assert line['artifact_id'] == 'eid-2' and 'Overloaded' in line['error']


def test_generate_connection_error_returns_a_result_with_the_error():
    fake = FakeMessages(exc=anthropic.APIConnectionError(request=_request()))
    res = xa.generate(SimpleNamespace(messages=fake), spot(1), JA, EN, xe.SPOT, None, SONNET)
    assert res.payload is None and res.error.startswith('connection: ')


def test_generate_makes_no_call_for_an_unexplainable_item(tmp_path):
    fake = FakeMessages(exc=AssertionError('no call expected'))
    res = xa.generate(SimpleNamespace(messages=fake), not_explainable(), JA, EN, xe.SPOT, None,
                      SONNET)
    assert res.error == 'not explainable' and fake.calls == []
    assert ledger_lines(tmp_path) == []


# ---------------------------------------------------------------------------
# scripts/prewrite_explanations_anthropic_batch.py: prepare
# ---------------------------------------------------------------------------

def test_existing_senses_counts_only_this_learner_language_and_prompt_version(world):
    world.backend.seed(xf.file_path(JA, 71, EN, xe.PROMPT_VERSION - 1), b'{}')
    world.backend.seed(xf.file_path(JA, 72, ZH, xe.PROMPT_VERSION), b'{}')
    world.backend.seed(xf.file_path(JA, 73, EN, xe.PROMPT_VERSION), b'{}')
    world.backend.seed(xf.file_path(ZH, 74, EN, xe.PROMPT_VERSION), b'{}')
    assert ab.existing_senses(JA, EN) == {30, 73}


def test_prepare_skips_existing_files_and_stored_notes_and_records_corrections(world, tmp_path):
    info = ab.prepare(world.db, prepare_args(), JA, EN, str(tmp_path), say_nothing)
    recs = ab.read_manifest(str(tmp_path))
    by_id = {r['custom_id']: r for r in recs}
    # sense 30 (has a file), the stored-notes pick item and the unexplainable item are out
    assert list(by_id) == [world.s10a, world.s10b, world.s20b, world.s50a,
                           world.s60a, world.s60b, world.s60c]
    assert by_id[world.s10a]['corrected'] == '間違い文1を直した。'
    assert by_id[world.s10b]['corrected'] is None             # no reviewed correction for it
    assert by_id[world.s20b]['corrected'] is None             # pick items never get one
    assert by_id[world.s50a]['content_version'] == 1
    assert by_id[world.s20b]['target_word'] == '芋'
    assert by_id[world.s10a]['sentences'] == spot(1)['sentences']
    assert {r['sense_id'] for r in recs} == {10, 20, 50, 60}
    spot_items = sum(1 for r in recs if r['exercise_type'] == xe.SPOT)
    assert info['items'] == {'to_write': 7, 'skipped_stored_notes': 1,
                             'skipped_not_explainable': 1,
                             'spot_with_correction': sum(1 for r in recs if r['corrected']),
                             'spot_without_correction': spot_items - sum(
                                 1 for r in recs if r['corrected'])}
    assert info['senses_held_back'] == []
    assert (info['senses_total'], info['senses_with_file'], info['senses_prepared']) == (6, 1, 5)
    assert info['estimate_usd'] == round(7 * ab.MEASURED_COST_PER_ITEM[SONNET] / 2, 2)
    assert info['model'] == SONNET and info['prompt_version'] == xe.PROMPT_VERSION
    saved = json.loads((tmp_path / 'prepare.json').read_text(encoding='utf-8'))
    assert saved == info
    assert world.backend.calls_for('put') == []                # read-only


def test_prepare_limit_and_sense_ids(world, tmp_path):
    ab.prepare(world.db, prepare_args(limit_senses=1), JA, EN, str(tmp_path), say_nothing)
    assert [r['custom_id'] for r in ab.read_manifest(str(tmp_path))] == [world.s10a, world.s10b]
    ab.prepare(world.db, prepare_args(sense_ids='60,30'), JA, EN, str(tmp_path), say_nothing)
    assert [r['sense_id'] for r in ab.read_manifest(str(tmp_path))] == [60, 60, 60]


@pytest.fixture
def many_senses():
    """120 senses, each with one spot item and its reviewed correction."""
    w = World()
    w.ids = {}
    for sense in range(1000, 1120):
        w.ids[sense] = w.add(sense, xe.SPOT, spot(sense))
        w.correction(sense, f'間違い文{sense}が。', f'直した文{sense}。')
    return w


def test_prepare_reads_corrections_in_url_sized_chunks(many_senses, tmp_path):
    many_senses.db.max_in = ab.pw.CHUNK_SENSES       # what the codebase's in_() readers use
    ab.prepare(many_senses.db, prepare_args(), JA, EN, str(tmp_path), say_nothing)
    recs = ab.read_manifest(str(tmp_path))
    assert len(recs) == 120
    assert all(r['corrected'] == f"直した文{r['sense_id']}。" for r in recs)


def test_prepare_does_not_silently_drop_corrections_when_the_read_fails(world, tmp_path):
    world.db.fail_word_assets = 1
    try:
        ab.prepare(world.db, prepare_args(), JA, EN, str(tmp_path), say_nothing)
    except Exception:
        return                                       # refusing to prepare is acceptable
    by_id = {r['custom_id']: r for r in ab.read_manifest(str(tmp_path))}
    assert by_id[world.s10a]['corrected'] == '間違い文1を直した。'


# ---------------------------------------------------------------------------
# main: dry run, apply, resume, spend cap
# ---------------------------------------------------------------------------

def test_dry_run_prepares_and_submits_nothing(world, monkeypatch, tmp_path, capsys):
    run_dir = tmp_path / 'run'
    assert run(world, monkeypatch, run_dir) == 0           # no client may be made
    assert world.backend.calls_for('put') == []
    assert (run_dir / 'manifest.jsonl').exists() and (run_dir / 'prepare.json').exists()
    assert not (run_dir / 'batches.json').exists() and not (run_dir / 'report.json').exists()
    assert 'dry run: nothing submitted' in capsys.readouterr().out
    assert ledger_lines(tmp_path) == []


def test_apply_after_a_dry_run_uses_the_prepared_manifest(world, monkeypatch, tmp_path):
    run_dir = tmp_path / 'run'
    run(world, monkeypatch, run_dir)
    late = world.add(80, xe.SPOT, spot(80))                # added after the dry run
    batches = FakeBatches()
    assert run(world, monkeypatch, run_dir, '--apply', client=FakeClient(batches)) == 0
    submitted = batches.all_custom_ids()
    assert late not in submitted and len(submitted) == 7


def test_apply_submits_collects_out_of_order_and_writes_one_file_per_sense(
        world, monkeypatch, tmp_path):
    monkeypatch.setattr(ab, 'BATCH_SIZE', 2)               # sense 60 spans two batches
    batches = FakeBatches(outcome={world.s10b: 'errored', world.s20b: 'unusable',
                                   world.s50a: 'fenced', world.s60b: 'expired',
                                   world.s60c: 'max_tokens'})
    run_dir = tmp_path / 'run'
    assert run(world, monkeypatch, run_dir, '--apply', client=FakeClient(batches)) == 0

    # submitted: every manifest item once in BATCH_SIZE chunks, then one retry batch
    # of the four that failed (they fail again here: outcomes are not one-off)
    assert [len(reqs) for _, reqs in batches.created] == [2, 2, 2, 1, 4]
    assert batches.all_custom_ids()[:7] == [world.s10a, world.s10b, world.s20b, world.s50a,
                                            world.s60a, world.s60b, world.s60c]
    assert sorted(r['custom_id'] for r in batches.created[-1][1]) == sorted(
        [world.s10b, world.s20b, world.s60b, world.s60c])
    params = dict((r['custom_id'], r['params']) for _, reqs in batches.created for r in reqs)
    assert params[world.s10a] == xa.request_params(
        spot(1), JA, EN, xe.SPOT, '間違い文1を直した。', SONNET, 'medium')
    assert all(batches.retrieves[b] >= 2 for b, _ in batches.created)   # polled until ended

    # a sense's file is written only when every one of its items is usable: only 50
    assert world.backend.calls_for('put') == [world.path(50)]
    for sense in (10, 20, 60):
        assert world.file(sense) is None
    f50 = world.file(50)
    assert list(f50['exercises']) == [world.s50a]                      # fenced JSON accepted
    assert (f50['language_id'], f50['sense_id'], f50['nl_language_id'],
            f50['prompt_version']) == (JA, 50, EN, xe.PROMPT_VERSION)
    entry = f50['exercises'][world.s50a]
    sents = world.content[world.s50a]['sentences']
    assert entry['model'] == SONNET and entry['content_version'] == 1
    assert [e['text'] for e in entry['payload']['sentences']] == [s['text'] for s in sents]
    assert [e['meaning'] for e in entry['payload']['sentences']] == [f"M:{s['text']}" for s in sents]

    # the report lists the held-back senses and why
    report = json.loads((run_dir / 'report.json').read_text(encoding='utf-8'))
    held = {h['sense_id']: h['failed'] for h in report['held_back']}
    assert held == {10: {world.s10b: 'errored'}, 20: {world.s20b: 'unusable (end_turn)'},
                    60: {world.s60b: 'expired', world.s60c: 'unusable (max_tokens)'}}
    assert report['usable'] == 3 and report['items'] == 7
    assert report['files'] == {'written': 1, 'held_back': 3}
    succeeded = 5 + 2               # billed: succeeded answers, usable or not, incl. the retry's
    assert report['tokens'] == {'input': succeeded * 1000, 'output': succeeded * 400}
    assert report['cost_usd'] == pytest.approx(
        round(succeeded * xa.cost_usd(SONNET, 1000, 400, batch=True), 4))
    assert report['batch_ids'] == [b for b, _ in batches.created]
    [line] = ledger_lines(tmp_path)
    assert line['via'] == 'message-batches' and line['batch_ids'] == report['batch_ids']
    assert line['cost_usd'] == report['cost_usd']


def test_items_that_fail_once_are_retried_and_their_senses_written(world, monkeypatch, tmp_path):
    batches = FakeBatches(outcome={world.s10b: 'errored', world.s60c: 'unusable'}, once=True)
    run_dir = tmp_path / 'run'
    assert run(world, monkeypatch, run_dir, '--apply', client=FakeClient(batches)) == 0
    assert sorted(r['custom_id'] for r in batches.created[-1][1]) == sorted([world.s10b, world.s60c])
    assert sorted(world.backend.calls_for('put')) == sorted(
        [world.path(10), world.path(20), world.path(50), world.path(60)])
    assert sorted(world.file(10)['exercises']) == sorted([world.s10a, world.s10b])
    report = json.loads((run_dir / 'report.json').read_text(encoding='utf-8'))
    assert report['held_back'] == [] and report['usable'] == 7


def test_a_lost_create_response_is_adopted_not_billed_twice(world, monkeypatch, tmp_path):
    monkeypatch.setattr(ab, 'BATCH_SIZE', 3)
    batches = FakeBatches(lose_response_at=1)      # the 2nd batch is made; its response is lost
    run_dir = tmp_path / 'run'
    with pytest.raises(anthropic.APIConnectionError):
        run(world, monkeypatch, run_dir, '--apply', client=FakeClient(batches))
    assert [len(r) for _, r in batches.created] == [3, 3]
    assert run(world, monkeypatch, run_dir, '--apply', client=FakeClient(batches)) == 0
    ids = batches.all_custom_ids()
    assert len(ids) == len(set(ids)) == 7          # the lost batch was adopted, not repeated
    state = json.loads((run_dir / 'batches.json').read_text(encoding='utf-8'))
    assert [b['id'] for b in state['batches']] == ['msgbatch_01', 'msgbatch_02', 'msgbatch_03']
    assert state['pending'] is None


def test_a_sense_whose_content_changed_since_prepare_is_held_back(world, monkeypatch, tmp_path):
    run_dir = tmp_path / 'run'
    assert run(world, monkeypatch, run_dir) == 0                       # prepare only
    for row in world.db.tables['exercises']:
        if row['id'] == world.s10a:
            row['content_version'] = 5                                 # re-rendered since
    assert run(world, monkeypatch, run_dir, '--apply', client=FakeClient(FakeBatches())) == 0
    assert world.file(10) is None
    report = json.loads((run_dir / 'report.json').read_text(encoding='utf-8'))
    assert [h for h in report['held_back'] if h['sense_id'] == 10][0]['stale'] == [world.s10a]


def test_written_files_are_served_to_items_at_their_content_version(world, monkeypatch, tmp_path):
    run(world, monkeypatch, tmp_path / 'run', '--apply', client=FakeClient(FakeBatches()))
    xe.reset_state()                                       # fresh caches; same backend
    items = [{'exercise_id': world.s10a, 'exercise_type': xe.SPOT, 'sense_id': 10,
              'content_version': 0, 'content': spot(1)},
             {'exercise_id': world.s50a, 'exercise_type': xe.SPOT, 'sense_id': 50,
              'content_version': 1, 'content': spot(5)},
             {'exercise_id': world.s60b, 'exercise_type': xe.SPOT, 'sense_id': 60,
              'content_version': 3, 'content': spot(7)}]   # a newer content version
    started = xe.prepare_items(None, items, language_id=JA, nl_language_id=EN, warm_limit=0)
    assert started == 0
    assert items[0]['content']['option_explanations'][1]['correction'] == '間違い文1を直した。'
    assert items[0]['content']['explanation_language'] == 'en'
    assert len(items[1]['content']['option_explanations']) == 3
    assert 'option_explanations' not in items[2]['content']   # written for version 0


def test_resume_after_collect_does_not_resubmit_or_rewrite(world, monkeypatch, tmp_path):
    batches = FakeBatches()
    run_dir = tmp_path / 'run'
    run(world, monkeypatch, run_dir, '--apply', client=FakeClient(batches))
    files_before = {p: d for p, d in world.backend.objects().items()
                    if p.startswith('explanations/')}
    created = list(batches.created)
    assert run(world, monkeypatch, run_dir, '--apply', client=FakeClient(batches)) == 0
    assert batches.created == created and batches.create_calls == len(created)
    files_after = {p: d for p, d in world.backend.objects().items()
                   if p.startswith('explanations/')}
    assert files_after == files_before
    report = json.loads((run_dir / 'report.json').read_text(encoding='utf-8'))
    assert report['files'] == {'exists': 4}


def test_resume_after_a_failed_submit_sends_only_the_rest(world, monkeypatch, tmp_path):
    monkeypatch.setattr(ab, 'BATCH_SIZE', 3)
    batches = FakeBatches(fail_create_at=1)                # the second create is lost
    run_dir = tmp_path / 'run'
    with pytest.raises(anthropic.APIConnectionError):
        run(world, monkeypatch, run_dir, '--apply', client=FakeClient(batches))
    state = json.loads((run_dir / 'batches.json').read_text(encoding='utf-8'))
    assert [(b['start'], b['count']) for b in state['batches']] == [(0, 3)]
    assert world.backend.calls_for('put') == []            # nothing written before collect

    batches.fail_create_at = None
    assert run(world, monkeypatch, run_dir, '--apply', client=FakeClient(batches)) == 0
    ids = batches.all_custom_ids()
    assert len(ids) == len(set(ids)) == 7                  # nothing submitted twice
    assert [len(reqs) for _, reqs in batches.created] == [3, 3, 1]
    assert {p for p in world.backend.calls_for('put')} == {
        world.path(10), world.path(20), world.path(50), world.path(60)}


def test_estimate_above_max_usd_refuses_to_submit(world, monkeypatch, tmp_path, capsys):
    run_dir = tmp_path / 'run'
    assert run(world, monkeypatch, run_dir, '--apply', '--max-usd', '0.001') == 2
    assert not (run_dir / 'batches.json').exists()
    assert world.backend.calls_for('put') == []
    assert 'exceeds --max-usd' in capsys.readouterr().out
    assert ledger_lines(tmp_path) == []


def test_nothing_to_write_makes_no_client(world, monkeypatch, tmp_path, capsys):
    assert run(world, monkeypatch, tmp_path / 'run', '--apply', '--sense-ids', '30,40') == 0
    assert 'nothing to write' in capsys.readouterr().out


def test_ledger_records_a_batch_once_across_resumes(world, monkeypatch, tmp_path):
    batches = FakeBatches()
    run_dir = tmp_path / 'run'
    run(world, monkeypatch, run_dir, '--apply', client=FakeClient(batches))
    run(world, monkeypatch, run_dir, '--apply', client=FakeClient(batches))
    entries = [e for e in ledger_lines(tmp_path) if e.get('via') == 'message-batches']
    assert len(entries) == 1


def test_run_dir_files_are_plain_json(world, monkeypatch, tmp_path):
    run_dir = tmp_path / 'run'
    run(world, monkeypatch, run_dir, '--apply', client=FakeClient(FakeBatches()))
    assert sorted(os.listdir(run_dir)) == ['batches.json', 'manifest.jsonl', 'prepare.json',
                                           'report.json']


def test_a_self_corrected_answer_uses_the_last_valid_json():
    """Pilot 2026-11-27: the model wrote its JSON, then 'Wait, I need to correct a slip ...
    Here is the corrected JSON:' and a second JSON. The corrected one is the answer."""
    prompt = xa.request_params(spot(1), JA, EN, xe.SPOT, None, SONNET, 'medium')
    first = json.loads(answer_for(prompt['messages'][0]['content']))
    second = json.loads(json.dumps(first))
    second['sentences'][0]['explanation'] = 'The corrected explanation in English.'
    text = (json.dumps(first, ensure_ascii=False) + '\n\nWait, I need to correct a slip in '
            'sentence 1. Here is the corrected JSON:\n\n' + json.dumps(second, ensure_ascii=False))
    payload = xa.payload_from_message(message(text), spot(1), EN, xe.SPOT, None)
    assert payload['sentences'][0]['explanation'] == 'The corrected explanation in English.'
    # a broken second object falls back to the earlier valid one
    payload = xa.payload_from_message(message(json.dumps(first) + '\n{"sentences": [oops'),
                                      spot(1), EN, xe.SPOT, None)
    assert payload['sentences'][0]['explanation'] == first['sentences'][0]['explanation']


# ---------------------------------------------------------------------------
# --family options (2026-11-27): particle / word form / synonym-antonym
# ---------------------------------------------------------------------------

def test_the_options_family_selects_its_types_kind_and_prompt_version():
    assert ab.FAMILIES['options'] == (sorted(xe.OPTION_TYPES), 'o', xe.OPTION_PROMPT_VERSION)
    assert ab.FAMILIES['sentences'] == (sorted(xe.SENTENCE_TYPES), 'p', xe.PROMPT_VERSION)
    assert ab.build_parser().parse_args([]).family is None      # prepare: sentences
    assert ab.build_parser().parse_args(['--family', 'options']).family == 'options'


def test_existing_senses_lists_only_files_of_the_kind_asked_for():   # conftest: empty in-memory store
    xf.write_file(JA, 70, EN, xe.PROMPT_VERSION, {'e1': {'content_version': 0, 'model': None,
                  'payload': {'sentences': [{'text': 'x'}], 'prompt_version': xe.PROMPT_VERSION}}})
    xf.write_file(JA, 71, EN, xe.OPTION_PROMPT_VERSION, {'e2': {'content_version': 0, 'model': None,
                  'payload': {'sentences': [{'text': 'を'}],
                              'prompt_version': xe.OPTION_PROMPT_VERSION}}}, kind='o')
    assert ab.existing_senses(JA, EN) == {70}
    assert ab.existing_senses(JA, EN, 'o', xe.OPTION_PROMPT_VERSION) == {71}


def test_an_option_record_carries_its_content_for_the_prompt():
    content = {'options': ['が', 'を'], 'correct_answer': 'が',
               'sentence_with_blank': '時計___鳴った。', 'original_sentence': '時計が鳴った。'}
    rec = {'custom_id': 'e', 'exercise_type': xe.PARTICLE, 'content': content,
           'sentences': xe.sentences_of(content, xe.PARTICLE), 'target_word': None}
    assert ab.item_content(rec) is content
    reqs = ab.build_requests([rec], {'language_id': JA, 'nl_language_id': EN,
                                     'model': SONNET, 'effort': 'medium'})
    assert 'Sentence with the blank: 時計___鳴った。' in reqs[0]['params']['messages'][0]['content']


def test_a_refused_retry_batch_holds_back_only_the_failed_senses(world, monkeypatch, tmp_path):
    # 2026-11-27: the account ran out of credit between the main batches and the retry.
    batches = FakeBatches(outcome={world.s60c: 'unusable'}, refuse_create_at=1)
    run_dir = tmp_path / 'run'
    assert run(world, monkeypatch, run_dir, '--apply', client=FakeClient(batches)) == 0
    assert len(batches.created) == 1                               # the retry was not made
    assert sorted(world.backend.calls_for('put')) == sorted(
        [world.path(10), world.path(20), world.path(50)])
    assert world.file(60) is None
    report = json.loads((run_dir / 'report.json').read_text(encoding='utf-8'))
    assert [h['sense_id'] for h in report['held_back']] == [60]
    assert 'credit balance is too low' in report['retry_refused']
    state = json.loads((run_dir / 'batches.json').read_text(encoding='utf-8'))
    assert state['pending'] is None and state['retry'] == []
    # resuming does not ask again and writes nothing twice
    assert run(world, monkeypatch, run_dir, '--apply', client=FakeClient(batches)) == 0
    assert batches.create_calls == 2
