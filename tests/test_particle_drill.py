"""Particle drill: markup, validator, catalog, content service
and routes. Offline: the content is files under data/particle_drill and the
progress store is given a fake client.
"""
import json
import os
import sys
from unittest.mock import patch

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import particle_drill_build as build  # noqa: E402
import particle_drill_catalog as catalog_src  # noqa: E402
import particle_drill_validate as validate  # noqa: E402
from services.particle_drill import content as content_mod  # noqa: E402
from services.particle_drill import markup  # noqa: E402

FIXTURES = os.path.join(ROOT, 'tests', 'fixtures', 'particle_drill')
CATALOG = validate.load_catalog()
SKILLS = {s['id']: s for s in CATALOG['skills']}

GOOD = {
    'jp': '私[わたし]{は|wa-topic}毎朝[まいあさ]七時[しちじ]{に|ni-time}起[お]きます。',
    'en': 'I get up at seven every morning.', 'f': 1, 'd': ['で', 'を', 'が'],
    'why': 'A clock time you can point to takes に.', 'lv': 5,
}


def _errors(item, skill='ni-time'):
    return validate.check_item(item, skill, SKILLS)


# --------------------------------------------------------------------------- markup
def test_markup_matches_the_shared_cases():
    """The same file drives the JS parser (tests/unit/particle-drill-engine.test.js)."""
    with open(os.path.join(FIXTURES, 'markup_cases.json'), encoding='utf-8') as fh:
        cases = json.load(fh)
    for case in cases:
        _segments, slots, errors = markup.parse(case['jp'])
        assert markup.plain(case['jp']) == case['plain']
        assert [[s['a'], s['alt'], s['skill']] for s in slots] == case['slots']
        assert len(errors) == case['errors'], (case['jp'], errors)


def test_markup_blank_and_expand():
    assert markup.plain(GOOD['jp'], blank='＿') == '私＿毎朝七時＿起きます。'
    assert markup.expand('<who>{は|wa-topic}<act>。', {'who': '母[はは]', 'act': '寝[ね]た'}) \
        == '母[はは]{は|wa-topic}寝[ね]た。'
    _seg, _slots, errors = markup.parse('<who>{は|wa-topic}')
    assert errors and 'variable' in errors[0]
    assert markup.parse('<who>{は|wa-topic}', allow_vars=True)[2] == []


# ------------------------------------------------------------------------ validator
def test_a_good_item_passes():
    assert _errors(GOOD) == []


@pytest.mark.parametrize('change, fragment', [
    ({'jp': '私は七時{に|ni-time}起[お]きます。'}, 'kanji without furigana'),
    ({'jp': '私[わたし]{は|wa-topic}7時[じ]{に|ni-time}起[お]きます。'}, 'digits'),
    ({'jp': '私[わたし]{は|wa-topic}七時[しちじ]{に|ni-tim}起[お]きます。'}, 'unknown skill'),
    ({'jp': '私[わたし]{は|wa-topic}七時[しちじ]{に|ni-time}起[お]きます'}, 'must end'),
    ({'f': 0}, "is not this file's skill"),
    ({'f': 5}, 'f must index a slot'),
    ({'d': ['で', 'を']}, 'd needs 3'),
    ({'d': ['で', 'を', 'に']}, 'is an accepted answer'),
    ({'d': ['で', 'を', 'wo']}, 'must be kana'),
    ({'d': ['で', 'で', 'が']}, 'repeated distractor'),
    ({'why': 'short'}, 'why must be'),
    ({'lv': 0}, 'lv must be'),
    ({'en': ''}, 'en missing'),
    ({'en': '七時に起きる'}, 'en missing'),
    ({'extra': 1}, 'unknown fields'),
])
def test_bad_items_are_rejected(change, fragment):
    errors = _errors({**GOOD, **change})
    assert any(fragment in e for e in errors), errors


def test_an_alternative_cannot_also_be_a_distractor():
    item = {**GOOD, 'jp': '駅[えき]{に/へ|ni-destination}行[い]きます。', 'f': 0, 'd': ['で', 'を', 'へ']}
    assert any('accepted answer' in e for e in _errors(item, 'ni-destination'))


