"""Grammar drill (the second sentence-drill course) and the reading drill.

Catalog, the kanji question kinds in the validator, the course switch of the
content service and routes, and the shipped content of data/particle_drill/ja-grammar.
The shared machinery is covered by tests/test_particle_drill.py.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import grammar_drill_catalog as catalog_src  # noqa: E402
import particle_drill_build as build  # noqa: E402
import particle_drill_validate as validate  # noqa: E402
from services.particle_drill import content as content_mod  # noqa: E402

GROOT = os.path.join(ROOT, 'data', 'particle_drill', 'ja-grammar')
CATALOG = validate.load_catalog(GROOT)
SKILLS = {s['id']: s for s in CATALOG['skills']}


def _item(**over):
    item = {'jp': '{今朝[けさ]|ym-n5-time}は早[はや]く起[お]きました。', 'en': 'I got up early this morning.',
            'f': 0, 'd': ['こんあさ', 'いまあさ', 'こんちょう'],
            'why': 'The word for this morning has its own reading.', 'lv': 5}
    item.update(over)
    return item


# ------------------------------------------------------------------ catalog
def test_catalog_file_is_what_the_source_script_builds():
    built, total = catalog_src.base.build(catalog_src.STAGES, catalog_src.TARGET_TOTAL)
    built['course'] = 'grammar'
    assert built == CATALOG
    assert total == 8000 == sum(s['n'] for s in CATALOG['skills'])


def test_skill_ids_are_unique_across_both_courses():
    """Progress is one document keyed by skill id."""
    particles = {s['id'] for s in validate.load_catalog(os.path.join(ROOT, 'data', 'particle_drill', 'ja'))['skills']}
    assert not particles & set(SKILLS)


def test_the_twelve_areas_are_there():
    assert [st['id'] for st in CATALOG['stages']] == [
        'give', 'trans', 'keigo', 'kosoado', 'connect', 'adverb', 'ono', 'cond',
        'pattern1', 'pattern2', 'yomi', 'nita']
    asks = {s['stage']: s.get('ask') for s in CATALOG['skills']}
    assert asks['yomi'] == 'reading' and asks['nita'] == 'kanji' and asks['give'] is None


# ------------------------------------------------------------------ validator: kanji kinds
def test_a_reading_item_passes():
    assert validate.check_item(_item(), 'ym-n5-time', SKILLS) == []


@pytest.mark.parametrize('d, fragment', [
    (['けさ', 'いまあさ', 'こんちょう'], 'accepted answer'),
    (['今朝[こんあさ]', 'いまあさ', 'こんちょう'], 'reading in kana'),
])
def test_reading_distractors_are_wrong_readings_in_kana(d, fragment):
    errs = validate.check_item(_item(d=d), 'ym-n5-time', SKILLS)
    assert any(fragment in e for e in errs), errs


def test_a_reading_item_needs_a_kanji_word():
    errs = validate.check_item(_item(jp='{けさ|ym-n5-time}は早[はや]く起[お]きました。'), 'ym-n5-time', SKILLS)
    assert any('written with kanji' in e for e in errs), errs


def _kanji_item(**over):
    item = {'jp': '駅[えき]の前[まえ]で友達[ともだち]を{待[ま]って|nt-n5}います。', 'en': 'I am waiting for a friend in front of the station.',
            'f': 0, 'd': ['持[ま]って', '特[ま]って', '侍[ま]って'],
            'why': 'Waiting is written with the person-side radical.', 'lv': 5}
    item.update(over)
    return item


def test_a_look_alike_item_passes_with_distractors_that_share_the_reading():
    assert validate.check_item(_kanji_item(), 'nt-n5', SKILLS) == []


@pytest.mark.parametrize('d, fragment', [
    (['持[も]って', '特[ま]って', '侍[ま]って'], "answer's reading"),
    (['まって', '特[ま]って', '侍[ま]って'], 'written with kanji'),
    (['待[ま]って', '特[ま]って', '侍[ま]って'], 'accepted answer'),
])
def test_look_alike_distractors_differ_only_in_writing(d, fragment):
    errs = validate.check_item(_kanji_item(d=d), 'nt-n5', SKILLS)
    assert any(fragment in e for e in errs), errs


def test_katakana_list_is_checked(tmp_path):
    d = tmp_path / 'reading'
    d.mkdir()
    path = d / 'katakana.json'
    path.write_text(json.dumps([{'k': 'コーヒー', 'en': 'coffee', 'lv': 5},
                                {'k': 'コーヒー', 'en': 'coffee', 'lv': 5},
                                {'k': 'てれび', 'en': 'television', 'lv': 5},
                                {'k': 'パン', 'en': '', 'lv': 9}]), encoding='utf-8')
    errs, n = validate.check_katakana_file(str(path))
    assert n == 4
    text = ' '.join(errs)
    assert 'duplicate' in text and 'katakana' in text and 'en missing' in text and 'lv must be' in text


# ------------------------------------------------------------------ service and routes
def test_the_course_selects_the_content():
    content_mod.reset_cache()
    particles = content_mod.get_content(3)
    grammar = content_mod.get_content(3, 'grammar')
    assert particles is content_mod.get_content(3, 'particles')
    assert 'wa-topic' in particles.skills and 'gv-ageru' in grammar.skills
    assert 'wa-topic' not in grammar.skills
    assert content_mod.get_content(3, 'nope') is None
    assert content_mod.get_content(1, 'grammar') is None
    rows = {s['id']: s for s in grammar.catalog_payload()['skills']}
    assert rows['ym-jukuji']['ask'] == 'reading' and 'ask' not in rows['gv-ageru']
    assert grammar.skill_payload('nt-n5')['skill']['ask'] == 'kanji'


def _json(resp):
    return json.loads(resp.data)


def test_course_routes(client, auth_headers):
    resp = client.get('/api/particle-drill/catalog?language_id=3&course=grammar', headers=auth_headers)
    assert resp.status_code == 200
    body = _json(resp)
    assert body['stages'][0]['id'] == 'give' and len(body['skills']) == len(SKILLS)
    assert client.get('/api/particle-drill/catalog?language_id=3&course=nope',
                      headers=auth_headers).status_code == 400
    skill = client.get('/api/particle-drill/skill/gv-ageru?language_id=3&course=grammar', headers=auth_headers)
    assert skill.status_code == 200 and _json(skill)['skill']['id'] == 'gv-ageru'
    # a grammar skill is not in the particle course, and the reverse
    assert client.get('/api/particle-drill/skill/gv-ageru?language_id=3', headers=auth_headers).status_code == 404
    assert client.get('/api/particle-drill/skill/wa-topic?language_id=3&course=grammar',
                      headers=auth_headers).status_code == 404


def test_reading_route(client, auth_headers):
    assert client.get('/api/particle-drill/reading?language_id=3').status_code == 401
    assert client.get('/api/particle-drill/reading?language_id=1', headers=auth_headers).status_code == 400
    resp = client.get('/api/particle-drill/reading?language_id=3', headers=auth_headers)
    assert resp.status_code == 200
    words = _json(resp)['katakana']
    assert len(words) >= 450 and all(w['k'] and w['en'] for w in words)


# ------------------------------------------------------------------ shipped content
def test_shipped_content_validates():
    errors = build.validation_errors(GROOT)
    assert errors == [], errors[:10]


def test_manifest_is_current():
    with open(os.path.join(GROOT, 'manifest.json'), encoding='utf-8') as fh:
        manifest = json.load(fh)
    assert manifest == build.build_manifest(GROOT), \
        'content changed: run PD_COURSE=ja-grammar python scripts/particle_drill_build.py --apply'


def test_every_skill_has_exercises_and_a_guide():
    content = content_mod.Content(GROOT)
    short = {sid: len(content.items(sid)) for sid, s in content.skills.items()
             if len(content.items(sid)) < s['n']}
    assert not short, f'skills under their target: {short}'
    assert sum(len(content.items(sid)) for sid in content.skills) >= 8000
    missing = [sid for sid in content.skills if not content.skill_guide(sid)]
    assert not missing, missing


def test_sets_rotate_their_answers():
    """A skill that covers a set of words must not have one answer in every line."""
    content = content_mod.Content(GROOT)
    from services.particle_drill import markup
    stuck = []
    for sid in ('x-give', 'x-cond', 'x-connect', 'cn-shikashi', 'ko-kore', 'tr-aku', 'on-feel'):
        answers = set()
        for it in content.items(sid):
            _, slots, _ = markup.parse(it['jp'])
            answers.add(slots[it['f']]['a'])
        if len(answers) < 3:
            stuck.append((sid, sorted(answers)))
    assert not stuck, stuck


def test_every_authored_batch_has_a_review_record():
    reviewed = set()
    review_dir = os.path.join(GROOT, 'review')
    for name in os.listdir(review_dir):
        with open(os.path.join(review_dir, name), encoding='utf-8') as fh:
            reviewed.update(json.load(fh).get('files') or [])
    reviewed = {os.path.basename(f) for f in reviewed}
    unreviewed = [os.path.relpath(p, GROOT) for p in build.content_files(GROOT)[1:]
                  if os.path.basename(p) not in reviewed]
    assert not unreviewed, unreviewed[:20]
