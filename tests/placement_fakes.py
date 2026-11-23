"""In-memory stand-in for the placement SQL functions (vocab-placement tech §14) and the session tables, so the
service and routes (TASK-1080) can be exercised end to end without a database. It follows the documented
contracts; the real functions are tested against PostgreSQL separately (migrations/calibration_placement_rpcs.sql).

Install with ``FakePlacementSQL(...).install(monkeypatch)``. Scripted learners read ``key_position`` /
``option_roles`` from ``fake.responses`` to answer right or wrong on purpose."""
from __future__ import annotations

import itertools
import random
import uuid
from datetime import datetime, timedelta, timezone
from statistics import median

from services import calibration_placement as cp
from services import placement_design as pd

FRAMES = {'1:2': [303, 617, 742, 691, 664, 435, 171], '3:2': [577, 425, 621, 655, 537, 283, 77],
          '2:2': [412, 517, 737, 794, 722, 425, 147], '1:1': [314, 615, 749, 690, 665, 438, 172],
          '3:3': [573, 422, 617, 653, 536, 280, 77]}


class SqlError(Exception):
    def __init__(self, code, message):
        super().__init__(f'{code} {message}')
        self.code = code


class FakePlacementSQL:
    def __init__(self, words_per_band=40, seed=0, kana_share=0.25):
        self.rng = random.Random(seed)
        # The service reads the real clock (resume window, daily cap), so the fake must too: a fixed
        # date made the resume and daily-cap tests fail from 24 h after it.
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.sessions: dict[str, dict] = {}
        self.responses: list[dict] = []
        self.ids = itertools.count(1)
        self.evidence_calls = []
        self.rpc_calls = []
        self.pool = {}
        vid = itertools.count(1000)
        for lang in (1, 2, 3):
            self.pool[lang] = []
            for b in range(1, 8):
                band = []
                for _ in range(words_per_band):
                    v = next(vid)
                    kana = lang == 3 and self.rng.random() < kana_share
                    band.append(dict(vocab_id=v, sense_id=v * 10, lemma=('かな' if kana else f'w{v}'), band=b,
                                     exempt=lang == 2 or kana))
                self.pool[lang].append(band)
        self.lemmas = {w['vocab_id']: w['lemma'] for bands in self.pool.values() for band in bands for w in band}

    # ---------------------------------------------------------------- install
    def install(self, monkeypatch):
        cp._cache.clear()
        monkeypatch.setattr(cp, '_rpc', self.rpc)
        monkeypatch.setattr(cp, '_session_row', self.session_row)
        monkeypatch.setattr(cp, '_open_session', self.open_session)
        monkeypatch.setattr(cp, '_starts_today', self.starts_today)
        monkeypatch.setattr(cp, '_insert_session', self.insert_session)
        monkeypatch.setattr(cp, '_save_result', self.save_result)
        monkeypatch.setattr(cp, '_previous_result', self.previous_result)
        monkeypatch.setattr(cp, '_session_by_id', lambda sid: self.sessions.get(str(sid)))
        monkeypatch.setattr(cp, '_latest_result_row', self.latest_result_row)
        monkeypatch.setattr(cp, '_response_rows', self.response_rows)
        monkeypatch.setattr(cp, '_lemmas', lambda ids: {i: self.lemmas.get(i) for i in ids})
        monkeypatch.setattr(cp, 'evidence_writer', lambda u, s, w: self.evidence_calls.append((u, s['id'], w)))
        monkeypatch.setattr(cp.Config, 'PLACEMENT_ENABLED_LANGS', '1,2,3', raising=False)
        return self

    # ---------------------------------------------------------------- tables
    def session_row(self, user_id, session_id):
        s = self.sessions.get(str(session_id))
        return s if s and s['user_id'] == user_id else None

    def open_session(self, user_id, lang, dlang, since):
        rows = [s for s in self.sessions.values() if s['user_id'] == user_id and s['word_language_id'] == lang
                and s['definition_language_id'] == dlang and s['ended_at'] is None and s['started_at'] >= since]
        return sorted(rows, key=lambda s: s['started_at'])[-1] if rows else None

    def starts_today(self, user_id, lang, now):
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return sum(1 for s in self.sessions.values() if s['user_id'] == user_id and s['word_language_id'] == lang
                   and s['started_at'] >= midnight)

    def insert_session(self, user_id, lang, dlang):
        sid = str(uuid.UUID(int=self.rng.getrandbits(128)))
        self.sessions[sid] = dict(id=sid, user_id=user_id, word_language_id=lang, definition_language_id=dlang,
                                  mode='placement', started_at=self.now, ended_at=None, stop_reason=None,
                                  result=None, bkt_applied_at=None, last_activity=self.now)
        return self.sessions[sid]

    def save_result(self, sid, result):
        self.sessions[str(sid)]['result'] = result

    def previous_result(self, user_id, lang, dlang, before):
        rows = [s for s in self.sessions.values() if s['user_id'] == user_id and s['word_language_id'] == lang
                and s['definition_language_id'] == dlang and s['id'] != before and s['result']]
        return sorted(rows, key=lambda s: s['ended_at'])[-1] if rows else None

    def latest_result_row(self, user_id, lang):
        rows = [s for s in self.sessions.values() if s['user_id'] == user_id and s['word_language_id'] == lang
                and s['result']]
        return sorted(rows, key=lambda s: s['ended_at'])[-1] if rows else None

    def response_rows(self, sid):
        return [r for r in self.responses if r['session_id'] == sid and r['probe_kind'] is None
                and r['answered_at'] is not None]

    # ---------------------------------------------------------------- helpers
    def _rows(self, sid):
        return [r for r in self.responses if r['session_id'] == sid]

    def _word(self, lang, vid):
        for band in self.pool[lang]:
            for w in band:
                if w['vocab_id'] == vid:
                    return w
        raise KeyError(vid)

    def _build_meaning(self, s, band):
        lang = s['word_language_id']
        used = {r['anchor_vocab_id'] for r in self.responses if r['user_id'] == s['user_id']
                and r['answered_at'] is not None} | {r['anchor_vocab_id'] for r in self._rows(s['id'])}
        order = sorted(range(1, 8), key=lambda b: (abs(b - band), b))
        for b in order:
            free = [w for w in self.pool[lang][b - 1] if w['vocab_id'] not in used]
            if free:
                w = free[0]
                key = self.rng.randrange(4)
                row = dict(id=next(self.ids), session_id=s['id'], user_id=s['user_id'], anchor_sense_id=w['sense_id'],
                           anchor_vocab_id=w['vocab_id'], item_kind='meaning', probe_kind=None, is_correct=None,
                           chosen_position=None, chosen_sense_id=None, answered_at=None, pair_response_id=None,
                           option_roles=None, option_texts=None, zipf_band=w['band'], key_position=key,
                           latency_ms=None)
                self.responses.append(row)
                return self._payload(row, w)
        return {'exhausted': True}

    def _build_reading(self, s, meaning_row):
        w = self._word(s['word_language_id'], meaning_row['anchor_vocab_id'])
        if s['word_language_id'] == 1:
            roles = ['K', 'KT', 'F', 'FT']
            self.rng.shuffle(roles)
            key = roles.index('K')
        else:
            roles, key = None, self.rng.randrange(4)
        row = dict(meaning_row, id=next(self.ids), item_kind='reading', is_correct=None, chosen_position=None,
                   answered_at=None, pair_response_id=meaning_row['id'], option_roles=roles, key_position=key,
                   option_texts=[f'r{i}' for i in range(4)], latency_ms=None)
        self.responses.append(row)
        return self._payload(row, w)

    def _payload(self, row, w):
        return dict(response_id=row['id'], vocab_id=w['vocab_id'], lemma=w['lemma'], band=w['band'],
                    kind=row['item_kind'], probe_kind=None, options=[f'o{i}' for i in range(4)], idk_allowed=True)

    def tallies(self, sid):
        s = self.sessions[sid]
        lang = s['word_language_id']
        zh = lang == 1
        rows = [r for r in self._rows(sid) if r['answered_at'] is not None]
        reading_of = {r['pair_response_id']: r for r in rows if r['item_kind'] == 'reading'}
        m = [[0, 0, 0] for _ in range(7)]
        mr = [[0, 0, 0, 0] if zh else [0, 0, 0] for _ in range(7)]
        for r in rows:
            if r['item_kind'] != 'meaning':
                continue
            b = r['zipf_band'] - 1
            idk = r['chosen_position'] is None
            m[b][0] += 1
            m[b][1] += bool(r['is_correct'])
            m[b][2] += (not idk) and not r['is_correct']
            w = self._word(lang, r['anchor_vocab_id'])
            rd = reading_of.get(r['id'])
            if r['is_correct'] and not w['exempt'] and rd is None:
                continue                                        # pending pair
            mr[b][0] += 1
            if w['exempt']:
                mr[b][1] += bool(r['is_correct'])
                if not zh:
                    mr[b][2] += (not idk) and not r['is_correct']
            elif rd is not None:
                if zh:
                    role = rd['option_roles'][rd['chosen_position']] if rd['chosen_position'] is not None else None
                    mr[b][1] += role == 'K'
                    mr[b][2] += role == 'KT'
                    mr[b][3] += role in ('F', 'FT')
                else:
                    mr[b][1] += bool(rd['is_correct'])
                    mr[b][2] += rd['chosen_position'] is not None and not rd['is_correct']
        lat = [min(int(r['latency_ms'] or 0), 60000) for r in rows]
        scored = len(rows)
        return dict(m=m, mr=mr, scored=scored, probes=0, active_ms=sum(lat),
                    median_latency_ms=int(median(lat)) if lat else None,
                    warmup_done=pd.warmup_done(dict(m=m)))

    def inputs(self, user_id, lang, dlang, session_id=None):
        zh = lang == 1
        if session_id:
            rows = [r for r in self._rows(session_id) if r['answered_at'] is not None]
        else:
            sids = {s['id'] for s in self.sessions.values() if s['user_id'] == user_id and s['word_language_id'] == lang
                    and s['definition_language_id'] == dlang}
            rows = [r for r in self.responses if r['session_id'] in sids and r['answered_at'] is not None]
        reading_of = {r['pair_response_id']: r for r in rows if r['item_kind'] == 'reading'}
        bands = [[0, 0, 0] for _ in range(7)]
        pairs = [[0, 0, 0, 0] if zh else [0, 0, 0] for _ in range(7)]
        gap = [[0, 0, 0, 0, 0] if zh else [0, 0, 0, 0] for _ in range(7)]
        for r in rows:
            if r['item_kind'] != 'meaning':
                continue
            b = r['zipf_band'] - 1
            idk = r['chosen_position'] is None
            bands[b][0] += 1
            bands[b][1] += idk
            bands[b][2] += bool(r['is_correct'])
            w = self._word(lang, r['anchor_vocab_id'])
            rd = reading_of.get(r['id'])
            if r['is_correct'] and not w['exempt'] and rd is None:
                continue
            pairs[b][0] += 1
            gap[b][0] += 1
            if not r['is_correct']:
                if not idk:
                    gap[b][3] += 1
                    if w['exempt'] and not zh:
                        pairs[b][2] += 1
                continue
            if w['exempt']:
                pairs[b][1] += 1
                continue
            ridk = rd['chosen_position'] is None
            if zh:
                role = None if ridk else rd['option_roles'][rd['chosen_position']]
                pairs[b][1] += role == 'K'
                pairs[b][2] += role == 'KT'
                pairs[b][3] += role in ('F', 'FT')
                gap[b][1] += role in ('F', 'FT')
                gap[b][2] += ridk
                gap[b][4] += role == 'KT'
            else:
                pairs[b][1] += bool(rd['is_correct'])
                pairs[b][2] += (not ridk) and not rd['is_correct']
                gap[b][1] += (not ridk) and not rd['is_correct']
                gap[b][2] += ridk
        out = dict(definition_language_id=dlang, instrument='meaning_bare_v1', bands=bands)
        if lang != 2:
            out.update(pairs=pairs, gap=gap)
        return out

    # ---------------------------------------------------------------- RPCs
    def rpc(self, name, p):
        self.rpc_calls.append(name)
        if name == 'knowledge_frame_bands':
            return dict(FRAMES)
        if name == 'knowledge_calibration_inputs':
            return self.inputs(p['p_user_id'], p['p_language_id'], p.get('p_definition_language_id'),
                               p.get('p_session_id'))
        if name == 'calibration_placement_close_stale':
            ids = []
            for s in self.sessions.values():
                if s['ended_at'] is None and (p['p_user_id'] is None or s['user_id'] == p['p_user_id']) \
                        and self.now - s['last_activity'] > timedelta(hours=24):
                    self._close(s, 'abandoned')
                    ids.append(s['id'])
            return ids
        s = self.sessions.get(str(p.get('p_session_id')))
        if not s or s['user_id'] != p['p_user_id']:
            raise cp.PlacementError('Placement session not found', 404, 'NOT_FOUND')
        if name == 'calibration_placement_next_item':
            pending = [r for r in self._rows(s['id']) if r['answered_at'] is None]
            if pending:
                r = pending[-1]
                return self._payload(r, self._word(s['word_language_id'], r['anchor_vocab_id']))
            return self._build_meaning(s, int(p['p_band']))
        if name == 'calibration_placement_close':
            return {'tallies': self._close(s, p['p_reason'])}
        if name == 'calibration_placement_answer':
            return self._answer(s, p)
        raise AssertionError(f'unexpected rpc {name}')

    def _close(self, s, reason):
        self.responses = [r for r in self.responses if not (r['session_id'] == s['id'] and r['answered_at'] is None)]
        if s['ended_at'] is None:
            s['ended_at'] = self.now
            s['stop_reason'] = reason
        return self.tallies(s['id'])

    def _answer(self, s, p):
        if s['ended_at'] is not None:
            raise cp.PlacementError('session closed', 400)
        row = next((r for r in self._rows(s['id']) if r['id'] == p['p_response_id']), None)
        if row is None or row['answered_at'] is not None:
            raise cp.PlacementError('already answered or not in this session', 400)
        pos = p['p_position']
        row.update(chosen_position=pos, is_correct=pos is not None and pos == row['key_position'],
                   answered_at=self.now, latency_ms=p['p_latency_ms'] or 6000)
        s['last_activity'] = self.now
        lang = s['word_language_id']
        w = self._word(lang, row['anchor_vocab_id'])
        reveal, next_item, exhausted = None, None, False
        role = row['option_roles'][pos] if row['option_roles'] and pos is not None else None
        if row['item_kind'] == 'meaning' and row['is_correct'] and not w['exempt']:
            next_item = self._build_reading(s, row)
        else:
            reveal = dict(lemma=w['lemma'], reading='r', meaning='m',
                          parts=[dict(kind=row['item_kind'], probe_kind=None, is_correct=row['is_correct'],
                                      tone_only_miss=role == 'KT')])
            if p['p_next_band'] is not None:
                next_item = self._build_meaning(s, int(p['p_next_band']))
                if next_item.get('exhausted'):
                    next_item, exhausted = None, True
        return dict(answer=dict(is_correct=row['is_correct'], skipped=pos is None, kind=row['item_kind'],
                                probe_kind=None, role=role),
                    reveal=reveal, next_item=next_item, exhausted=exhausted, tallies=self.tallies(s['id']))

    # ---------------------------------------------------------------- scripted learner
    def key_of(self, response_id):
        return next(r['key_position'] for r in self.responses if r['id'] == response_id)

    def roles_of(self, response_id):
        return next(r['option_roles'] for r in self.responses if r['id'] == response_id)
