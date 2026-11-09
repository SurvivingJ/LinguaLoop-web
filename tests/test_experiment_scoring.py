"""Experiment harness scoring on a synthetic two-arm fixture (TASK-923)."""

import json

import scripts.build_experiment_review_packs as packs
import scripts.score_experiment as se


def _test(tid, answer2):
    return {'id': tid, 'slug': tid, 'title': 't', 'language_code': 'en', 'target_age_tier': 3,
            'transcript': 'The cat sleeps on the warm mat every day.',
            'questions': [
                {'question_id': f'{tid}-q1', 'type_code': 'literal_detail', 'question_text': 'Where?',
                 'choices': ['mat', 'bed', 'box', 'car'], 'answer': 'mat'},
                {'question_id': f'{tid}-q2', 'type_code': 'literal_detail', 'question_text': 'When?',
                 'choices': ['every day', 'at night', 'never', 'mat'], 'answer': answer2}]}


def test_two_arm_score(tmp_path, monkeypatch):
    monkeypatch.setattr(packs, 'ROOT', str(tmp_path))
    for tag, rows in {
        'armA': [{'outcome': 'pass', 'test_id': 'a1'}, {'outcome': 'error', 'error': 'Too few valid questions: 1/4'}],
        'armB': [{'outcome': 'pass', 'test_id': 'b1'}, {'outcome': 'pass', 'test_id': 'b2'}],
    }.items():
        d = tmp_path / 'data' / 'test_quality' / 'experiments' / tag
        d.mkdir(parents=True)
        (d / 'tests.jsonl').write_text('\n'.join(json.dumps(dict(r, run_tag=tag, language='en')) for r in rows))
    recs = packs.load_records(['armA', 'armB'])
    tests = [_test('a1', 'mat'), _test('b1', 'every day'), _test('b2', 'every day')]
    reviews = [
        {'test_id': 'a1', 'question_id': 'a1-q1', 'verdict': 'ok', 'level_fit': 'ok'},
        {'test_id': 'a1', 'question_id': 'a1-q2', 'verdict': 'minor', 'level_fit': 'ok'},
        {'test_id': 'b1', 'question_id': 'b1-q1', 'verdict': 'ok', 'level_fit': 'ok'},
        {'test_id': 'b1', 'question_id': 'b1-q2', 'verdict': 'ok', 'level_fit': 'too_hard'},
        {'test_id': 'b2', 'question_id': 'b2-q1', 'verdict': 'major', 'level_fit': 'ok'},
        {'test_id': 'b2', 'question_id': 'b2-q2', 'verdict': 'ok', 'level_fit': 'ok'},
    ]
    text = se.score(recs, tests, reviews, {'armA': 0.10, 'armB': 0.30})
    row_a = next(l for l in text.splitlines() if l.startswith('| armA'))
    row_b = next(l for l in text.splitlines() if l.startswith('| armB'))
    cells_a = [c.strip() for c in row_a.split('|')[1:-1]]
    cells_b = [c.strip() for c in row_b.split('|')[1:-1]]
    assert cells_a[1:5] == ['2', '1', '1', '0']          # slots, passed, floor fails, other
    assert cells_a[5] == '0.100' and cells_b[5] == '0.150'
    assert float(cells_a[7]) == 0.0 and float(cells_a[8]) == 0.5
    assert float(cells_b[7]) == 0.25 and float(cells_b[9]) == 0.75
    # a1 keys "mat" for q2 too: the duplicate_answer quality check counts it
    assert float(cells_a[6]) > 0


def test_review_packs_hide_arms(tmp_path, monkeypatch):
    monkeypatch.setattr(packs, 'ROOT', str(tmp_path))
    d = tmp_path / 'data' / 'test_quality' / 'experiments' / 'armZ'
    d.mkdir(parents=True)
    (d / 'tests.jsonl').write_text(json.dumps({'outcome': 'pass', 'test_id': 'z1', 'run_tag': 'armZ'}))
    dump = tmp_path / 'dump.json'
    dump.write_text(json.dumps([_test('z1', 'mat')]))
    out = tmp_path / 'packs'
    assert packs.main(['armZ', '--out', str(out), '--input-json', str(dump)]) == 0
    md = (out / 'review_01.md').read_text()
    assert 'z1-q1' in md and 'armZ' not in md
    assert json.loads((out / 'key.json').read_text()) == {'z1': 'armZ'}