def test_compound_particles_are_written_in_kanji_with_furigana():
    item = {'jp': '親[おや]{に対[たい]して|nitaishite}失礼[しつれい]だ。', 'en': 'That is rude to parents.',
            'f': 0, 'd': ['に関[かん]して', 'にとって', 'として'],
            'why': 'に対して marks the target of an attitude.', 'lv': 3}
    assert _errors(item, 'nitaishite') == []
    assert markup.strip_reading('に対[たい]して') == 'に対して'
    assert markup.reading_of('に対[たい]して') == 'にたいして'
    # The kana spelling of the answer, and bare kanji, are both refused as distractors.
    assert any('accepted answer' in e for e in _errors({**item, 'd': ['にたいして', 'にとって', 'として']}, 'nitaishite'))
    assert any('kanji with furigana' in e for e in _errors({**item, 'd': ['に関して', 'にとって', 'として']}, 'nitaishite'))


def test_clinic_files_take_one_to_three_distractors_and_any_focus_skill():
    item = {**GOOD, 'f': 0, 'd': ['が']}
    assert _errors(item, 'x-wa-ga') == []
    assert any('1-3' in e for e in _errors({**item, 'd': []}, 'x-wa-ga'))


def _pack(**over):
    values = lambda *pairs: [list(p) for p in pairs]  # noqa: E731
    pack = {
        'id': 'de-place-1', 'lv': 5,
        'tpl': '<who>{は|wa-topic}<place>{で|de-place}<act>。', 'en': '<who> <act> at <place>.',
        'f': 1, 'd': ['に', 'を', 'が'], 'why': 'The place where an action happens takes で.',
        'vars': {
            'who': values(('母[はは]', 'My mother'), ('父[ちち]', 'My father'), ('姉[あね]', 'My sister'),
                          ('兄[あに]', 'My brother'), ('弟[おとうと]', 'My little brother')),
            'place': values(('家[いえ]', 'home'), ('図書館[としょかん]', 'the library'), ('学校[がっこう]', 'school'),
                            ('公園[こうえん]', 'the park'), ('部屋[へや]', 'the room')),
            'act': values(('本[ほん]{を|o-object}読[よ]みました', 'read a book'), ('休[やす]みました', 'rested'),
                          ('音楽[おんがく]{を|o-object}聞[き]きました', 'listened to music'),
                          ('手紙[てがみ]{を|o-object}書[か]きました', 'wrote a letter')),
        },
    }
    pack.update(over)
    return pack


def _check_packs(tmp_path, packs, name='de-place.json'):
    d = tmp_path / 'packs'
    d.mkdir(exist_ok=True)
    path = d / name
    path.write_text(json.dumps(packs, ensure_ascii=False), encoding='utf-8')
    return validate.check_packs_file(str(path), SKILLS)


def test_a_good_pack_passes_and_expands(tmp_path):
    errors, count = _check_packs(tmp_path, [_pack()])
    assert (errors, count) == ([], 1)
    item = validate.expand_pack(_pack(), {'who': 0, 'place': 1, 'act': 0})
    assert markup.plain(item['jp']) == '母は図書館で本を読みました。'
    assert item['en'] == 'My mother read a book at the library.'


def test_a_pack_value_that_breaks_the_markup_is_found(tmp_path):
    bad = _pack()
    bad['vars']['place'][4] = ['部屋', 'the room']               # no furigana, last value
    errors, _ = _check_packs(tmp_path, [bad])
    assert any('kanji without furigana' in e for e in errors)


def test_a_pack_needs_enough_combinations_and_declared_variables(tmp_path):
    small = _pack()
    small['vars']['who'] = small['vars']['who'][:4]
    small['vars']['place'] = small['vars']['place'][:4]
    assert any('combinations' in e for e in _check_packs(tmp_path, [small])[0])
    assert any('has no values' in e for e in _check_packs(tmp_path, [_pack(en='<who> <act> at <where>.')])[0])


