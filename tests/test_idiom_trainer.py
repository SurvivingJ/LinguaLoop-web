"""Idiom trainer: the content contract (scripts/idiom_trainer.py), the built
static files, the pages and the tracking topics (idiom-<id>)."""
import copy
import json
import os
import sys
from datetime import datetime, timezone

import pytest

pytest.importorskip('pypinyin')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import idiom_trainer as it  # noqa: E402
import idiom_trainer_swarm as swarm  # noqa: E402
from services import grammar_drill_tracking as tracking  # noqa: E402

ENTRY = {'id': 'cy001', 't': '画蛇添足', 'r': 'huà shé tiān zú',
         'mean': 'to ruin something by adding what is not needed', 'lvl': 2, 'tag': 'foolishness'}
CARD = dict(
    ENTRY,
    lit='to draw a snake and add feet',
    story={'text': 'Servants in the state of Chu were given one jug of wine, too little to share, so they agreed '
                   'that whoever drew a snake first would drink it. One man finished early and added feet.',
           'source': '《战国策·齐策二》'},
    use={'reg': 'neutral', 'tone': 'criticism', 'how': 'Used as a predicate or after 是: 这样做是画蛇添足。'},
    near=[{'t': '多此一举', 'diff': '多此一举 is any unnecessary extra step; this one makes the result worse.'}],
    parts=['画蛇', '添足'],
    cue="A colleague's report was clear, then he added three more pages that confused everyone. What did he do?",
    ctx=[{'s': '这篇文章已经很完整了，再加一段解释就是{画蛇添足}' + '了' * i + '。',
          'en': 'The essay is already complete; adding more would spoil it.'} for i in range(6)],
    bad=[{'s': '他工作很努力，' + w + '都{画蛇添足}。', 'en': '(meant: he works hard)',
          'why': 'It criticises one unnecessary addition; it is not praise.'} for w in ('每天', '天天')],
)


def _card_errors(change, lang='zh', key='chengyu', entry=ENTRY):
    card = copy.deepcopy(CARD)
    change(card)
    errs = []
    it.check_card(card, lang, key, entry, errs)
    return errs


def test_a_good_entry_and_card_pass():
    errs = []
    assert it.check_list_entry(dict(ENTRY), 'zh', 'cy', errs) and errs == []
    assert _card_errors(lambda c: None) == []
    assert _card_errors(lambda c: c.update(story=None)) == []      # no story is fine


@pytest.mark.parametrize('change, fragment', [
    (lambda e: e.update(id='ky001'), 'id must be cy'),
    (lambda e: e.update(r='huà shé tiān'), 'syllable'),
    (lambda e: e.update(t='画蛇添足abc'), 'simplified characters'),
    (lambda e: e.update(mean='画蛇添足'), 'mean must be English'),
    (lambda e: e.update(lvl=4), 'lvl must be'),
    (lambda e: e.update(tag='snakes'), 'tag is not'),
])
def test_bad_list_entries(change, fragment):
    entry = dict(ENTRY)
    change(entry)
    errs = []
    it.check_list_entry(entry, 'zh', 'cy', errs)
    assert any(fragment in e for e in errs), errs


@pytest.mark.parametrize('change, fragment', [
    (lambda c: c.update(mean='something else'), 'mean differs from the list'),
    (lambda c: c['story'].update(text='Too short.'), 'story.text'),
    (lambda c: c.update(story={'text': 'x' * 100}), 'story must be null or'),
    (lambda c: c['use'].update(reg='slang'), 'use.reg'),
    (lambda c: c['use'].update(tone='rude'), 'use.tone'),
    (lambda c: c.update(parts=['画蛇', '添']), 'parts must be two pieces'),
    (lambda c: c.update(cue='He wanted to ruin something by adding what is not needed, clearly.'), 'meaning line'),
    (lambda c: c['ctx'].pop(), 'exactly 6 contexts'),
    (lambda c: c['ctx'][0].update(s='这篇文章已经很完整了，再加一段就多余了。'), 'once, in braces'),
    (lambda c: c['ctx'][0].update(s='这篇文章已经很完整了，再加一段就是{画蛇添脚}。'), 'unchanged'),
    (lambda c: c['ctx'][1].update(s=c['ctx'][0]['s']), 'repeats a context'),
    (lambda c: c['ctx'][2].update(s='OK，这样就是{画蛇添足}了。'), 'simplified characters and full-width'),
    (lambda c: c['bad'].pop(), 'exactly 2 misuses'),
    (lambda c: c['bad'][0].update(why='no'), 'bad[0].why'),
    (lambda c: c['near'].append({'t': '画蛇添足', 'diff': 'the same idiom listed as its own look-alike'}), 'itself'),
    (lambda c: c.update(extra=1), 'unknown fields'),
])
def test_bad_cards(change, fragment):
    errs = _card_errors(change)
    assert any(fragment in e for e in errs), errs


