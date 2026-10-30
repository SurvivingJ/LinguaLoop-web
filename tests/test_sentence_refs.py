"""Sentence references (services/dual_translation/sentence_refs.py, TASK-902/903).

Offline: no database, no model. Run: PYTHONPATH=. python -m pytest tests/test_sentence_refs.py -q
"""
import json
import os
import subprocess
import sys

import pytest

from services.dual_translation import sentence_refs as sr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, 'data', 'fixtures', 'sentence_refs', 'demo_tests.json')


@pytest.fixture(scope='module')
def fixture():
    with open(FIX, encoding='utf-8') as fh:
        return json.load(fh)


def test_regexes_match_passage_builder():
    pb = pytest.importorskip('services.dual_translation.passage_builder')
    assert pb._CJK_SENTENCE_RE.pattern == sr._CJK_SENTENCE_RE.pattern
    assert pb._LATIN_SENTENCE_RE.pattern == sr._LATIN_SENTENCE_RE.pattern
    assert pb._CJK_CODES == sr._CJK_CODES


def test_spans_reproduce_transcript_and_match_segmenter(fixture):
    for t in fixture['tests']:
        code = sr.LANG_CODE[t['language_id']]
        spans = sr.segment_with_spans(t['transcript'], code)
        assert spans, t['id']
        for sp in spans:
            assert t['transcript'][sp.char_start:sp.char_end] == sp.text
        assert [sp.text for sp in spans] == sr.segment_sentences(t['transcript'], code)
        for a, b in zip(spans, spans[1:]):
            assert a.char_end <= b.char_start


def test_token_spans_cover_sentences_exactly(fixture):
    for t in fixture['tests']:
        if not t['vocab_token_map']:
            continue
        code = sr.LANG_CODE[t['language_id']]
        spans = sr.segment_with_spans(t['transcript'], code)
        warnings = sr.attach_token_spans(spans, t['vocab_token_map'])
        assert warnings == [], (t['id'], warnings)
        for sp in spans:
            joined = ''.join(s for s, _ in t['vocab_token_map'][sp.token_start:sp.token_end])
            assert joined.strip() == sp.text


def test_token_straddling_boundary_with_whitespace_only_is_accepted():
    tm = [['Hi', 1], ['. ', 0], ['Bye', 2], ['.', 0]]
    spans = sr.segment_with_spans('Hi. Bye.', 'en')
    assert sr.attach_token_spans(spans, tm) == []
    assert [(s.token_start, s.token_end) for s in spans] == [(0, 2), (2, 4)]


def test_token_carrying_text_across_boundary_is_rejected():
    tm = [['Hi.B', 0], ['ye.', 0]]
    spans = sr.segment_with_spans('Hi. Bye.', 'en')  # spans [0,3) and [4,8)
    tm = [['Hi. B', 0], ['ye.', 0]]
    warnings = sr.attach_token_spans(spans, tm)
    assert len(warnings) == 2 and all(s.token_start is None for s in spans)


def test_no_token_map_gives_null_spans():
    spans = sr.segment_with_spans('一。二。', 'zh')
    assert sr.attach_token_spans(spans, None) == ['no token map']
    assert all(sp.token_start is None for sp in spans)


def test_preamble_detection():
    assert sr.has_preamble('この文章は、T3レベル（B1-B2）の学習者向けに解説します。')
    assert sr.has_preamble('本文介绍… --- 正文')
    assert sr.has_preamble('This passage explains…')
    assert not sr.has_preamble('T3の学習者が増えている。')


def test_script_leak_and_numbers():
    assert sr.leaked_script('handmade accessories (手作り)', 'ja') == ['り', '作', '手']
    assert sr.leaked_script('a long time ago', 'zh') == []
    assert sr.leaked_script('这是 Tokyo 的 catalogue', 'en') == ['Tokyo', 'catalogue']
    assert sr.missing_numbers('３個のりんごを買った。', 'He bought three apples.') == ['3']
    assert sr.missing_numbers('３個のりんごを買った。', 'He bought 3 apples.') == []


