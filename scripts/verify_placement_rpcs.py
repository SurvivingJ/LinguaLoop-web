#!/usr/bin/env python3
"""Verify the placement SQL functions after the owner applies them (TASK-1077).

Owner-run, service role. It READS ONLY, apart from the placement sessions it creates
for the given TEST ACCOUNT, which it deletes at the end (their responses go by ON DELETE
CASCADE). Nothing else is written. Per (L, D) pair it runs one scripted placement of
--draws meaning items (default 200, no cap) and checks, item by item, independently of
the SQL that built them:

  * a payload carries no key, role, sense id or reading field; options are distinct;
  * meaning items: a rank-1 frame row of (L, D), placement-ready, never answered by the
    account in another session within 180 days, never served twice in a session, and
    no option equals the word's reading;
  * reading items: every option has the key's display syllable (zh) / mora (ja) count;
    ja options match the lemma's visible kana (rule 3b); zh options have exactly the
    roles K, KT, F, FT, KT and FT are tone variants of K and F
    (calibration_zh_tone_variants), F is not a tone variant of K;
  * grading, the stored answer, and the tallies equal a hand count after every answer
    (zh pairs [n', pc, pkt, pf], ja [n', pc, prw]);
  * probes <= 4 per session, <= 2 per kind, <= 1 per word;
  * a second answer, an out-of-range position (22023) and a foreign session (P0002) are
    rejected; close leaves no unanswered row and is idempotent;
  * the client round-trip time of every answer call (p50 / p95, for TASK-1080's budget).

Usage (live, owner):
    python scripts/verify_placement_rpcs.py --user <test account uuid>
    python scripts/verify_placement_rpcs.py --user <uuid> --pairs 1:2 --draws 50 --ready-counts
Local harness (the same checks over psql; never a Supabase host):
    python scripts/verify_placement_rpcs.py --user <any uuid> --dsn "host=/tmp port=55435 user=postgres"

calibration_placement_ready_counts for zh takes ~9 ms per frame lemma on the harness
(two calibration_zh_tone_variants calls), ~30 s for the live zh frame: above PostgREST's
8 s statement_timeout. --ready-counts tries it and reports a timeout; run
tests/sql/check_calibration_placement.sql in the SQL editor for the gate numbers.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

PAYLOAD_KEYS = {'response_id', 'vocab_id', 'lemma', 'band', 'kind', 'probe_kind', 'options',
                'idk_allowed', 'resent'}
SMALL_KANA = re.compile('[ゃゅょぁぃぅぇぉっャュョァィゥェォッ]')
KANA_ONLY = re.compile('^[ぁ-ゟァ-ヿー・]+$')
TONELESS = str.maketrans('āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü', 'aaaaeeeeiiiioooouuuuvvvvv')
ROW_COLS = ('id, session_id, user_id, anchor_sense_id, anchor_vocab_id, zipf_band, item_kind, probe_kind, '
            'instrument, pair_response_id, option_sense_ids, key_position, option_roles, option_texts, '
            'chosen_position, chosen_sense_id, is_correct, answered_at')


class RpcError(Exception):
    def __init__(self, code: str | None, message: str):
        super().__init__(f'{code}: {message}')
        self.code = code


# --------------------------------------------------------------------------------------
# Backends
# --------------------------------------------------------------------------------------
class SupabaseBackend:
    """Service-role PostgREST client (the owner's live run)."""

    def __init__(self):
        try:
            from _common import admin_db, bootstrap
        except ImportError:  # run as scripts.<name>
            from scripts._common import admin_db, bootstrap
        bootstrap(log_level=None)
        self.db = admin_db()

    def rpc(self, name: str, params: dict):
        from postgrest.exceptions import APIError
        try:
            return self.db.rpc(name, params).execute().data
        except APIError as exc:
            raise RpcError(exc.code, exc.message or str(exc)) from None

    def rows(self, table: str, cols: str, **eq):
        q = self.db.table(table).select(cols)
        for k, v in eq.items():
            q = q.eq(k, v)
        return q.limit(5000).execute().data or []

    def answered_elsewhere(self, user: str, vocab: int, session: str, since: str) -> int:
        data = (self.db.table('calibration_responses').select('id').eq('user_id', user)
                .eq('anchor_vocab_id', vocab).neq('session_id', session).gt('answered_at', since)
                .limit(5).execute().data) or []
        return len(data)

    def create_session(self, user: str, lang: int, defn: int) -> str:
        return self.db.table('calibration_sessions').insert({
            'user_id': user, 'word_language_id': lang, 'definition_language_id': defn,
            'mode': 'placement'}).execute().data[0]['id']

    def delete_sessions(self, user: str, ids: list[str]) -> None:
        for sid in ids:
            self.db.table('calibration_sessions').delete().eq('id', sid).eq('user_id', user) \
                .eq('mode', 'placement').execute()


class PsqlBackend:
    """The same calls over psql, for the local harness only."""

    def __init__(self, dsn: str):
        if re.search(r'supabase\.(co|com)|pooler', dsn, re.I):
            sys.exit('refusing: --dsn is for the local harness, never Supabase')
        self.dsn = dsn

    @staticmethod
    def lit(v) -> str:
        if v is None:
            return 'NULL'
        if isinstance(v, bool):
            return 'true' if v else 'false'
        if isinstance(v, (int, float)):
            return repr(v)
        if isinstance(v, (dict, list)):
            return "'" + json.dumps(v).replace("'", "''") + "'::jsonb"
        return "'" + str(v).replace("'", "''") + "'"

    def _query(self, sql: str):
        p = subprocess.run(['psql', self.dsn, '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-v', 'VERBOSITY=verbose',
                            '-c', sql], capture_output=True, text=True)
        if p.returncode:
            m = re.search(r'ERROR:\s+([0-9A-Z]{5}):\s*(.*)', p.stderr)
            raise RpcError(m.group(1) if m else None, m.group(2) if m else p.stderr.strip())
        out = p.stdout.strip()
        return json.loads(out) if out else None

    _types: dict[str, dict[str, str]] = {}

    def _arg_types(self, name: str) -> dict[str, str]:
        """IN argument name -> type, as PostgREST resolves them from the signature."""
        if name not in self._types:
            ident = self._query(f"SELECT to_jsonb(pg_get_function_identity_arguments(p.oid)) FROM pg_proc p "
                                f"JOIN pg_namespace n ON n.oid = p.pronamespace AND n.nspname = 'public' "
                                f"WHERE p.proname = {self.lit(name)}")
            self._types[name] = {}
            for part in (ident or '').split(', '):
                if part and not part.startswith('OUT '):
                    arg, typ = part.split(' ', 1)
                    self._types[name][arg] = typ
        return self._types[name]

    def rpc(self, name: str, params: dict):
        types = self._arg_types(name)
        args = ', '.join(f'{k} => {self.lit(v)}::{types[k]}' for k, v in params.items())
        return self._query(f'SELECT to_jsonb(r) FROM public.{name}({args}) r')

    def rows(self, table: str, cols: str, **eq):
        where = ' AND '.join(f'{k} = {self.lit(v)}' for k, v in eq.items()) or 'true'
        return self._query(f'SELECT coalesce(jsonb_agg(to_jsonb(x)), \'[]\') FROM '
                           f'(SELECT {cols} FROM public.{table} WHERE {where}) x')

    def answered_elsewhere(self, user, vocab, session, since) -> int:
        return self._query(f'SELECT count(*) FROM public.calibration_responses WHERE user_id = {self.lit(user)} '
                           f'AND anchor_vocab_id = {int(vocab)} AND session_id <> {self.lit(session)} '
                           f'AND answered_at > {self.lit(since)}')

    def create_session(self, user, lang, defn) -> str:
        return self._query(f"WITH x AS (INSERT INTO public.calibration_sessions "
                           f"(user_id, word_language_id, definition_language_id, mode) VALUES "
                           f"({self.lit(user)}, {int(lang)}, {int(defn)}, 'placement') RETURNING id) "
                           f"SELECT to_jsonb(id) FROM x")

    def delete_sessions(self, user, ids) -> None:
        for sid in ids:
            self._query(f"DELETE FROM public.calibration_sessions WHERE id = {self.lit(sid)} "
                        f"AND user_id = {self.lit(user)} AND mode = 'placement'")


# --------------------------------------------------------------------------------------
# Independent rules
# --------------------------------------------------------------------------------------
def units(text: str, lang: int) -> int:
    text = (text or '').strip()
    if not text:
        return 0
    if lang == 1:
        return len(text.split())
    if lang == 3:
        return len(SMALL_KANA.sub('', text))
    return len(text)


def kana_pattern(lemma: str) -> str:
    return '^' + re.sub('[^ぁ-ゟー]+', '.+', lemma) + '$'


def toneless(text: str) -> str:
    return (text or '').lower().translate(TONELESS)


def exempt(lemma: str, lang: int) -> bool:
    return lang != 1 and (lang != 3 or bool(KANA_ONLY.match(lemma or '')))


class Checker:
    def __init__(self, backend, user: str, verbose: bool = False):
        self.b, self.user, self.verbose = backend, user, verbose
        self.failures: list[str] = []
        self.counts: dict[str, int] = {}
        self.rtt_ms: list[float] = []

    def fail(self, msg: str) -> None:
        self.failures.append(msg)
        print(f'  XX {msg}')

    def count(self, key: str) -> None:
        self.counts[key] = self.counts.get(key, 0) + 1

    def row(self, rid: int) -> dict:
        return self.b.rows('calibration_responses', ROW_COLS, id=rid)[0]

    # ---- item invariants --------------------------------------------------------------
    def check_item(self, lang: int, defn: int, sid: str, item: dict, started: str) -> dict:
        r = self.row(item['response_id'])
        tag = f"[{lang}:{defn} r{r['id']} {item.get('lemma')}]"
        if set(item) - PAYLOAD_KEYS:
            self.fail(f'{tag} payload keys {sorted(set(item) - PAYLOAD_KEYS)}')
        opts = item['options']
        n = 2 if r['item_kind'] == 'sound_pair' else 4
        if len(opts) != n or len(set(opts)) != n or len(r['option_sense_ids']) != n:
            self.fail(f'{tag} option set {opts}')
        if r['session_id'] != sid or r['answered_at'] is not None or not 0 <= r['key_position'] < n:
            self.fail(f'{tag} stored row {r}')
        if item['kind'] != r['item_kind'] or item['probe_kind'] != r['probe_kind'] \
                or item['vocab_id'] != r['anchor_vocab_id'] or item['band'] != r['zipf_band']:
            self.fail(f'{tag} payload/row mismatch')
        if item['idk_allowed'] != (r['probe_kind'] != 'forced_guess'):
            self.fail(f'{tag} idk_allowed')
        lemma = item['lemma']
        key = opts[r['key_position']]
        if r['item_kind'] == 'meaning':
            self.count('meaning_items' if r['probe_kind'] is None else 'forced_guess')
            sense = self.b.rows('dim_word_senses', 'vocab_id, sense_rank', id=r['anchor_sense_id'])[0]
            pool = self.b.rows('calibration_anchor_pool', 'has_embedding', word_language_id=lang,
                               definition_language_id=defn, sense_id=r['anchor_sense_id'])
            blocked = self.b.rows('calibration_anchor_blocklist', 'sense_id', sense_id=r['anchor_sense_id'])
            if sense['sense_rank'] != 1 or not pool or not pool[0]['has_embedding'] or blocked:
                self.fail(f'{tag} not a rank-1 frame row')
            if r['option_sense_ids'][r['key_position']] != r['anchor_sense_id']:
                self.fail(f'{tag} key sense')
            definition = self.b.rows('dim_word_senses', 'definition', id=r['anchor_sense_id'])[0]['definition']
            mp = self.b.rpc('calibration_placement_meaning_parts', {
                'p_anchor_sense_id': r['anchor_sense_id'], 'p_word_language_id': lang,
                'p_definition_language_id': defn, 'p_lemma': lemma, 'p_key': definition})
            mp = mp[0] if isinstance(mp, list) else mp
            if mp['status'] != 'ok':
                self.fail(f'{tag} meaning status {mp["status"]}')
            if not exempt(lemma, lang):
                ready = self.b.rpc('calibration_placement_reading_ready', {
                    'p_vocab_id': r['anchor_vocab_id'], 'p_word_language_id': lang, 'p_lemma': lemma})
                if ready is not True:
                    self.fail(f'{tag} not reading-ready')
                reading = self.b.rpc('calibration_placement_reveal_reading', {
                    'p_vocab_id': r['anchor_vocab_id'], 'p_word_language_id': lang})
                if reading and reading in opts:
                    self.fail(f'{tag} meaning item shows the reading {reading}')
            if r['probe_kind'] is None:
                since = (datetime.fromisoformat(started) - timedelta(days=180)).isoformat()
                if self.b.answered_elsewhere(self.user, r['anchor_vocab_id'], sid, since):
                    self.fail(f'{tag} answered within 180 days')
                same = self.b.rows('calibration_responses', 'id', session_id=sid,
                                   anchor_vocab_id=r['anchor_vocab_id'])
                if len(same) != 1:
                    self.fail(f'{tag} served twice in the session')
        elif r['item_kind'] == 'reading':
            self.count('reading_items' if r['probe_kind'] is None else r['probe_kind'])
            if any(units(o, lang) != units(key, lang) for o in opts):
                self.fail(f'{tag} syllable/mora counts differ {opts}')
            if lang == 3:
                bad = [o for o in opts if not re.match(kana_pattern(lemma), o)]
                if bad:
                    self.fail(f'{tag} kana-inconsistent {bad}')
            elif lang == 1:
                roles = r['option_roles'] or []
                if sorted(roles) != ['F', 'FT', 'K', 'KT'] or roles[r['key_position']] != 'K':
                    self.fail(f'{tag} roles {roles}')
                else:
                    by = {role: opts[i] for i, role in enumerate(roles)}
                    f_vocab = self.b.rows('dim_word_senses', 'vocab_id',
                                          id=r['option_sense_ids'][roles.index('F')])[0]['vocab_id']
                    kv = self.b.rpc('calibration_zh_tone_variants',
                                    {'p_pronunciation': by['K'], 'p_vocab_id': r['anchor_vocab_id']}) or []
                    fv = self.b.rpc('calibration_zh_tone_variants',
                                    {'p_pronunciation': by['F'], 'p_vocab_id': f_vocab}) or []
                    if by['KT'] not in kv or by['FT'] not in fv:
                        self.fail(f'{tag} KT/FT not tone variants of K/F: {by}')
                    if toneless(by['F']) == toneless(by['K']):
                        self.fail(f'{tag} F is a tone variant of K: {by}')
        else:
            self.count('sound_pair')
            if lang != 3:
                self.fail(f'{tag} sound_pair outside ja')
        return r

    # ---- one scripted session ------------------------------------------------------------
    def run_pair(self, lang: int, defn: int, draws: int, rng: random.Random, created: list[str]) -> None:
        print(f'--- pair {lang}:{defn}, {draws} meaning draws')
        sid = self.b.create_session(self.user, lang, defn)
        created.append(sid)
        started = datetime.now(timezone.utc).isoformat()
        hm = [[0, 0, 0] for _ in range(7)]
        hp = [[0, 0, 0, 0] for _ in range(7)]
        bands = [7, 6, 5, 4, 3, 2, 1]
        item = self.b.rpc('calibration_placement_next_item', {'p_user_id': self.user, 'p_session_id': sid,
                                                               'p_band': 7})
        words = answers = 0
        scored = 0
        exhausted = False
        while item and not item.get('exhausted'):
            r = self.check_item(lang, defn, sid, item, started)
            answers += 1
            know = 0.10 + 0.11 * r['zipf_band']
            role = None
            if r['item_kind'] == 'meaning':
                pos = r['key_position'] if rng.random() < know else (
                    None if rng.random() < 0.4 and r['probe_kind'] is None else rng.randrange(4))
            elif r['item_kind'] == 'reading' and lang == 1:
                role = rng.choice(['K', 'K', 'KT', 'F', 'FT', None])
                pos = None if role is None else r['option_roles'].index(role)
            elif r['item_kind'] == 'reading':
                pos = rng.choice([r['key_position'], r['key_position'], None, (r['key_position'] + 1) % 4])
            else:
                pos = rng.randrange(2)
            starts_word = r['item_kind'] == 'meaning' and r['probe_kind'] is None
            next_band = bands[words % 7] if words + starts_word < draws else None
            params = {'p_user_id': self.user, 'p_session_id': sid, 'p_response_id': r['id'],
                      'p_position': pos, 'p_latency_ms': 4000, 'p_next_band': next_band,
                      'p_draws': {'u_probe': rng.random(), 'u_seed': rng.random()}}
            if answers == 3:
                self.expect_error('out-of-range position', '22023', 'calibration_placement_answer',
                                  {**params, 'p_position': 7})
                self.expect_error('foreign session', 'P0002', 'calibration_placement_answer',
                                  {**params, 'p_session_id': str(uuid.uuid4())})
            t0 = time.perf_counter()
            res = self.b.rpc('calibration_placement_answer', params)
            self.rtt_ms.append((time.perf_counter() - t0) * 1000)
            if answers == 3:
                self.expect_error('second answer', '22023', 'calibration_placement_answer', params)
            # grading and stored answer
            want = pos is not None and pos == r['key_position']
            ans = res['answer']
            if ans['is_correct'] != want or ans['skipped'] != (pos is None) \
                    or ans['role'] != (r['option_roles'][pos] if (pos is not None and r['option_roles']) else None):
                self.fail(f"grading r{r['id']}: {ans} pos={pos} key={r['key_position']}")
            stored = self.row(r['id'])
            if stored['chosen_position'] != pos or stored['is_correct'] != want:
                self.fail(f"stored answer r{r['id']}")
            # hand tally (scored items only)
            if r['probe_kind'] is None:
                scored += 1
                b = r['zipf_band'] - 1
                if r['item_kind'] == 'meaning':
                    words += 1
                    hm[b][0] += 1
                    hm[b][1] += want
                    hm[b][2] += (pos is not None and not want)
                    if exempt(item['lemma'], lang):
                        hp[b][0] += 1
                        hp[b][1] += want
                        hp[b][2] += (pos is not None and not want)
                    elif not want:
                        hp[b][0] += 1
                else:
                    hp[b][0] += 1
                    if lang == 1:
                        hp[b][1] += role == 'K'
                        hp[b][2] += role == 'KT'
                        hp[b][3] += role in ('F', 'FT')
                    else:
                        hp[b][1] += want
                        hp[b][2] += (pos is not None and not want)
            t = res['tallies']
            exp_mr = None if lang not in (1, 3) else [x if lang == 1 else x[:3] for x in hp]
            if t['m'] != hm or t['mr'] != exp_mr or t['scored'] != scored:
                self.fail(f"tallies after answer {answers}: {t['m']} {t['mr']} vs {hm} {exp_mr}")
            exhausted = exhausted or bool(res.get('exhausted'))
            item = res['next_item']
        stop = 'exhausted' if exhausted or (item and item.get('exhausted')) else 'cap'
        rows = self.b.rows('calibration_responses', 'id, probe_kind, pair_response_id, answered_at', session_id=sid)
        probes = [x for x in rows if x['probe_kind']]
        per_kind: dict[str, int] = {}
        per_word: dict[int, int] = {}
        for x in probes:
            per_kind[x['probe_kind']] = per_kind.get(x['probe_kind'], 0) + 1
            if x['pair_response_id']:
                per_word[x['pair_response_id']] = per_word.get(x['pair_response_id'], 0) + 1
        if len(probes) > 4 or any(v > 2 for v in per_kind.values()) or any(v > 1 for v in per_word.values()):
            self.fail(f'probe budget {per_kind}')
        c1 = self.b.rpc('calibration_placement_close', {'p_user_id': self.user, 'p_session_id': sid,
                                                         'p_reason': stop})
        left = [x for x in self.b.rows('calibration_responses', 'id, answered_at', session_id=sid)
                if x['answered_at'] is None]
        c2 = self.b.rpc('calibration_placement_close', {'p_user_id': self.user, 'p_session_id': sid,
                                                         'p_reason': 'learner'})
        if left or not c2['already_closed'] or c2['stop_reason'] != stop or c2['m'] != c1['m']:
            self.fail(f'close: {len(left)} unanswered rows, second close {c2.get("already_closed")}')
        print(f'  words {words}, answers {answers}, scored {scored}, stop {stop}, probes {per_kind}, '
              f'failures so far {len(self.failures)}')

    def expect_error(self, what: str, code: str, name: str, params: dict) -> None:
        try:
            self.b.rpc(name, params)
        except RpcError as exc:
            if exc.code != code:
                self.fail(f'{what}: expected {code}, got {exc.code}')
            return
        self.fail(f'{what}: accepted')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--user', required=True, help='the TEST account uuid (its placement rows are created and deleted)')
    ap.add_argument('--pairs', default='1:2,1:3,3:1,3:2,2:2', help='L:D pairs (default: the five of TASK-1077)')
    ap.add_argument('--draws', type=int, default=200, help='meaning draws per pair (default 200)')
    ap.add_argument('--seed', type=int, default=1077)
    ap.add_argument('--ready-counts', action='store_true', help='also call calibration_placement_ready_counts')
    ap.add_argument('--keep', action='store_true', help='keep the created sessions (default: delete them)')
    ap.add_argument('--dsn', help='local harness only: run over psql instead of Supabase')
    args = ap.parse_args()
    uuid.UUID(args.user)

    backend = PsqlBackend(args.dsn) if args.dsn else SupabaseBackend()
    chk = Checker(backend, args.user)
    rng = random.Random(args.seed)
    created: list[str] = []
    pairs = [tuple(int(x) for x in p.split(':')) for p in args.pairs.split(',')]
    try:
        for lang, defn in pairs:
            chk.run_pair(lang, defn, args.draws, rng, created)
        if args.ready_counts:
            for lang, defn in pairs:
                t0 = time.perf_counter()
                try:
                    rc = backend.rpc('calibration_placement_ready_counts',
                                     {'p_word_language_id': lang, 'p_definition_language_id': defn})
                    print(f'--- ready_counts({lang},{defn}) in {time.perf_counter() - t0:.1f} s: '
                          f'{json.dumps(rc, ensure_ascii=False)}')
                except RpcError as exc:
                    print(f'--- ready_counts({lang},{defn}) failed after {time.perf_counter() - t0:.1f} s '
                          f'({exc}); run tests/sql/check_calibration_placement.sql in the SQL editor')
    finally:
        if created and not args.keep:
            backend.delete_sessions(args.user, created)
            print(f'--- deleted {len(created)} test session(s) of {args.user[:8]}')
    if chk.rtt_ms:
        q = statistics.quantiles(chk.rtt_ms, n=20)
        print(f'--- answer round trip: n {len(chk.rtt_ms)}, p50 {statistics.median(chk.rtt_ms):.0f} ms, '
              f'p95 {q[18]:.0f} ms, max {max(chk.rtt_ms):.0f} ms')
    print(f'--- items checked: {chk.counts}')
    if chk.failures:
        print(f'XX {len(chk.failures)} check(s) failed')
        return 1
    print('OK every check passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