def test_lexicon_classes_are_checked(tmp_path):
    d = tmp_path / 'conjugation'
    d.mkdir()
    path = d / 'verbs_x.json'
    rows = [
        {'d': '帰る', 'k': 'かえる', 'c': 'godan', 't': 'i', 'en': 'return', 'lv': 5},
        {'d': '書く', 'k': 'かく', 'c': 'ichidan', 't': 't', 'en': 'write', 'lv': 5},
        {'d': '勉強する', 'k': 'べんきょう', 'c': 'suru', 't': 't', 'en': 'study', 'lv': 5},
        {'d': '見る', 'k': 'ミル', 'c': 'ichidan', 't': 't', 'en': 'see', 'lv': 5},
    ]
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    errors, count = validate.check_lexicon_file(str(path))
    assert count == 4
    text = '\n'.join(errors)
    assert '[0]' not in text
    assert '[1]: ichidan verb must end in -iru / -eru' in text
    assert '[2]' in text and '[3]: k must be hiragana' in text


# -------------------------------------------------------------------------- catalog
def test_catalog_file_is_what_the_source_script_builds():
    built, total = catalog_src.build()
    assert total == catalog_src.TARGET_TOTAL == 10000
    assert built == CATALOG, 'run: python scripts/particle_drill_catalog.py --apply'


def test_catalog_is_consistent():
    ids = [s['id'] for s in CATALOG['skills']]
    assert len(ids) == len(set(ids))
    groups = [g for st in CATALOG['stages'] for g in st['groups']]
    assert sorted(k for g in groups for k in g['skills']) == sorted(ids)
    for s in CATALOG['skills']:
        assert s['lv'] in (1, 2, 3, 4, 5) and s['n'] >= 20 and s['conf']


# ------------------------------------------------------------------ shipped content
def test_shipped_content_validates():
    errors = build.validation_errors(validate.ROOT)
    assert errors == [], errors[:10]


def test_manifest_is_current():
    with open(os.path.join(validate.ROOT, 'manifest.json'), encoding='utf-8') as fh:
        manifest = json.load(fh)
    assert manifest == build.build_manifest(validate.ROOT), \
        'content changed: run python scripts/particle_drill_build.py --apply'


def test_every_skill_has_exercises_and_a_guide():
    content = content_mod.Content(validate.ROOT)
    short = {sid: len(content.items(sid)) for sid, s in content.skills.items()
             if len(content.items(sid)) < s['n']}
    assert not short, f'skills under their target: {short}'
    assert sum(len(content.items(sid)) for sid in content.skills) >= 10000
    missing = [sid for sid in content.skills if not content.skill_guide(sid)]
    assert not missing, missing
    conj = content.conjugation_payload()
    assert len(conj['verbs']) >= 300 and len(conj['adjectives']) >= 150 and len(conj['guide']) == 21


def test_every_authored_batch_has_a_review_record():
    """Each content file was checked by a reviewer in a separate context."""
    reviewed = set()
    review_dir = os.path.join(validate.ROOT, 'review')
    for name in os.listdir(review_dir):
        with open(os.path.join(review_dir, name), encoding='utf-8') as fh:
            reviewed.update(json.load(fh).get('files') or [])
    reviewed = {os.path.basename(f) for f in reviewed}
    unreviewed = [os.path.relpath(p, validate.ROOT) for p in build.content_files(validate.ROOT)[1:]
                  if os.path.basename(p) not in reviewed]
    assert not unreviewed, unreviewed[:20]