def test_colloquial_expressions_may_be_split_and_japanese_needs_furigana():
    errs = []
    it.check_sentence('老板昨天{炒了他的鱿鱼}，他很难过。', 'zh', 'guanyong', '炒鱿鱼', 'ctx', errs)
    assert errs == []
    it.check_sentence('老板昨天{开除}了他，他很难过。', 'zh', 'guanyong', '炒鱿鱼', 'ctx', errs)
    assert any('first to the last character' in e for e in errs)
    errs = []
    it.check_sentence('弟[おとうと]の態度[たいど]に{腹[はら]が立[た]って}、部屋[へや]を出[で]た。',
                      'ja', 'kanyo', '腹が立つ', 'ctx', errs)
    assert errs == []
    it.check_sentence('弟の態度に{腹が立って}、部屋を出た。', 'ja', 'kanyo', '腹が立つ', 'ctx', errs)
    assert any('furigana' in e for e in errs)
    errs = []
    it.check_sentence('これは{一石二鳥[いっせきにちょう]}の方法[ほうほう]だと思[おも]います。', 'ja', 'yoji', '一石二鳥', 'ctx', errs)
    assert errs == []


def test_paths_and_sets():
    assert it.where_of(os.path.join(it.DATA, 'zh', 'lists', 'chengyu.json')) == ('zh', 'lists', 'chengyu', None)
    assert it.where_of(os.path.join(it.DATA, 'ja', 'cards', 'kanyo-07.json')) == ('ja', 'cards', 'kanyo', 7)
    assert it.where_of(os.path.join(it.DATA, 'ja', 'cards', 'chengyu-01.json')) is None   # a Chinese set
    assert it.where_of(os.path.join(it.DATA, 'zh', 'lists', 'nope.json')) is None
    assert sum(r[4] for r in it.SETS['zh']) == 320 and sum(r[4] for r in it.SETS['ja']) == 330
    assert sum(n for (lang, _k), n in it.FULL.items() if lang == 'zh') == 850
    assert sum(n for (lang, _k), n in it.FULL.items() if lang == 'ja') == 770
    codes = [r[1] for rows in it.SETS.values() for r in rows]
    assert len(set(codes)) == len(codes)


# ------------------------------------------------------------------ shipped content
def _all(kind):
    out = []
    for lang in it.SETS:
        base = os.path.join(it.DATA, lang, kind)
        out += sorted(os.path.join(base, n) for n in os.listdir(base) if n.endswith('.json'))
    return out


def test_shipped_lists_and_cards_validate():
    for path in _all('lists'):
        lang, _kind, key, _ = it.where_of(path)
        floor = int(it.set_info(lang, key)[4] * swarm.LIST_FLOOR)
        assert it.validate_file(path, floor) == [], path
    for path in _all('cards'):
        assert it.validate_file(path) == [], path


def test_every_listed_idiom_has_a_card_and_a_review():
    for lang, sets in it.SETS.items():
        for key, _code, _title, _en, core in sets:
            entries = it.load_list(lang, key)
            assert len(entries) >= int(it.FULL[(lang, key)] * swarm.LIST_FLOOR), (lang, key, len(entries))
            carded = set()
            for path in it.card_files(lang, key):
                carded.update(c['id'] for c in it.load_json(path))
            assert carded == {e['id'] for e in entries}, (lang, key)
    assert swarm.pending(swarm.jobs()) == {}


