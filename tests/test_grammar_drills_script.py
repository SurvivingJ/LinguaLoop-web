"""scripts/grammar_drills.py: item and guide validation, blind compare, build."""

import importlib.util
import json
import os

import pytest

pytest.importorskip('pypinyin')
pytest.importorskip('opencc')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    'grammar_drills', os.path.join(ROOT, 'scripts', 'grammar_drills.py'))
gd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gd)

import sys  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, 'scripts'))   # for grammar_drills_swarm (imported in tests below)

SUBS = ['x']


def cloze(**over):
    item = {
        'id': 'le-01-001', 'type': 'cloze', 'sub': 'x', 'lvl': 1,
        'q': '我昨天买___三本书。', 'opts': ['了', '过', '着', '的'], 'a': 0,
        'zh': '我昨天买了三本书。', 'py': 'wǒ zuó tiān mǎi le sān běn shū',
        'en': 'I bought three books yesterday.',
        'why': 'A finished action with a counted object takes 了 after the verb.',
    }
    item.update(over)
    return item


def order(**over):
    item = {
        'id': 'le-01-002', 'type': 'order', 'sub': 'x', 'lvl': 1,
        'tokens': ['我', '明天', '在家', '看', '电影'],
        'alts': [['明天', '我', '在家', '看', '电影']],
        'zh': '我明天在家看电影。', 'py': 'wǒ míng tiān zài jiā kàn diàn yǐng',
        'en': "I'm watching a film at home tomorrow.",
        'why': 'Time, then place, then the verb phrase.',
    }
    item.update(over)
    return item


def judge(**over):
    item = {
        'id': 'le-01-004', 'type': 'judge', 'sub': 'x', 'lvl': 1,
        's': '我不有哥哥。', 's_py': 'wǒ bù yǒu gē ge', 'ok': False,
        'zh': '我没有哥哥。', 'py': 'wǒ méi yǒu gē ge',
        'en': "I don't have an older brother.",
        'why': '有 is only ever negated with 没.',
    }
    item.update(over)
    return item


def errors(item):
    return gd.validate_item(item, SUBS, 'le')


def test_spec_examples_are_valid():
    assert errors(cloze()) == []
    assert errors(order()) == []
    assert errors(judge()) == []
    rewrite = order(
        id='le-01-003', type='rewrite', src='我喝完了那杯咖啡。',
        src_py='wǒ hē wán le nà bēi kā fēi', task='Rewrite with 把.',
        tokens=['我', '把', '那杯咖啡', '喝完', '了'], alts=[],
        zh='我把那杯咖啡喝完了。', py='wǒ bǎ nà bēi kā fēi hē wán le')
    assert errors(rewrite) == []


def test_two_blanks_and_empty_option():
    two = cloze(q='___下雨，___我们没去。', opts=['因为|所以', '虽然|但是'], a=0,
                zh='因为下雨，所以我们没去。', py='yīn wèi xià yǔ suǒ yǐ wǒ men méi qù')
    assert errors(two) == []
    nothing = cloze(q='我每天喝___咖啡。', opts=['了', '∅'], a=1, zh='我每天喝咖啡。',
                    py='wǒ měi tiān hē kā fēi')
    assert errors(nothing) == []


@pytest.mark.parametrize('change, needle', [
    ({'zh': '我昨天买过三本书。'}, 'must equal q'),
    ({'a': 4}, 'index of the correct option'),
    ({'opts': ['了', '了']}, 'duplicates'),
    ({'py': 'wǒ zuó tiān mǎi le sān běn'}, 'syllables'),
    ({'py': 'wǒ zuó tiān mǎi le sān běn shù'}, 'not a reading'),
    ({'sub': 'nope'}, 'not a sub-point'),
    ({'lvl': 4}, 'lvl'),
    ({'why': 'short'}, 'why'),
    ({'q': '我昨天买___3本书。', 'zh': '我昨天买了3本书。'}, 'digits'),
    ({'q': '我昨天買___三本書。', 'zh': '我昨天買了三本書。'}, 'traditional'),
    ({'bogus': 1}, 'unknown fields'),
])
def test_cloze_defects_are_reported(change, needle):
    assert any(needle in e for e in errors(cloze(**change)))


def test_pinyin_accepts_neutral_tone_erhua_and_tone_change():
    errs = []
    gd.check_py('我买了一点儿东西，不去。', 'wǒ mǎi le yì diǎn r dōng xi bú qù', 'py', errs)
    assert errs == []


def test_order_defects_are_reported():
    assert any('joined' in e for e in errors(order(tokens=['我', '明天', '看', '电影'], alts=[])))
    assert any('reordering' in e for e in errors(order(alts=[['我', '明天']])))
    assert any('repeats' in e for e in errors(order(alts=[['我', '明天', '在家', '看', '电影']])))


def test_judge_defects_are_reported():
    assert any('must differ' in e for e in errors(judge(s='我没有哥哥。', s_py='wǒ méi yǒu gē ge')))
    assert any('must equal zh' in e for e in errors(judge(ok=True)))