# ------------------------------------------------------------------ content service
@pytest.fixture()
def tiny_root(tmp_path):
    root = tmp_path / 'ja'
    for sub in ('items', 'packs', 'guides', 'conjugation'):
        (root / sub).mkdir(parents=True)
    cat = {'language': 'ja', 'version': 1,
           'stages': [{'id': 'core1', 'title': 'Core', 'blurb': 'b',
                       'groups': [{'id': 'ni', 'p': 'に', 'name': 'Point', 'skills': ['ni-time', 'ni-location']}]}],
           'skills': [{'id': 'ni-time', 'group': 'ni', 'stage': 'core1', 'p': 'に', 'title': 'Time',
                       'lv': 5, 'n': 2, 'conf': ['で'], 'packs': 1},
                      {'id': 'ni-location', 'group': 'ni', 'stage': 'core1', 'p': 'に', 'title': 'Place',
                       'lv': 5, 'n': 2, 'conf': ['で'], 'packs': 0}]}
    (root / 'catalog.json').write_text(json.dumps(cat, ensure_ascii=False), encoding='utf-8')
    line = json.dumps(GOOD, ensure_ascii=False)
    other = json.dumps({**GOOD, 'jp': GOOD['jp'].replace('七時[しちじ]', '八時[はちじ]')}, ensure_ascii=False)
    (root / 'items' / 'ni-time.jsonl').write_text(line + '\n', encoding='utf-8')
    (root / 'items' / 'ni-time__2.jsonl').write_text(line + '\n' + other + '\n', encoding='utf-8')
    (root / 'guides' / 'ni.json').write_text(json.dumps({
        'group': 'ni', 'intro': 'に is a point.',
        'skills': [{'id': 'ni-time', 'rule': 'Clock times take に.'}, {'id': 'ni-location', 'rule': 'Places.'}],
    }), encoding='utf-8')
    (root / 'conjugation' / 'verbs_n5.json').write_text(json.dumps(
        [{'d': '行く', 'k': 'いく', 'c': 'godan', 't': 'i', 'en': 'go', 'lv': 5}]), encoding='utf-8')
    (root / 'conjugation' / 'verbs_n4.json').write_text(json.dumps(
        [{'d': '行く', 'k': 'いく', 'c': 'godan', 't': 'i', 'en': 'go', 'lv': 5},
         {'d': '決める', 'k': 'きめる', 'c': 'ichidan', 't': 't', 'en': 'decide', 'lv': 4}]), encoding='utf-8')
    return str(root)


def test_content_merges_part_files_and_drops_repeats(tiny_root):
    content = content_mod.Content(tiny_root)
    items = content.items('ni-time')
    assert len(items) == 2
    assert items[0]['id'] == content_mod.item_id(GOOD['jp']) and len(items[0]['id']) == 10
    assert content.items('ni-location') == []
    payload = content.catalog_payload()
    assert [(s['id'], s['items'], s['packs']) for s in payload['skills']] == \
        [('ni-time', 2, 0), ('ni-location', 0, 0)]
    # the target count stays on the server; conf goes out (the client picks companions from it)
    assert 'n' not in payload['skills'][0] and payload['skills'][0]['conf'] == ['で']


def test_skill_payload_carries_guide_items_and_packs(tiny_root):
    content = content_mod.Content(tiny_root)
    payload = content.skill_payload('ni-time')
    assert payload['skill']['conf'] == ['で']
    assert payload['guide'] == {'id': 'ni-time', 'rule': 'Clock times take に.', 'intro': 'に is a point.'}
    assert payload['group']['skills'] == ['ni-time', 'ni-location']
    assert len(payload['items']) == 2 and payload['packs'] == []
    assert content.skill_payload('nope') is None


def test_conjugation_lexicon_parts_are_merged_without_repeats(tiny_root):
    conj = content_mod.Content(tiny_root).conjugation_payload()
    assert [w['d'] for w in conj['verbs']] == ['行く', '決める']
    assert conj['adjectives'] == [] and conj['guide'] == []


def test_manifest_counts_and_version_follow_the_files(tiny_root):
    first = build.build_manifest(tiny_root)
    assert first['skills']['ni-time'] == {'items': 2, 'packs': 0}
    assert first['totals']['items'] == 2 and first['totals']['verbs'] == 2
    with open(os.path.join(tiny_root, 'items', 'ni-location.jsonl'), 'w', encoding='utf-8') as fh:
        fh.write(json.dumps({**GOOD, 'jp': '家[いえ]{に|ni-location}います。', 'f': 0}, ensure_ascii=False) + '\n')
    second = build.build_manifest(tiny_root)
    assert second['version'] != first['version']
    assert second['skills']['ni-location']['items'] == 1


def test_only_japanese_has_content():
    assert content_mod.get_content(3) is not None
    assert content_mod.get_content(1) is None and content_mod.get_content(2) is None