def test_static_files_are_built_and_idioms_are_unique():
    for lang in it.SETS:
        files, skipped = it.built_files(lang)
        assert skipped == 0
        for name, body in files.items():
            with open(os.path.join(it.STATIC, lang, name), encoding='utf-8') as fh:
                assert fh.read() == body, f'run python scripts/idiom_trainer.py build ({lang}/{name})'
        manifest = json.loads(files['manifest.json'])
        ids = [i['id'] for i in manifest['idioms']]
        texts = [i['t'] for i in manifest['idioms']]
        assert len(set(ids)) == len(ids) and len(set(texts)) == len(texts)
        assert manifest['total'] == len(ids) >= 750
        # an expression that two sets list (半斤八两; 背水の陣) is built once, in the earlier set
        listed = [e['t'] for key, *_ in it.SETS[lang] for e in it.load_list(lang, key)]
        assert len(ids) == len(set(listed)) and 0 <= len(listed) - len(ids) <= 5
        assert manifest['language_id'] == it.LANGUAGE_IDS[lang]
        # the "complete" step needs every idiom's two halves in the manifest
        assert all(''.join(i['parts']) == i['t'] for i in manifest['idioms'])


def test_stories_are_marked_and_sourced():
    """A story always names its source; the sets with classical origins have many."""
    with_story = {}
    for lang, sets in it.SETS.items():
        for key, *_ in sets:
            cards = [c for p in it.card_files(lang, key) for c in it.load_json(p)]
            stories = [c for c in cards if c['story']]
            assert all(c['story']['source'].strip() for c in stories)
            with_story[key] = len(stories) / max(1, len(cards))
    # a core list is mostly everyday descriptive idioms; the fable-born ones are a minority
    assert with_story['chengyu'] > 0.15
    assert with_story['kanyo'] < with_story['chengyu']     # body-part idioms mostly have none


# ------------------------------------------------------------------ pages and tracking
def test_pages(client):
    for path in ('/idiom-trainer/zh', '/idiom-trainer/ja'):
        resp = client.get(path)
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        lang = path[-2:]
        assert f'data-lang="{lang}"' in html and f'data/idioms/{lang}/manifest.json' in html
        assert f'data-language-id="{it.LANGUAGE_IDS[lang]}"' in html
    chooser = client.get('/idiom-trainer').get_data(as_text=True)
    assert 'data-base="/idiom-trainer"' in chooser and '/idiom-trainer/zh' in chooser and '/idiom-trainer/ja' in chooser


NOW = datetime(2026, 11, 28, 3, 0, tzinfo=timezone.utc)
STAMP = int(NOW.timestamp())


def _round(language_id, topic, **over):
    state = {'u': 3, 'l': STAMP, 's': {'l': 3, 'k': 1, 'n': 5, 'c': 4, 'due': None, 'iv': 0, 'last': STAMP * 1000}}
    entry = {'topic': topic, 'answers': 4, 'correct': 3, 'timed': 3, 'ms_sum': 9000, 'stage': 3,
             'instant': False, 'sub_misses': {}, 'state': state}
    entry.update(over)
    return {'language_id': language_id, 'round_key': '44444444-4444-4444-8444-444444444444',
            'mode': 'round', 'played_at': STAMP, 'topics': [entry]}


def test_idioms_are_tracking_topics_of_their_own_language():
    tracking.reset()
    zh = sorted(tracking.idiom_ids(1))[0]
    ja = sorted(tracking.idiom_ids(3))[0]
    assert tracking.profile_for(1).topic(f'idiom-{zh}') == (frozenset(), 6)
    assert tracking.profile_for(3).topic(f'idiom-{ja}') == (frozenset(), 6)
    assert tracking.profile_for(1).topic(f'idiom-{ja}') is None
    assert tracking.profile_for(3).topic('idiom-nope') is None
    for language_id, idiom in ((1, zh), (3, ja)):
        got = tracking.validate_round(_round(language_id, f'idiom-{idiom}'), NOW)
        assert got['topics'][0]['state']['s']['k'] == 1 and got['language_id'] == language_id
    mastered = _round(1, f'idiom-{zh}', stage=6, instant=True)
    mastered['topics'][0]['state'] = {'u': 6, 'l': STAMP, 's': {'l': 6, 'n': 10, 'c': 10}}
    assert tracking.validate_round(mastered, NOW)['topics'][0]['instant'] is True
    with pytest.raises(tracking.ValidationError, match='stage'):
        tracking.validate_round(_round(1, f'idiom-{zh}', stage=7), NOW)
    bad = _round(3, f'idiom-{ja}')
    bad['topics'][0]['state']['s']['miss'] = []          # a particle-ladder field
    with pytest.raises(tracking.ValidationError, match='unknown fields'):
        tracking.validate_round(bad, NOW)
    tracking.reset()