def test_tightness_cases():
    assert sr.tightness('很久以前，人们写字很慢。', '很久以前，人们写字很慢。', 'zh') == 1.0
    assert 0.5 < sr.tightness('很久以前人们写字非常慢', '很久以前，人们写字很慢。', 'zh') < 1.0
    assert sr.tightness('完全不同的句子', '很久以前，人们写字很慢。', 'zh') < 0.4
    assert sr.tightness('He bought three apples', 'He bought 3 apples!', 'en') == 0.75


def _canon(t):
    code = sr.LANG_CODE[t['language_id']]
    return [{'idx': sp.idx, 'l2_text': sp.text} for sp in sr.segment_with_spans(t['transcript'], code)]


def _doc(t, refs, arm='aligned', **over):
    d = {'test_id': t['id'], 'l2': sr.LANG_CODE[t['language_id']], 'l1': 'en', 'arm': arm, 'prompt_version': sr.PROMPT_VERSION,
         'sentences': [{'idx': c['idx'], 'l2': c['l2_text'], 'l1': refs[c['idx']]} for c in _canon(t)]}
    d.update(over)
    return d


def test_validate_doc_accepts_hand_written_references(fixture):
    for t in fixture['tests']:
        refs = fixture['l1_refs'].get(t['id'])
        if not refs:
            continue
        r = sr.validate_doc(_doc(t, refs), _canon(t), sr.LANG_CODE[t['language_id']])
        assert r.ok, (t['title'], r.failures)


def test_validate_doc_rejects_each_failure_class(fixture):
    t = next(x for x in fixture['tests'] if x['id'].startswith('8002d9fe'))
    refs = list(fixture['l1_refs'][t['id']])
    canon = _canon(t)
    bad = _doc(t, refs); bad['sentences'] = bad['sentences'][:-1]
    assert 'count_mismatch:7!=8' in sr.validate_doc(bad, canon, 'zh').failures
    bad = _doc(t, refs); bad['sentences'][0]['l1'] = 'A long time ago, 人们 wrote slowly.'
    assert any(f.startswith('l2_script_leak:0') for f in sr.validate_doc(bad, canon, 'zh').failures)
    bad = _doc(t, refs); bad['sentences'][0]['l1'] = 'This passage explains that people wrote slowly.'
    assert 'preamble:0' in sr.validate_doc(bad, canon, 'zh').failures
    bad = _doc(t, refs); bad['sentences'][1]['l1'] = refs[0]
    assert 'duplicate_sentence:1=0' in sr.validate_doc(bad, canon, 'zh').failures
    bad = _doc(t, refs); bad['sentences'][0]['l1'] = 'Slow.'
    assert any(f.startswith('length_ratio:0') for f in sr.validate_doc(bad, canon, 'zh').failures)
    bad = _doc(t, refs); bad['sentences'][0]['l2'] = 'changed'
    assert 'l2_changed:0' in sr.validate_doc(bad, canon, 'zh').failures
    bad = _doc(t, refs, arm='nope')
    assert 'arm_invalid:nope' in sr.validate_doc(bad, canon, 'zh').failures


def test_activation_plan():
    rows = [{'sentence_id': 1, 'l1_language_id': 2, 'review_verdict': 'pass'},
            {'sentence_id': 2, 'l1_language_id': 2, 'review_verdict': 'fail'},
            {'sentence_id': 3, 'l1_language_id': 2, 'review_verdict': 'rewritten'}]
    plan = sr.activation_plan(rows, {(1, 2): 99, (2, 2): 98})
    assert plan['activate'] == [(1, 2), (3, 2)]
    assert plan['deactivate'] == [99]