# --------------------------------------------------------------------------- routes
def _json(resp):
    return json.loads(resp.data)


def test_routes_need_a_login(client):
    for path in ('/catalog', '/skill/ni-time', '/conjugation'):
        assert client.get(f'/api/particle-drill{path}?language_id=3').status_code == 401


def test_catalog_route(client, auth_headers):
    resp = client.get('/api/particle-drill/catalog?language_id=3', headers=auth_headers)
    assert resp.status_code == 200
    body = _json(resp)
    assert len(body['skills']) == len(SKILLS) and body['stages'][0]['id'] == 'core1'
    assert resp.headers['Cache-Control'] == 'private, max-age=3600'
    again = client.get('/api/particle-drill/catalog?language_id=3',
                       headers={**auth_headers, 'If-None-Match': resp.headers['ETag']})
    assert again.status_code == 304 and again.data == b''


def test_content_routes_are_japanese_only(client, auth_headers):
    for path in ('/catalog', '/skill/ni-time', '/conjugation'):
        resp = client.get(f'/api/particle-drill{path}?language_id=1', headers=auth_headers)
        assert resp.status_code == 400, path
        assert client.get(f'/api/particle-drill{path}', headers=auth_headers).status_code == 400


def test_skill_route(client, auth_headers):
    resp = client.get('/api/particle-drill/skill/ni-time?language_id=3', headers=auth_headers)
    assert resp.status_code == 200
    body = _json(resp)
    assert body['skill']['id'] == 'ni-time' and body['group']['id'] == 'ni'
    assert {'guide', 'items', 'packs'} <= set(body)
    assert client.get('/api/particle-drill/skill/nope?language_id=3', headers=auth_headers).status_code == 404


def test_conjugation_route(client, auth_headers):
    body = _json(client.get('/api/particle-drill/conjugation?language_id=3', headers=auth_headers))
    assert {'guide', 'verbs', 'adjectives'} <= set(body)


# ------------------------------------------------- the learner's own words (conjugation)
from services.particle_drill import conjugation  # noqa: E402


@pytest.mark.parametrize('lemma, reading, pos, raw, want', [
    ('書く', 'かく', 'verb', '動詞', 'godan'),
    ('帰る', 'かえる', 'verb', '動詞', 'godan'),          # -eru but godan
    ('入る', 'はいる', 'verb', '動詞', 'godan'),
    ('切る', 'きる', 'verb', '動詞', 'godan'),
    ('着る', 'きる', 'verb', '動詞', 'ichidan'),
    ('食べる', 'たべる', 'verb', '動詞', 'ichidan'),
    ('信じる', 'しんじる', 'verb', '動詞', 'ichidan'),
    ('来る', 'くる', 'verb', '動詞', 'kuru'),
    ('する', 'する', 'verb', '動詞', 'suru'),
    ('勉強する', 'べんきょうする', 'verb', '動詞', 'suru'),
    ('高い', 'たかい', 'adjective', '形容詞', 'i'),
    ('静か', 'しずか', 'adjective', '形状詞', 'na'),
    ('きれい', 'きれい', 'adjective', '形状詞', 'na'),      # ends in い, still な
    ('有名', 'ゆうめい', 'adjective', '形状詞', 'na'),
    # Left out: the rule engine would produce wrong forms.
    ('いらっしゃる', 'いらっしゃる', 'verb', '動詞', None),
    ('くださる', 'くださる', 'verb', '動詞', None),
    ('問う', 'とう', 'verb', '動詞', None),
    ('愛する', 'あいする', 'verb', '動詞', None),
    ('存ずる', 'ぞんずる', 'verb', '動詞', None),
    ('持って来る', 'もってくる', 'verb', '動詞', None),
    ('学校', 'がっこう', 'noun', '名詞', None),
])
def test_classify_known_words(lemma, reading, pos, raw, want):
    pytest.importorskip('fugashi')
    got = conjugation.classify(lemma, reading, pos, raw)
    assert (got or {}).get('c') == want, got
    if want:
        assert got['d'] == lemma and got['k'] == reading


