#!/usr/bin/env python3
"""Score the sentence-reference pilot (TASK-907).

    python scripts/score_sentence_ref_pilot.py data/sentence_refs/pilot_2026-10-30 [--worst 10] [--md out.md]

Walks <root>/<language>/<arm>/sentence_refs/{verdicts,check.json,reviewed}
and reports, per arm x language: sentences, median and p10 tightness,
entailment pass %, rewrite %, fail %, deterministic-check failure rate on the
authored docs, and the worst sentences by tightness with reviewer notes.
Applies the decision rule from the tech page: higher median tightness wins
unless its entailment pass rate is more than 3 points lower.
"""

import os
import sys
import glob
import json
import argparse
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from services.dual_translation import sentence_refs as sr  # noqa: E402


def load(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def collect(root: str) -> dict:
    out = {}
    cpath = os.path.join(root, 'contaminated.json')
    contaminated = load(cpath) if os.path.exists(cpath) else {}
    for run in sorted(glob.glob(os.path.join(root, '*', '*'))):
        parts = run.split(os.sep)
        lang, arm = parts[-2], parts[-1]
        base = os.path.join(run, 'sentence_refs')
        if not os.path.isdir(base):
            continue
        wl = load(os.path.join(base, 'worklist.json'))
        titles = {t['test_id']: t.get('title') for t in wl['tests']}
        golds = {t['test_id']: {s['idx']: s['l2_text'] for s in t['sentences']} for t in wl['tests']}
        rows = []
        for vp in glob.glob(os.path.join(base, 'verdicts', '*.json')):
            v = load(vp)
            rv = {}
            rp = os.path.join(base, 'reviewed', os.path.basename(vp))
            if os.path.exists(rp):
                rv = {s['idx']: s['l1'] for s in load(rp).get('sentences', [])}
            for s in v.get('sentences', []):
                rows.append({'test_id': v['test_id'], 'title': titles.get(v['test_id']), 'idx': s['idx'], 'verdict': s.get('verdict'),
                             'entailment_ok': s.get('entailment_ok'), 'tightness': s.get('tightness'), 'notes': s.get('notes') or '',
                             'l1': rv.get(s['idx']), 'gold': golds.get(v['test_id'], {}).get(s['idx']), 'back': s.get('back_translation')})
        chk = load(os.path.join(base, 'check.json')) if os.path.exists(os.path.join(base, 'check.json')) else []
        bad = set(contaminated.get(f'{lang}/{arm}', []))
        for r in rows:
            r['contaminated'] = r['test_id'] in bad
        out[(lang, arm)] = {'rows': rows, 'n_contaminated': len(bad), 'check_failed': sum(1 for c in chk if not c.get('ok')), 'check_total': len(chk),
                            'authored': len(glob.glob(os.path.join(base, 'docs', '*.json'))), 'tests': len(wl['tests'])}
    return out


def stats(rows: list[dict]) -> dict:
    t = [r['tightness'] for r in rows if isinstance(r.get('tightness'), (int, float)) and not r.get('contaminated')]
    n = len(rows) or 1
    q = sorted(t)
    p10 = q[max(0, int(0.1 * len(q)) - 1)] if q else None
    return {'n': len(rows), 'n_blind': len(t), 'median_tightness': round(statistics.median(t), 3) if t else None, 'p10_tightness': round(p10, 3) if p10 is not None else None,
            'entail_pass_pct': round(100 * sum(1 for r in rows if r.get('entailment_ok')) / n, 1),
            'rewrite_pct': round(100 * sum(1 for r in rows if r.get('verdict') == 'rewritten') / n, 1),
            'fail_pct': round(100 * sum(1 for r in rows if r.get('verdict') == 'fail') / n, 1)}


def decide(by_arm: dict[str, dict]) -> str:
    if len(by_arm) < 2 or any(v['median_tightness'] is None for v in by_arm.values()):
        return 'undecided (both arms need scored verdicts)'
    (a, sa), (b, sb) = sorted(by_arm.items(), key=lambda kv: -(kv[1]['median_tightness'] or 0))
    if sa['entail_pass_pct'] + 3 < sb['entail_pass_pct']:
        return f'{b} (higher-tightness arm {a} loses >3 points of entailment)'
    return f'{a} (median tightness {sa["median_tightness"]} vs {sb["median_tightness"]})'


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('root')
    ap.add_argument('--worst', type=int, default=10)
    ap.add_argument('--md')
    a = ap.parse_args()
    data = collect(a.root)
    lines = ['| language | arm | tests | authored | check fails | sentences | blind for tightness | median tightness | p10 | entail % | rewrite % | fail % |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
    per_lang: dict[str, dict[str, dict]] = {}
    for (lang, arm), d in sorted(data.items()):
        s = stats(d['rows'])
        per_lang.setdefault(lang, {})[arm] = s
        lines.append(f'| {lang} | {arm} | {d["tests"]} | {d["authored"]} | {d["check_failed"]}/{d["check_total"]} | {s["n"]} | {s["n_blind"]} ({d["n_contaminated"]} tests excluded) | {s["median_tightness"]} | {s["p10_tightness"]} | {s["entail_pass_pct"]} | {s["rewrite_pct"]} | {s["fail_pct"]} |')
    lines.append('')
    for lang, arms in per_lang.items():
        lines.append(f'- **{lang}**: decision rule picks **{decide(arms)}**')
    lines.append('')
    for (lang, arm), d in sorted(data.items()):
        worst = sorted([r for r in d['rows'] if isinstance(r.get('tightness'), (int, float)) and not r.get('contaminated')], key=lambda r: r['tightness'])[:a.worst]
        if not worst:
            continue
        lines.append(f'### Worst {len(worst)} by tightness — {lang} / {arm}')
        lines.append('')
        for r in worst:
            lines.append(f'- {r["tightness"]:.2f} · {r["test_id"][:8]} idx {r["idx"]} · {r["verdict"]} · gold: {r["gold"]} · ref: {r["l1"]} · back: {r["back"]}' + (f' · notes: {r["notes"]}' if r['notes'] else ''))
        lines.append('')
    text = '\n'.join(lines)
    print(text)
    if a.md:
        with open(a.md, 'w', encoding='utf-8') as fh:
            fh.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