def test_compare_flags_ambiguity_and_wrong_key(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gd, 'DATA', str(tmp_path))
    batch = tmp_path / 'le-01.jsonl'
    items = [cloze(), cloze(id='le-01-005', q='他去___北京。', zh='他去了北京。',
                            py='tā qù le běi jīng'), order(), judge()]
    batch.write_text('\n'.join(json.dumps(i, ensure_ascii=False) for i in items), encoding='utf-8')
    assert gd.cmd_strip(str(batch)) == 0
    blind = (tmp_path / 'blind' / 'le-01.blind.jsonl').read_text(encoding='utf-8')
    assert '"a"' not in blind and 'why' not in blind and '没有哥哥' not in blind
    answers = [
        {'id': 'le-01-001', 'ok': [0]},
        {'id': 'le-01-005', 'ok': [0, 1]},
        {'id': 'le-01-002', 'zh': '明天我在家看电影。'},
        {'id': 'le-01-004', 'ok': True},
    ]
    (tmp_path / 'blind' / 'le-01.answers.jsonl').write_text(
        '\n'.join(json.dumps(a, ensure_ascii=False) for a in answers), encoding='utf-8')
    capsys.readouterr()
    assert gd.cmd_compare(str(batch)) == 0
    out = capsys.readouterr().out
    assert '4 items, 2 flagged' in out
    assert 'le-01-005: AMBIGUOUS' in out and 'le-01-004: JUDGEMENT DIFFERS' in out


def test_plan_batches_and_mixes():
    plan = gd.load_plan()
    # 105 in the first build; 10 more for the four topics added on 2026-11-28
    assert sum(t['batches'] for t in plan['topics'] if not t.get('added')) == 105
    assert sum(t['batches'] for t in plan['topics']) == 115
    added = {t['slug'] for t in plan['topics'] if t.get('added')}
    assert added == {'near-synonyms', 'collocations', 'look-alike-characters', 'chengyu', 'polyphones'}
    cats = {c['key'] for c in plan['categories']}
    slugs = [t['slug'] for t in plan['topics']]
    assert len(set(slugs)) == len(slugs)
    for t in plan['topics']:
        assert t['cat'] in cats
        assert sum(t['mix'].values()) == 100, t['slug']


def test_shipped_content_is_valid_and_built():
    """Every reviewed batch and guide in the repository passes validation and
    the static files match what a build would write."""
    plan = gd.load_plan()
    guides = os.path.join(gd.DATA, 'guides')
    for name in sorted(os.listdir(guides)) if os.path.isdir(guides) else []:
        if name.endswith('.json'):
            _, problems = gd.validate_guide(os.path.join(guides, name), plan, quiet=True)
            assert problems == [], (name, problems[:3])
    for path in gd.source_files(plan):
        slug, _ = gd.batch_topic(path, plan)
        subs = [s['key'] for s in gd.load_guide(slug)['subs']]
        for n, obj, err in gd.read_jsonl(path):
            assert err is None, (path, n, err)
            assert gd.validate_item(obj, subs, slug) == [], (path, n)
    if gd.source_files(plan):
        assert gd.cmd_build(check_only=True) == 0


# ------------------------------------------------- topics added 2026-11-28 and their runner
def test_free_levels_topic_skips_the_level_mix_only():
    """chengyu has no HSK 1-2 items: its plan entry opts out of the level check."""
    plan = gd.load_plan()
    assert gd.topic_of(plan, 'chengyu').get('free_levels') is True
    assert not any(t.get('free_levels') for t in plan['topics'] if t['slug'] != 'chengyu')
    path = os.path.join(gd.DATA, 'reviewed', 'chengyu-01.jsonl')
    _, problems = gd.validate_file(path, plan, quiet=True, min_items=90)
    assert problems == []


def test_polyphone_table_is_checked_and_built():
    import grammar_drills_swarm as swarm
    assert swarm.check_words() == []
    with open(swarm.WORDS, encoding='utf-8') as fh:
        rows = json.load(fh)
    assert len(rows) >= swarm.MIN_WORDS
    # every listed reading, right and wrong, is a real reading of the character
    for r in rows:
        ch = r['w'][r['i']]
        known = gd.readings(ch)
        assert r['py'].split(' ')[r['i']] in known and set(r['wrong']) <= known, r['w']
    # the generator's data file is what build-words writes
    _, body = swarm.words_js()
    assert open(swarm.WORDS_JS, encoding='utf-8').read() == body, \
        'run python scripts/grammar_drills_swarm.py build-words --apply'
    assert body.count('\n  ["') == len(rows)


@pytest.mark.parametrize('change, fragment', [
    (lambda r: r.update(py='yin hang'), 'not a reading'),
    (lambda r: r.update(wrong=['háng']), 'right reading is among'),
    (lambda r: r.update(wrong=['bàng']), 'is not a reading of'),
    (lambda r: r.update(w='行', py='háng', i=0), '2 to 6'),
    (lambda r: r.update(i=5), 'must index'),
    (lambda r: r.update(why='short'), 'why must be'),
    (lambda r: r.pop('lvl'), 'needs exactly'),
])
def test_polyphone_checker_rejects(tmp_path, change, fragment):
    import grammar_drills_swarm as swarm
    row = {'w': '银行', 'py': 'yín háng', 'i': 1, 'wrong': ['xíng'], 'en': 'bank',
           'why': 'A firm or a line of business is read with the other sound.', 'lvl': 1}
    change(row)
    path = tmp_path / 'p.json'
    path.write_text(json.dumps([row], ensure_ascii=False), encoding='utf-8')
    errs = swarm.check_words(str(path))
    assert any(fragment in e for e in errs), errs


def test_the_runner_only_plans_added_topics_and_every_new_file_has_a_verdict():
    import grammar_drills_swarm as swarm
    all_jobs = swarm.jobs()
    assert {v['slug'] for v in all_jobs.values() if v['kind'] == 'batch'} == \
        {'near-synonyms', 'collocations', 'look-alike-characters', 'chengyu'}
    assert 'words-polyphones' in all_jobs
    assert swarm.pending(all_jobs) == {}
    for jid in all_jobs:
        name = jid[len('batch-'):] if jid.startswith('batch-') else jid
        assert os.path.exists(swarm.verdict(name)), jid
