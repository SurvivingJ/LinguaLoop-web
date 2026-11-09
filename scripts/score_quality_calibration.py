"""Score the test quality checks against hand-labelled findings (TASK-920).

Inputs: <dir>/pack_<lang>.json (sampled findings with their whole test) and
<dir>/labels_<lang>.json ({finding_id, code, label: real|false_alarm}).

For each labelled finding, re-runs the CURRENT checks on its test and asks
whether the same finding (same code, same question) still fires. Reports, per
language x code: labelled, real, precision as labelled (the version that
produced the sample), and precision / kept-real / dropped-real under the
current rules. Writes <dir>/scores.md and prints it.

    python scripts/score_quality_calibration.py data/test_quality/calibration_2026-11-09
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path[:0] = [ROOT]

from services.test_generation import quality_checks as qc  # noqa: E402


def still_fires(item: dict, lang: str) -> bool:
    profile = qc.get_profile(lang)
    qs = [dict(q, question=q['question'], type_code=q['type']) for q in item['questions']]
    target = item.get('flagged_question_id') or ''
    code, tier = item['code'], item.get('tier')
    if item['scope'] == 'passage':
        res = qc.run_passage_checks(item['transcript'], item.get('title'), profile, mode_override='flag')
        return any(r.code == code for r in res)
    if item['scope'] == 'question':
        for i, q in enumerate(qs):
            if q.get('question_id') == target:
                res = qc.run_question_checks(q, item['transcript'], profile, tier, i, mode_override='flag')
                return any(r.code == code for r in res)
        return False
    res = qc.run_test_checks(qs, item['transcript'], profile, tier, mode_override='flag')
    for r in res:
        if r.code != code:
            continue
        if not target or (r.question_index is not None and r.question_index < len(qs)
                          and qs[r.question_index].get('question_id') == target):
            return True
        if code == 'type_mix':
            return True
    return False


def main(d: str) -> int:
    stats = defaultdict(lambda: defaultdict(int))
    for lang in ('ja', 'zh', 'en'):
        pp, lp = os.path.join(d, f'pack_{lang}.json'), os.path.join(d, f'labels_{lang}.json')
        if not (os.path.exists(pp) and os.path.exists(lp)):
            continue
        pack = {i['finding_id']: i for i in json.load(open(pp, encoding='utf-8'))}
        for lab in json.load(open(lp, encoding='utf-8')):
            item = pack[lab['finding_id']]
            real = lab['label'] == 'real'
            fires = still_fires(item, lang)
            for key in ((lang, item['code']), ('all', item['code'])):
                s = stats[key]
                s['n'] += 1
                s['real'] += real
                s['now_fires'] += fires
                s['now_real'] += fires and real
                s['dropped_real'] += (not fires) and real

    lines = ['| language | check | labelled | real | precision (sampled) | still fires | '
             'precision now | real dropped |', '|---|---|---|---|---|---|---|---|']
    for (lang, code) in sorted(stats, key=lambda k: (k[0] != 'all', k[0], k[1])):
        s = stats[(lang, code)]
        p0 = s['real'] / s['n'] if s['n'] else 0
        p1 = f"{s['now_real'] / s['now_fires']:.2f}" if s['now_fires'] else '—'
        lines.append(f"| {lang} | `{code}` | {s['n']} | {s['real']} | {p0:.2f} | {s['now_fires']} | {p1} | {s['dropped_real']} |")
    out = '\n'.join(lines) + '\n'
    with open(os.path.join(d, 'scores.md'), 'w', encoding='utf-8') as f:
        f.write(out)
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, 'data', 'test_quality', 'calibration_2026-11-09')))