def test_offline_chain_export_brief_check_assemble(tmp_path, fixture):
    """export --fixture -> brief -> docs from the hand-written refs -> check -> review-pack
    -> back_translations (gold copied, so tightness = 1) -> verdicts -> tightness -> assemble."""
    run = str(tmp_path / 'run_00')
    py = [sys.executable, os.path.join(ROOT, 'scripts', 'sentence_ref_runner.py')]
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONIOENCODING='utf-8')
    def r(*args, ok=True):
        p = subprocess.run(py + list(args), capture_output=True, text=True, env=env, cwd=ROOT)
        assert (p.returncode == 0) == ok, p.stdout + p.stderr
        return p.stdout + p.stderr
    r('export', '--language', 'zh', '--l1', 'en', '--limit', '5', '--arm', 'aligned', '--out-dir', run, '--fixture', FIX)
    wl = json.load(open(os.path.join(run, 'sentence_refs', 'worklist.json'), encoding='utf-8'))
    assert len(wl['tests']) == 2  # the two zh demo tests
    r('brief', run, '--width', '1')
    assert len(os.listdir(os.path.join(run, 'sentence_refs', 'briefs'))) == 2
    r('check', run, ok=False)  # nothing authored yet
    os.makedirs(os.path.join(run, 'sentence_refs', 'docs'))
    for t in wl['tests']:
        refs = fixture['l1_refs'][t['test_id']]
        doc = {'test_id': t['test_id'], 'l2': 'zh', 'l1': 'en', 'arm': 'aligned', 'prompt_version': sr.PROMPT_VERSION, 'author_model': 'test',
               'sentences': [{'idx': s['idx'], 'l2': s['l2_text'], 'l1': refs[s['idx']]} for s in t['sentences']], 'author_notes': 'n/a'}
        sr.dump_json(os.path.join(run, 'sentence_refs', 'docs', f'{t["test_id"]}.en.json'), doc)
    out = r('check', run)
    assert '2 ok, 0 failed' in out
    r('review-pack', run)
    pack = open(os.path.join(run, 'sentence_refs', 'review_packs', 'review_01.md'), encoding='utf-8').read()
    gold = open(os.path.join(run, 'sentence_refs', 'review_packs', 'review_01.gold.md'), encoding='utf-8').read()
    assert 'BLIND HALF' in pack and 'gold:' not in pack and 'n/a' not in pack
    assert 'gold:' in gold and '很久以前' in gold
    for sub in ('back_translations', 'reviewed', 'verdicts'):
        os.makedirs(os.path.join(run, 'sentence_refs', sub), exist_ok=True)
    for t in wl['tests']:
        key = f'{t["test_id"]}.en'
        sr.dump_json(os.path.join(run, 'sentence_refs', 'back_translations', key + '.json'),
                     {'test_id': t['test_id'], 'l1': 'en', 'sentences': [{'idx': s['idx'], 'back': s['l2_text']} for s in t['sentences']]})
        doc = sr.load_json(os.path.join(run, 'sentence_refs', 'docs', key + '.json'))
        sr.dump_json(os.path.join(run, 'sentence_refs', 'reviewed', key + '.json'), sr.strip_author_notes(doc) | {'arm': 'aligned', 'prompt_version': sr.PROMPT_VERSION, 'test_id': t['test_id'], 'l2': 'zh', 'l1': 'en'})
        sr.dump_json(os.path.join(run, 'sentence_refs', 'verdicts', key + '.json'),
                     {'test_id': t['test_id'], 'l1': 'en', 'reviewer_model': 'test', 'sentences': [{'idx': s['idx'], 'verdict': 'pass', 'entailment_ok': True, 'changed': False, 'notes': ''} for s in t['sentences']]})
    r('tightness', run)
    v = sr.load_json(os.path.join(run, 'sentence_refs', 'verdicts', f'{wl["tests"][0]["test_id"]}.en.json'))
    assert all(s['tightness'] == 1.0 for s in v['sentences'])
    out = r('assemble', run)
    up = sr.load_json(os.path.join(run, 'sentence_refs', 'upload.json'))
    assert len(up['rows']) == sum(len(t['sentences']) for t in wl['tests']) and '0 problems' in out
    assert up['rows'][0]['review_verdict'] == 'pass' and up['rows'][0]['run_id'] == 'run_00'
    out = r('status', run)
    assert out.count('yes') >= 2 * 5


def test_build_script_fixture_mode(tmp_path):
    out = str(tmp_path / 'spans.json')
    p = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'build_test_sentences.py'), '--fixture', FIX, '--out', out],
                       capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=ROOT), cwd=ROOT)
    assert p.returncode == 0, p.stdout + p.stderr
    spans = json.load(open(out, encoding='utf-8'))
    assert sum(len(v) for v in spans.values()) >= 23 + 2 + 3
    pre = spans['00000000-0000-0000-0000-00000000pre1']
    assert pre[0]['l2_text'].startswith('この文章は')  # cleanup is TASK-900's job, segmentation stays faithful
    assert 'under 2 sentences' in p.stderr + p.stdout