def test_classify_fills_a_missing_reading_and_fixes_katakana():
    pytest.importorskip('fugashi')
    assert conjugation.classify('読む', None, 'verb', '動詞') == {'d': '読む', 'k': 'よむ', 'c': 'godan'}
    assert conjugation.classify('飲む', 'ノム', 'verb', '動詞')['k'] == 'のむ'


def test_tagger_classes_agree_with_the_reviewed_word_lists():
    """Two independent sources for the class of every listed verb: the reviewed list and UniDic."""
    pytest.importorskip('fugashi')
    conj = content_mod.Content(validate.ROOT).conjugation_payload()
    disagree, covered = [], 0
    for w in conj['verbs']:
        got = conjugation.classify(w['d'], w['k'], 'verb', '動詞')
        if got is None:
            continue                       # left out by the safety rules; the list's class stands
        covered += 1
        if got['c'] != w['c']:
            disagree.append((w['d'], w['c'], got['c']))
    assert not disagree, disagree
    assert covered >= 0.85 * len(conj['verbs'])


class _KnowledgeDb:
    """Answers the four reads of conjugation.known_words from in-memory rows."""

    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return _KnowledgeQuery(self.tables[name])


class _KnowledgeQuery:
    def __init__(self, rows):
        self.rows = list(rows)

    def select(self, *_a, **_k):
        return self

    def eq(self, col, value):
        self.rows = [r for r in self.rows if r.get(col) == value]
        return self

    def in_(self, col, values):
        self.rows = [r for r in self.rows if r.get(col) in values]
        return self

    def order(self, col, desc=False):
        self.rows.sort(key=lambda r: r.get(col) or 0, reverse=desc)
        return self

    def range(self, start, end):
        self.rows = self.rows[start:end + 1]
        return self

    def execute(self):
        return type('R', (), {'data': self.rows})()


def _knowledge_db():
    uvk = [
        {'user_id': 'u1', 'language_id': 3, 'sense_id': 1, 'p_known': 0.97, 'status': 'known'},
        {'user_id': 'u1', 'language_id': 3, 'sense_id': 2, 'p_known': 0.70, 'status': 'learning'},
        {'user_id': 'u1', 'language_id': 3, 'sense_id': 3, 'p_known': 0.90, 'status': 'probably_known'},
        {'user_id': 'u1', 'language_id': 3, 'sense_id': 4, 'p_known': 0.10, 'status': 'unknown'},
        {'user_id': 'u1', 'language_id': 3, 'sense_id': 5, 'p_known': 0.95, 'status': 'known'},
        {'user_id': 'u1', 'language_id': 3, 'sense_id': 6, 'p_known': 0.99, 'status': 'known'},
        {'user_id': 'u2', 'language_id': 3, 'sense_id': 7, 'p_known': 0.99, 'status': 'known'},
    ]
    senses = [
        {'id': 1, 'vocab_id': 11, 'definition_language_id': 3, 'definition': '字を…', 'sense_rank': 1},
        {'id': 2, 'vocab_id': 12, 'definition_language_id': 3, 'definition': '…', 'sense_rank': 1},
        {'id': 3, 'vocab_id': 13, 'definition_language_id': 3, 'definition': '…', 'sense_rank': 1},
        {'id': 4, 'vocab_id': 14, 'definition_language_id': 3, 'definition': '…', 'sense_rank': 1},
        {'id': 5, 'vocab_id': 15, 'definition_language_id': 3, 'definition': '…', 'sense_rank': 1},
        {'id': 6, 'vocab_id': 16, 'definition_language_id': 3, 'definition': '…', 'sense_rank': 1},
        {'id': 7, 'vocab_id': 17, 'definition_language_id': 3, 'definition': '…', 'sense_rank': 1},
        {'id': 21, 'vocab_id': 11, 'definition_language_id': 2, 'definition': 'to write', 'sense_rank': 1},
        {'id': 22, 'vocab_id': 11, 'definition_language_id': 2, 'definition': 'to draw', 'sense_rank': 2},
        {'id': 23, 'vocab_id': 13, 'definition_language_id': 2, 'definition': 'x' * 200, 'sense_rank': 1},
    ]
    vocab = [
        {'id': 11, 'language_id': 3, 'lemma': '書く', 'reading': 'かく', 'part_of_speech': 'verb', 'part_of_speech_raw': '動詞', 'level_tag': 'N5'},
        {'id': 12, 'language_id': 3, 'lemma': '帰る', 'reading': 'かえる', 'part_of_speech': 'verb', 'part_of_speech_raw': '動詞', 'level_tag': None},
        {'id': 13, 'language_id': 3, 'lemma': '静か', 'reading': 'しずか', 'part_of_speech': 'adjective', 'part_of_speech_raw': '形状詞', 'level_tag': 'N4'},
        {'id': 14, 'language_id': 3, 'lemma': '読む', 'reading': 'よむ', 'part_of_speech': 'verb', 'part_of_speech_raw': '動詞', 'level_tag': 'N5'},
        {'id': 15, 'language_id': 3, 'lemma': '学校', 'reading': 'がっこう', 'part_of_speech': 'noun', 'part_of_speech_raw': '名詞', 'level_tag': 'N5'},
        {'id': 16, 'language_id': 3, 'lemma': 'いらっしゃる', 'reading': 'いらっしゃる', 'part_of_speech': 'verb', 'part_of_speech_raw': '動詞', 'level_tag': 'N4'},
        {'id': 17, 'language_id': 3, 'lemma': '飲む', 'reading': 'のむ', 'part_of_speech': 'verb', 'part_of_speech_raw': '動詞', 'level_tag': 'N5'},
    ]
    return _KnowledgeDb({'user_vocabulary_knowledge': uvk, 'dim_word_senses': senses, 'dim_vocabulary': vocab})


def test_known_words_come_from_the_learners_vocabulary():
    pytest.importorskip('fugashi')
    lexicon = {'verbs': [{'d': '帰る', 'k': 'かえる', 'c': 'godan', 't': 'i', 'en': 'go home', 'lv': 5}],
               'adjectives': []}
    out = conjugation.known_words(_knowledge_db(), 'u1', 3, lexicon)
    words = {w['d']: w for w in out['words']}
    # Known, probably known and learning words; not the unknown one, the noun or another user's.
    assert set(words) == {'書く', '帰る', '静か'}
    assert [w['d'] for w in out['words']] == ['書く', '静か', '帰る']        # most confident first
    assert words['書く'] == {'d': '書く', 'k': 'かく', 'c': 'godan', 'en': 'to write', 'known': True, 'lv': 5}
    assert words['帰る']['c'] == 'godan' and words['帰る']['en'] == 'go home'   # class and gloss from the list
    assert words['静か']['c'] == 'na' and len(words['静か']['en']) == conjugation.GLOSS_CHARS
    assert (out['verbs'], out['adjectives'], out['skipped']) == (2, 1, 1)     # いらっしゃる left out


def test_known_words_for_a_new_learner_is_empty():
    assert conjugation.known_words(_knowledge_db(), 'nobody', 3, {'verbs': [], 'adjectives': []}) == \
        {'words': [], 'verbs': 0, 'adjectives': 0, 'skipped': 0}


def test_conjugation_words_route(client, auth_headers):
    payload = {'words': [{'d': '書く', 'k': 'かく', 'c': 'godan', 'en': 'to write', 'known': True, 'lv': 5}],
               'verbs': 1, 'adjectives': 0, 'skipped': 0}
    with patch('routes.particle_drill.conjugation.known_words', return_value=payload) as known, \
            patch('routes.particle_drill._gloss_language_id', return_value=2):
        resp = client.get('/api/particle-drill/conjugation/words?language_id=3', headers=auth_headers)
    assert resp.status_code == 200 and _json(resp)['words'] == payload['words']
    assert known.call_args.args[2] == 3 and known.call_args.kwargs == {'gloss_language_id': 2}
    assert client.get('/api/particle-drill/conjugation/words?language_id=1', headers=auth_headers).status_code == 400
    assert client.get('/api/particle-drill/conjugation/words?language_id=3').status_code == 401
