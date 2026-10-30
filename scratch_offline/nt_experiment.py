"""Run one optimisation arm of the tool-free pipeline on the gold sense set.

    python3 scratch_offline/nt_experiment.py ARM [--author-model sonnet]
        [--author-effort low] [--review-model opus] [--review-effort medium]
        [--skip-l1] [--width N] [--variant-batch 4] [--review-batch 4]
        [--no-review] [--chunks 2]

The gold set (data/exercise_seeding/ja/opt/gold/senses.csv) is split into
--chunks run dirs under opt/ARM/, authored and reviewed in parallel with the
given config, then scored by the frozen judge (nt_judge.py). Writes
opt/ARM/summary.json: cost per sense by stage (judge excluded), check pass
rates and judge metrics. `python3 scratch_offline/nt_experiment.py --compare`
prints every arm side by side.
"""
import argparse
import csv
import glob
import json
import os
import shlex
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# NT_LANG (ja | zh | en, default ja) picks the language's experiment directory;
# the scripts this harness starts inherit it and name the language in their prompts.
OPT = os.path.join(REPO, 'data/exercise_seeding', os.environ.get('NT_LANG', 'ja'), 'opt')
GOLD = os.path.join(OPT, 'gold')
csv.field_size_limit(10 ** 9)


def make_runs(arm, chunks, gold=GOLD):
    rows = list(csv.DictReader(open(os.path.join(gold, 'senses.csv'), encoding='utf-8', newline='')))
    cols = list(rows[0].keys())
    per = -(-len(rows) // chunks)
    runs = []
    for i in range(chunks):
        run = os.path.join(OPT, arm, f'r{i:02d}')
        runs.append(run)
        if os.path.exists(os.path.join(run, 'senses.csv')):
            continue
        os.makedirs(run)
        shutil.copy(os.path.join(gold, 'prompts.json'), run)
        with open(os.path.join(run, 'senses.csv'), 'w', encoding='utf-8', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows[i * per:(i + 1) * per])
    return runs


def sh(script, *a, log):
    with open(log, 'a') as fh:
        fh.write(f'\n$ {script} {" ".join(a)}\n')
        fh.flush()
        p = subprocess.run([sys.executable, f'scratch_offline/{script}', *a], cwd=REPO,
                           stdout=fh, stderr=subprocess.STDOUT)
    if p.returncode:
        raise RuntimeError(f'{script} exited {p.returncode} (see {log})')


def process(run, args):
    rel = os.path.relpath(run, REPO)
    log = os.path.join(run, 'experiment.log')
    a = [rel, '--model', args.author_model, '--effort', args.author_effort,
         '--variant-batch', str(args.variant_batch)]
    if args.skip_l1:
        a.append('--skip-l1')
    if args.width:
        a += ['--width', str(args.width)]
    if args.cheatsheet:
        a += ['--cheatsheet', args.cheatsheet]
    a += shlex.split(getattr(args, 'author_args', '') or '')  # NT_AUTHOR_EXTRA_ARGS (env) keeps working too
    sh('nt_author.py', *a, log=log)
    source = 'words'
    if not args.no_review:
        rv = [rel, rel, '--model', args.review_model, '--effort', args.review_effort,
              '--batch', str(args.review_batch), *shlex.split(getattr(args, 'review_args', '') or '')]
        if glob.glob(os.path.join(run, 'fat_seed', 'reviewed', '*.json')) and '--resume' not in rv:
            rv.append('--resume')  # relaunch: do not re-review (re-pay) senses already reviewed
        sh('nt_review.py', *rv, log=log)
        source = 'reviewed'
    sh('nt_judge.py', rel, '--source', source, *judge_flags(args), log=log)
    return source


def judge_flags(args):
    """nt_judge.py flags for the arm's screening judge (frozen judge when unset)."""
    f = []
    if getattr(args, 'judge_model', None):
        f += ['--model', args.judge_model]
    if getattr(args, 'judge_effort', None):
        f += ['--effort', args.judge_effort]
    if getattr(args, 'judge_rubric', None):
        f += ['--rubric', str(args.judge_rubric)]
    return f


def judge_file(source, config):
    from nt_judge import output_name, MODEL, EFFORT, DEFAULT_BATCH, JUDGE_VERSION
    return output_name(source, config.get('judge_model') or MODEL, config.get('judge_effort') or EFFORT,
                       DEFAULT_BATCH, '', config.get('judge_rubric') or JUDGE_VERSION)


def summarise(arm, runs, source, config):
    cost = {}
    out_tokens = {}
    n = 0
    first = [0, 0]
    final_ok = 0
    judged = {}
    for run in runs:
        seen_first = False
        for line in open(os.path.join(run, 'fat_seed', 'nt_usage.jsonl')):
            r = json.loads(line)
            if r.get('tag') == 'first_pass_check':
                if not seen_first:  # a resumed run logs the check again; only the first run's record counts
                    first[0] += r['ok']
                    first[1] += r['of']
                    seen_first = True
                continue
            stage = r['tag'].split(':')[0].rstrip('0123456789')
            cost[stage] = cost.get(stage, 0) + (r.get('cost_usd') or 0)
            out_tokens[stage] = out_tokens.get(stage, 0) + (r.get('output') or 0)
        chk = os.path.join(run, 'fat_seed', f'check.{source}.json')
        if os.path.exists(chk):
            final_ok += sum(1 for v in json.load(open(chk)).values() if v.get('status') == 'ok')
        judged.update(json.load(open(os.path.join(run, 'fat_seed', judge_file(source, config)))))
        n += sum(1 for _ in csv.DictReader(open(os.path.join(run, 'senses.csv'), encoding='utf-8', newline='')))
    scored = [r for r in judged.values() if r.get('score') is not None]
    sev = lambda k: sum(1 for r in scored for d in r['defects'] if d.get('severity') == k)  # noqa: E731
    pipeline = {k: v for k, v in cost.items() if k != 'judge'}
    m = len(scored) or 1
    summary = {
        'arm': arm, 'config': config, 'senses': n, 'judged': len(scored),
        'cost_per_sense': round(sum(pipeline.values()) / n, 4),
        'cost_by_stage_per_sense': {k: round(v / n, 4) for k, v in cost.items()},
        'output_tokens_per_sense': {k: round(v / n) for k, v in out_tokens.items()},
        'first_pass_check': f'{first[0]}/{first[1]}', 'final_check_ok': final_ok,
        'judge_mean_score': round(sum(r['score'] for r in scored) / m, 2),
        # level_1 is dropped in some arms, so also score without level_1 defects
        'judge_mean_score_ex_l1': round(sum(
            max(0.0, 10.0 - sum({'fatal': 3.0, 'major': 1.0, 'minor': 0.3}.get(d.get('severity'), 1.0)
                                for d in r['defects'] if 'level_1' not in (d.get('path') or '')))
            for r in scored) / m, 2),
        'fatal_per_sense': round(sev('fatal') / m, 2), 'major_per_sense': round(sev('major') / m, 2),
        'minor_per_sense': round(sev('minor') / m, 2),
        'clean_senses': sum(1 for r in scored if not r['defects']),
    }
    json.dump(summary, open(os.path.join(OPT, arm, 'summary.json'), 'w'), indent=1)
    return summary


def compare():
    rows = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(OPT, '*', 'summary.json')))]
    cols = ['arm', 'senses', 'cost_per_sense', 'judge_mean_score', 'judge_mean_score_ex_l1', 'fatal_per_sense',
            'major_per_sense', 'minor_per_sense', 'clean_senses', 'first_pass_check', 'final_check_ok']
    print(' | '.join(cols))
    for r in rows:
        print(' | '.join(str(r.get(c)) for c in cols))


# ------------------------------------------------------------------------------------------------
# Track C additions (measurement). All flags below are additive; `--compare` above is unchanged.
#   --judge SPEC             (with any flag below) judge to analyse: v2 (frozen), v3.opus-medium, opus-medium;
#                            default = each arm's own screening judge (summary.json/config.json), else v2
#   --passes                 every arm: mean over ALL passes of its judge + per-pass means
#   --defects ARM [ARM..]    defect classes per arm (block x severity, per sense, over all passes);
#                            --detail groups by full path with array indexes stripped
#   --fatals ARM             list one arm's fatal defects (sid, path, problem); --severity major|minor|all,
#                            --block level_7 to filter
#   --reliability            judge repeatability for arms with >= 2 frozen passes + the resolution rule
#   --proxy sonnet-high      proxy judge (nt_judge.py --model/--effort) vs the frozen judge's pass mean
#   --show ARM SID [--path variants.A.level_3]   document context + every pass's defects for one sense
#   --confirm FINALIST [--against c_base100] [--judge v3] [--nfatal 10]   finalist confirmation report under an
#                            independent judge: paired difference +- 2SE, fatal shares +- 2SE, first-pass check,
#                            the proxy's paired difference beside it, N fatals per arm with document text
#   --resummarise ARM [ARM ...]   rewrite summary.json from existing files (first-pass check = first record per run)
#   --stale [ARM ...]        staleness audit: judged senses whose document changed since judging (doc_sha,
#                            judged_at or mtimes), relaunch signals, per-run-dir re-judge lists
#   --loss ARM [--against c_base100] [--top 3] [--examples 2]   where ARM loses points vs another arm, by
#                            defect class (block x severity), with example defects resolved to document text
# ------------------------------------------------------------------------------------------------
import math  # noqa: E402
import re  # noqa: E402
import statistics  # noqa: E402

# judge.<src>.v<N>[.<model>-<effort>[-b<batch>]][_tag].json  ->  spec 'v<N>[.<model>-<effort>]', tag
JUDGE_RE = re.compile(r'^judge\.(reviewed|words)\.v(\d+)(?:\.([a-z0-9.-]+?))?(_[A-Za-z0-9]+)?\.json$')
FROZEN_SPEC = 'v2'  # the frozen judge (opus/high, rubric 2)


def judge_spec(fname):
    """('v3.opus-medium', '_rep') for a judge file name, or None."""
    m = JUDGE_RE.match(fname)
    if not m:
        return None
    return 'v' + m.group(2) + ('.' + m.group(3) if m.group(3) else ''), m.group(4) or ''


def norm_spec(spec):
    """Accept 'v3.opus-medium', 'opus-medium' (= v2 proxy), 'v2'."""
    if spec and not re.match(r'^v\d+', spec):
        spec = FROZEN_SPEC + '.' + spec
    return spec


def arm_source(arm):
    """'reviewed' if the arm has reviewed documents, else 'words' (an arm relaunched with a different
    --no-review setting can hold judge files of both sources; only the arm's final source counts)."""
    return 'reviewed' if glob.glob(os.path.join(OPT, arm, 'r*', 'fat_seed', 'reviewed', '*.json')) else 'words'


def arm_spec(arm):
    """The arm's own screening judge: resolved from summary.json / config.json like summarise() does."""
    for name in ('summary.json', 'config.json'):
        path = os.path.join(OPT, arm, name)
        if os.path.exists(path):
            cfg = json.load(open(path))
            cfg = cfg.get('config', cfg) if name == 'summary.json' else cfg
            if cfg.get('judge_model') or cfg.get('judge_effort') or cfg.get('judge_rubric'):
                return judge_spec(judge_file('reviewed', cfg))[0]
            return FROZEN_SPEC
    return FROZEN_SPEC
WEIGHTS = {'fatal': 3.0, 'major': 1.0, 'minor': 0.3}
# a defect that only says this gold sense duplicates another gold sense (unfixable by the pipeline)
DUP_RE = re.compile(r'(duplicat|same sense as|same meaning as|identical sense)(?=.*\b(36\d{3}|39\d{3}|51\d{3})\b)', re.I | re.S)
SEV = ('fatal', 'major', 'minor')


def judge_passes(arm, judge=None):
    """{tag: {sid: result}} for one arm, merged over its run dirs (scored senses only).

    judge=None: the arm's own screening judge (frozen v2 unless the arm was run with --judge-*).
    judge='v3.opus-medium' / 'v2' / 'sonnet-high' (= v2.sonnet-high): that judge's passes."""
    judge = norm_spec(judge) or arm_spec(arm)
    source = arm_source(arm)
    passes = {}
    for fs in sorted(glob.glob(os.path.join(OPT, arm, 'r*', 'fat_seed'))):
        for f in sorted(os.listdir(fs)):
            sp = judge_spec(f)
            if not sp or sp[0] != judge or not f.startswith(f'judge.{source}.'):
                continue
            tag = sp[1]
            res = json.load(open(os.path.join(fs, f)))
            passes.setdefault(tag, {}).update({s: r for s, r in res.items() if r.get('score') is not None})
    return passes


def arms_with_judge():
    return sorted(a for a in os.listdir(OPT)
                  if glob.glob(os.path.join(OPT, a, 'r*', 'fat_seed', 'judge.*.v*.json')))


def spec_model(spec):
    """(model, effort) that a judge spec bills under."""
    m = re.match(r'^v\d+(?:\.([a-z0-9.-]+?)-([a-z]+)(?:-b\d+)?)?$', spec or FROZEN_SPEC)
    return (m.group(1), m.group(2)) if m and m.group(1) else ('opus', 'high')


def per_sense_means(passes):
    sids = set()
    for p in passes.values():
        sids |= set(p)
    return {s: statistics.mean(p[s]['score'] for p in passes.values() if s in p) for s in sorted(sids, key=int)}


def strip_path(path):
    p = re.sub(r'\[\d+\]', '', path or '')
    p = re.sub(r'^variants\.[AB]\.', '', p)
    return p or '(none)'


def block_of(path):
    return strip_path(path).split('.')[0]


def sev_counts(result):
    c = {k: 0 for k in SEV}
    for d in result.get('defects', []):
        if d.get('severity') in c:
            c[d['severity']] += 1
    return c


def judge_cost(arm):
    """{(model, effort): [usd, calls]} of judge calls in the arm's usage logs."""
    out = {}
    for p in glob.glob(os.path.join(OPT, arm, 'r*', 'fat_seed', 'nt_usage.jsonl')):
        for line in open(p):
            r = json.loads(line)
            if r.get('tag', '').startswith('judge'):
                k = out.setdefault((r.get('model'), r.get('effort')), [0.0, 0])
                k[0] += r.get('cost_usd') or 0
                k[1] += 1
    return out


def pearson(x, y):
    if len(x) < 3 or statistics.pstdev(x) == 0 or statistics.pstdev(y) == 0:
        return float('nan')
    mx, my = statistics.mean(x), statistics.mean(y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (len(x) * statistics.pstdev(x) * statistics.pstdev(y))


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def fmt(v, nd=2):
    return '-' if v is None or (isinstance(v, float) and math.isnan(v)) else f'{v:.{nd}f}'


def passes_table(judge=None):
    print('arm | judge | $/sense | passes | n | mean(all) | per-pass means | fatal | major | minor | clean% | judge$')
    for arm in arms_with_judge():
        spec = norm_spec(judge) or arm_spec(arm)
        passes = judge_passes(arm, spec)
        if not passes:
            continue
        tags = sorted(passes, key=lambda t: (t != '', t))
        means = per_sense_means(passes)
        nmax = len(means)
        pp = []
        for t in tags:
            sc = [r['score'] for r in passes[t].values()]
            pp.append(f'{statistics.mean(sc):.2f}' + ('' if len(sc) == nmax else f'(n={len(sc)})'))
        tot = {k: 0 for k in SEV}
        cells = 0
        clean = 0
        for p in passes.values():
            for r in p.values():
                cells += 1
                clean += not r.get('defects')
                for k, v in sev_counts(r).items():
                    tot[k] += v
        sp = os.path.join(OPT, arm, 'summary.json')
        cps = json.load(open(sp)).get('cost_per_sense') if os.path.exists(sp) else None
        jc = judge_cost(arm).get(spec_model(spec), [0, 0])
        print(f"{arm} | {spec} | {fmt(cps, 3)} | {len(tags)} | {nmax} | {statistics.mean(means.values()):.2f} | "
              f"{'/'.join(pp)} | {tot['fatal'] / cells:.2f} | {tot['major'] / cells:.2f} | {tot['minor'] / cells:.2f} | "
              f"{100 * clean / cells:.0f} | {jc[0]:.2f}")


def defects_table(arms, detail=False, judge=None):
    data = {}
    for arm in arms:
        passes = judge_passes(arm, judge)
        cells = sum(len(p) for p in passes.values()) or 1
        agg = {}
        for p in passes.values():
            for r in p.values():
                for d in r.get('defects', []):
                    key = strip_path(d.get('path')) if detail else block_of(d.get('path'))
                    c = agg.setdefault(key, {k: 0 for k in SEV})
                    if d.get('severity') in c:
                        c[d['severity']] += 1
        data[arm] = {k: {s: v / cells for s, v in c.items()} for k, c in agg.items()}

    def lost(c):
        return sum(WEIGHTS[s] * c.get(s, 0) for s in SEV) if c else 0.0

    keys = set()
    for d in data.values():
        keys |= set(d)
    keys = sorted(keys, key=lambda k: -max(lost(data[a].get(k)) for a in arms))
    print('per sense, averaged over all passes of ' + ', '.join(f'{a}:{norm_spec(judge) or arm_spec(a)}' for a in arms)
          + '; cell = fatal/major/minor (points lost)')
    print(('path' if detail else 'block') + ' | ' + ' | '.join(arms))
    for k in keys:
        cells = []
        for a in arms:
            c = data[a].get(k)
            cells.append(f"{c['fatal']:.2f}/{c['major']:.2f}/{c['minor']:.2f} ({lost(c):.2f})" if c else '-')
        print(f'{k} | ' + ' | '.join(cells))
    tot = []
    for a in arms:
        t = {s: sum(c[s] for c in data[a].values()) for s in SEV}
        tot.append(f"{t['fatal']:.2f}/{t['major']:.2f}/{t['minor']:.2f} ({lost(t):.2f})")
    print('TOTAL | ' + ' | '.join(tot))


def list_defects(arm, severity='fatal', block=None, judge=None):
    n = 0
    spec = norm_spec(judge) or arm_spec(arm)
    for tag, p in sorted(judge_passes(arm, spec).items()):
        for sid in sorted(p, key=int):
            for d in p[sid].get('defects', []):
                if severity != 'all' and d.get('severity') != severity:
                    continue
                if block and block_of(d.get('path')) != block:
                    continue
                n += 1
                print(f"[{spec}{tag}] {sid} {d.get('severity')} {d.get('path')}\n    {d.get('problem')}")
    print(f'{n} defects')


def reliability(judge=None):
    """One section per judge spec (the arm's own judge unless --judge is given)."""
    groups = {}
    for arm in arms_with_judge():
        spec = norm_spec(judge) or arm_spec(arm)
        if len(judge_passes(arm, spec)) >= 2:
            groups.setdefault(spec, []).append(arm)
    if not groups:
        print('no arm has two passes of ' + (norm_spec(judge) or 'its own judge'))
    for spec, arms in sorted(groups.items()):
        print(f'=== judge {spec}: arms with >= 2 passes: {", ".join(arms)}')
        _reliability(spec, arms)
        print()


def _reliability(spec, arm_list):
    pooled = []
    arm_means = {}
    pair_means = {}
    print('arm | n | p1 | p2 | r | mean|d| | SD(d) | fatal: r / same-count% | major: r / same% | minor: r / same% | '
          'defect path recur% (same sev / any sev)')
    for arm in arm_list:
        passes = judge_passes(arm, spec)
        tags = sorted(passes, key=lambda t: (t != '', t))
        if len(tags) < 2:
            continue
        p1, p2 = passes[tags[0]], passes[tags[1]]
        common = sorted(set(p1) & set(p2), key=int)
        if len(common) < 5:
            continue
        x = [p1[s]['score'] for s in common]
        y = [p2[s]['score'] for s in common]
        d = [a - b for a, b in zip(x, y)]
        pooled += d
        arm_means[arm] = (statistics.mean(x), statistics.mean(y))
        pair_means[arm] = per_sense_means({tags[0]: p1, tags[1]: p2})
        sev_cells = []
        for sv in SEV:
            cx = [sev_counts(p1[s])[sv] for s in common]
            cy = [sev_counts(p2[s])[sv] for s in common]
            same = sum(a == b for a, b in zip(cx, cy)) / len(common)
            sev_cells.append(f'{fmt(pearson(cx, cy))} / {100 * same:.0f}')
        tot = same_sev = any_sev = 0
        for s in common:
            d1 = [(strip_path(q.get('path')), q.get('severity')) for q in p1[s].get('defects', [])]
            d2 = [(strip_path(q.get('path')), q.get('severity')) for q in p2[s].get('defects', [])]
            paths2 = {q[0] for q in d2}
            for q in d1:
                tot += 1
                same_sev += q in d2
                any_sev += q[0] in paths2
        print(f"{arm} | {len(common)} | {statistics.mean(x):.2f} | {statistics.mean(y):.2f} | {fmt(pearson(x, y))} | "
              f"{statistics.mean(abs(v) for v in d):.2f} | {statistics.pstdev(d):.2f} | " + ' | '.join(sev_cells) +
              f" | {100 * same_sev / max(tot, 1):.0f} / {100 * any_sev / max(tot, 1):.0f}")
    # which score definition repeats best? (minors are noisy; gold-set duplicate-sense defects are constant)
    alt = {'full': lambda r: r['score'],
           'no_minor': lambda r: max(0.0, 10 - 3 * sev_counts(r)['fatal'] - sev_counts(r)['major']),
           'fatal_only': lambda r: -sev_counts(r)['fatal'],
           'no_dup': lambda r: max(0.0, 10 - sum(WEIGHTS.get(d.get('severity'), 1.0) for d in r.get('defects', [])
                                                 if not DUP_RE.search(d.get('problem', '')))) }
    print('\nper-sense pass-to-pass r by score definition: arm | ' + ' | '.join(alt))
    for arm in sorted(pair_means):
        passes = judge_passes(arm, spec)
        tags = sorted(passes, key=lambda t: (t != '', t))
        p1, p2 = passes[tags[0]], passes[tags[1]]
        common = sorted(set(p1) & set(p2), key=int)
        print(f'{arm} | ' + ' | '.join(fmt(pearson([f(p1[s]) for s in common], [f(p2[s]) for s in common]))
                                      for f in alt.values()))
    if len(arm_means) >= 3:
        arms = sorted(arm_means)
        m1 = [arm_means[a][0] for a in arms]
        m2 = [arm_means[a][1] for a in arms]
        flips = [(a, b) for i, a in enumerate(arms) for b in arms[i + 1:]
                 if (arm_means[a][0] - arm_means[b][0]) * (arm_means[a][1] - arm_means[b][1]) < 0]
        print(f'\narm ranking: pass1 {" > ".join(sorted(arms, key=lambda a: -arm_means[a][0]))}')
        print(f'             pass2 {" > ".join(sorted(arms, key=lambda a: -arm_means[a][1]))}')
        print(f'Spearman(arm means p1, p2) = {fmt(spearman(m1, m2))}; pairwise order flips: {len(flips)} of '
              f'{len(arms) * (len(arms) - 1) // 2}' + (f' {flips}' if flips else ''))
    if pooled:
        sigma_j = statistics.pstdev(pooled) / math.sqrt(2)
        n_ref = int(statistics.median(len(pair_means[a]) for a in pair_means)) or 23
        # judge noise is partly batch-correlated (3 senses per call), so the per-pass ARM mean moves more
        # than independent per-sense noise predicts; estimate it from the observed pass-to-pass arm-mean shifts
        shifts = [m[0] - m[1] for m in arm_means.values()]
        sigma_arm = statistics.pstdev(shifts) / math.sqrt(2) if len(shifts) >= 3 else sigma_j / math.sqrt(n_ref)
        sigma_eff = max(sigma_j, sigma_arm * math.sqrt(n_ref))
        # per-sense between-arm paired differences of 2-pass means; their variance minus the judge
        # component (sigma_j^2 for a difference of two 2-pass means) is the "true" document variance
        true_vars = []
        arms = sorted(pair_means)
        for i, a in enumerate(arms):
            for b in arms[i + 1:]:
                common = sorted(set(pair_means[a]) & set(pair_means[b]), key=int)
                if len(common) >= 5:
                    dv = statistics.pvariance([pair_means[a][s] - pair_means[b][s] for s in common])
                    true_vars.append(max(dv - sigma_j ** 2, 0.0))
        if not true_vars:  # a single arm: use its between-sense variance of pass means as the doc component
            one = next(iter(pair_means.values()))
            true_vars = [max(2 * (statistics.pvariance(list(one.values())) - sigma_j ** 2 / 2), 0.0)]
        v_true = statistics.median(true_vars) if true_vars else 0.0
        print(f'\njudge noise per sense per pass: sigma_j = {sigma_j:.2f} points (from {len(pooled)} repeated senses, '
              f'independent-sense model -> arm-mean SD {sigma_j / math.sqrt(n_ref):.2f} at n={n_ref}); '
              f'observed pass-to-pass arm-mean shift SD = {sigma_arm:.2f} (from {len(shifts)} arms: '
              f'{", ".join(f"{v:+.2f}" for v in shifts)}) -> effective per-sense sigma {sigma_eff:.2f}')
        print(f'between-arm paired doc variance (judge-free, median over arm pairs) = {v_true:.2f} '
              f'(SD {math.sqrt(v_true):.2f}); this part never shrinks with more passes, only with more senses')
        print('resolution: an observed arm-vs-arm difference D is credible when D >= 2*SE, '
              f'SE = sqrt(v_true + 2*sigma_eff^2/k) / sqrt(n)   (k passes each, n common senses, sigma_eff={sigma_eff:.2f})')
        print('k passes | SD(per-sense diff) | 2*SE @ n=23 | 2*SE @ n=100 | 2*SE @ n=200 | n for D=0.5 | n for D=1.0')
        for k in (1, 2, 3, 4):
            sd = math.sqrt(v_true + 2 * sigma_eff ** 2 / k)
            print(f'{k} | {sd:.2f} | {2 * sd / math.sqrt(23):.2f} | {2 * sd / math.sqrt(100):.2f} | '
                  f'{2 * sd / math.sqrt(200):.2f} | {math.ceil((2 * sd / 0.5) ** 2)} | {math.ceil((2 * sd / 1.0) ** 2)}')


def proxy_report(name, against=None):
    name = norm_spec(name)
    against = norm_spec(against) or FROZEN_SPEC
    model, effort = spec_model(name)
    px, fy = [], []
    arm_rows = []
    print(f'judge {name} vs judge {against}, per-sense scores against the {against} pass mean')
    print('arm | n | proxy mean (k) | frozen mean (k) | bias | r | fatal r | major r | minor r | proxy $/sense | frozen $/sense')
    for arm in arms_with_judge():
        frozen = judge_passes(arm, against)
        prox = judge_passes(arm, name)
        if not prox or not frozen:
            continue
        fm, pm = per_sense_means(frozen), per_sense_means(prox)
        common = sorted(set(fm) & set(pm), key=int)
        if len(common) < 5:
            continue
        x = [pm[s] for s in common]
        y = [fm[s] for s in common]
        px += x
        fy += y
        sev_r = []
        for sv in SEV:
            cx = [statistics.mean(sev_counts(p[s])[sv] for p in prox.values() if s in p) for s in common]
            cy = [statistics.mean(sev_counts(p[s])[sv] for p in frozen.values() if s in p) for s in common]
            sev_r.append(fmt(pearson(cx, cy)))
        jc = judge_cost(arm)
        pc = jc.get((model, effort), [0, 0])[0] / (len(common) * len(prox))
        fc = jc.get(spec_model(against), [0, 0])[0] / (len(common) * len(frozen))
        arm_rows.append((arm, statistics.mean(x), statistics.mean(y)))
        print(f'{arm} | {len(common)} | {statistics.mean(x):.2f} ({len(prox)}) | {statistics.mean(y):.2f} ({len(frozen)}) | '
              f'{statistics.mean(x) - statistics.mean(y):+.2f} | {fmt(pearson(x, y))} | ' + ' | '.join(sev_r) +
              f' | {pc:.3f} | {fc:.3f}')
    if len(px) >= 5:
        print(f'\npooled per-sense r = {fmt(pearson(px, fy))} over {len(px)} senses; '
              f'mean |proxy - frozen| per sense = {statistics.mean(abs(a - b) for a, b in zip(px, fy)):.2f}')
    if len(arm_rows) >= 3:
        pm = [r[1] for r in arm_rows]
        fm = [r[2] for r in arm_rows]
        flips = [(a[0], b[0]) for i, a in enumerate(arm_rows) for b in arm_rows[i + 1:]
                 if (a[1] - b[1]) * (a[2] - b[2]) < 0]
        print(f'arm means: Spearman = {fmt(spearman(pm, fm))}, Pearson = {fmt(pearson(pm, fm))}, '
              f'mean |arm-mean error| = {statistics.mean(abs(a - b) for a, b in zip(pm, fm)):.2f}; '
              f'pairwise order flips: {len(flips)} of {len(arm_rows) * (len(arm_rows) - 1) // 2}'
              + (f' {flips}' if flips else ''))
        print('ranking proxy : ' + ' > '.join(r[0] for r in sorted(arm_rows, key=lambda r: -r[1])))
        print('ranking frozen: ' + ' > '.join(r[0] for r in sorted(arm_rows, key=lambda r: -r[2])))


def show(arm, sid, path=None, judge=None):
    docs = glob.glob(os.path.join(OPT, arm, 'r*', 'fat_seed', 'reviewed', f'{sid}.json')) or \
        glob.glob(os.path.join(OPT, arm, 'r*', 'fat_seed', 'words', f'{sid}.json'))
    if not docs:
        print('no document')
        return
    doc = json.load(open(docs[0]))
    core = doc['core']
    print(f"{arm} {sid} {doc.get('lemma')} [{os.path.relpath(docs[0], OPT)}]")
    print(f"DEF: {core.get('definition')} | FP: {core.get('sense_fingerprint')} | register={core.get('register')} "
          f"pos={core.get('pos')} collocate={core.get('primary_collocate')}")
    for i, s in enumerate(core.get('sentences', [])):
        print(f"S[{i}] {(s.get('source') or '')[:5]:5} {s.get('complexity_tier', '')} {s.get('text')}")
    m = re.match(r'variants\.([AB])\.(\w+)', path or '')
    blocks = [(m.group(1), m.group(2))] if m else [(v, b) for v in 'AB' for b in doc.get('variants', {}).get(v, {})]
    for v, b in blocks:
        blk = doc['variants'][v].get(b)
        if m or not (isinstance(blk, dict) and 'declined' in blk):
            print(f'{v}.{b}: {json.dumps(blk, ensure_ascii=False)}')
    if m:
        o = 'B' if m.group(1) == 'A' else 'A'
        ob = doc['variants'][o].get(m.group(2))
        if isinstance(ob, dict) and 'options' in ob:
            print(f"{o}.{m.group(2)} options: {[x.get('text') for x in ob['options']]}")
    spec = norm_spec(judge) or arm_spec(arm)
    for tag, p in sorted(judge_passes(arm, spec).items()):
        r = p.get(str(sid))
        if not r:
            continue
        print(f"-- judge {spec}{tag}: score {r['score']:.1f}, sense_fit={r.get('sense_fit')}")
        for d in r.get('defects', []):
            if not path or (d.get('path') or '').startswith(path):
                print(f"   {d.get('severity'):5} {d.get('path')}: {d.get('problem')}")


def text_at(doc, path):
    """The document text a defect path points at, compact; None if the path does not resolve."""
    node = doc
    try:
        for name, idx in re.findall(r'([^.\[\]]+)|\[(\d+)\]', path or ''):
            node = node[int(idx)] if idx else node[name]
    except (KeyError, IndexError, TypeError):
        return None
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        if 'text' in node:
            return node['text'] + (f"  // {node['explanation']}" if node.get('explanation') else '')
        return json.dumps(node, ensure_ascii=False)
    return json.dumps(node, ensure_ascii=False)


def loss_report(arm, against='c_base100', top=3, examples=2, judge=None):
    """Where ARM loses points relative to AGAINST, by defect class (block x severity), with concrete examples."""
    def classes(a):
        spec = norm_spec(judge) or arm_spec(a)
        passes = judge_passes(a, spec)
        cells = sum(len(p) for p in passes.values()) or 1
        agg = {}
        for tag, p in passes.items():
            for sid, r in p.items():
                for d in r.get('defects', []):
                    e = agg.setdefault((block_of(d.get('path')), d.get('severity')), [0, []])
                    e[0] += 1
                    e[1].append((sid, tag, d))
        return spec, {k: (v[0] / cells, v[1]) for k, v in agg.items()}, cells

    sa, A, _ = classes(arm)
    sb, B, _ = classes(against)
    if sa != sb:
        print(f'WARNING: {arm} judged by {sa} but {against} by {sb}; classes are not directly comparable')
    for a in (arm, against):
        sp = os.path.join(OPT, a, 'summary.json')
        if os.path.exists(sp):
            s = json.load(open(sp))
            stages = ' '.join(f"{k}={v:.3f}" for k, v in s['cost_by_stage_per_sense'].items() if k != 'judge')
            print(f"{a}: score {s['judge_mean_score']} | fatal {s['fatal_per_sense']} major {s['major_per_sense']} "
                  f"minor {s['minor_per_sense']} /sense | ${s['cost_per_sense']}/sense ({stages}) | "
                  f"first-pass check {s['first_pass_check']} | judge {sa if a == arm else sb}")
    rows = sorted(((WEIGHTS.get(k[1], 1.0) * (A.get(k, (0,))[0] - B.get(k, (0,))[0]), k) for k in set(A) | set(B)),
                  reverse=True)
    print(f'\nclass (block x severity) | {arm} /sense | {against} /sense | points lost vs {against} /sense')
    for delta, k in rows:
        if abs(delta) >= 0.02:
            print(f"{k[0]} {k[1]} | {A.get(k, (0,))[0]:.2f} | {B.get(k, (0,))[0]:.2f} | {delta:+.2f}")
    print(f'TOTAL | | | {sum(d for d, _ in rows):+.2f}')
    docs = {}
    for delta, k in rows[:top]:
        if delta <= 0:
            break
        print(f'\n== {k[0]} {k[1]}: {delta:+.2f} points/sense vs {against}')
        pool = sorted(A[k][1], key=lambda e: int(e[0]))
        step = max(1, len(pool) // examples)
        for sid, tag, d in pool[::step][:examples]:
            if sid not in docs:
                f = glob.glob(os.path.join(OPT, arm, 'r*', 'fat_seed', 'reviewed', f'{sid}.json')) or \
                    glob.glob(os.path.join(OPT, arm, 'r*', 'fat_seed', 'words', f'{sid}.json'))
                docs[sid] = json.load(open(f[0])) if f else {}
            doc = docs[sid]
            print(f"  {sid} {doc.get('lemma', '')} {d.get('path')}")
            print(f"    problem: {(d.get('problem') or '')[:260]}")
            t = text_at(doc, d.get('path'))
            if t:
                print(f"    text: {t[:260]}")
            m = re.match(r'variants\.([AB])\.(\w+)', d.get('path') or '')
            if m and isinstance(doc.get('variants', {}).get(m.group(1), {}).get(m.group(2)), dict):
                blk = doc['variants'][m.group(1)][m.group(2)]
                idx = [blk[k2] for k2 in ('anchor_sentence_index', 'sentence_index', 'correct_sentence_index') if isinstance(blk.get(k2), int)]
                for i in idx[:1]:
                    if i < len(doc.get('core', {}).get('sentences', [])):
                        print(f"    anchor S[{i}]: {doc['core']['sentences'][i].get('text')}")


def stale_report(arms=None, judge=None):
    """Staleness audit: per run dir, judged senses whose current document differs from the one judged.

    Evidence used, strongest first: doc_sha mismatch (records written by the hashing judge);
    document mtime after the record's judged_at; for legacy records, document mtime after the judge
    file's mtime (weak: a resume re-saves the file). Also prints the relaunch signals (several
    `$ nt_author.py` blocks in experiment.log, judge files for both sources) and the share of the
    judge's quoted 「…」 strings missing from the current documents (35% is the paraphrase baseline)."""
    import datetime
    arms = arms or arms_with_judge()
    print('arm | judge | run dirs | judged | hash-checked | stale (sha) | stale (time) | legacy unverifiable | '
          'quotes missing | relaunched run dirs | both sources | verdict')
    for arm in arms:
        spec = norm_spec(judge) or arm_spec(arm)
        source = arm_source(arm)
        judged = checked = stale_sha = stale_time = legacy = qhit = qmiss = 0
        relaunched = both = 0
        stale_dirs = {}
        runs = sorted(glob.glob(os.path.join(OPT, arm, 'r*', 'fat_seed')))
        for fs in runs:
            run = os.path.dirname(fs)
            log = os.path.join(run, 'experiment.log')
            if os.path.exists(log) and sum(1 for l in open(log) if l.startswith('$ nt_author.py')) > 1:
                relaunched += 1
            names = os.listdir(fs)
            specs_here = {(judge_spec(f)[0], f.split('.')[1]) for f in names if judge_spec(f)}
            if {(spec, 'reviewed'), (spec, 'words')} <= specs_here:
                both += 1
            for f in sorted(names):
                sp = judge_spec(f)
                if not sp or sp[0] != spec or not f.startswith(f'judge.{source}.'):
                    continue
                jpath = os.path.join(fs, f)
                jtime = os.path.getmtime(jpath)
                for sid, r in json.load(open(jpath)).items():
                    if not isinstance(r, dict) or r.get('score') is None:
                        continue
                    dpath = os.path.join(fs, source, f'{sid}.json')
                    if not os.path.exists(dpath):
                        continue
                    judged += 1
                    doc = json.load(open(dpath))
                    blob = json.dumps(doc, ensure_ascii=False)
                    for q in re.findall(r'「([^」]{6,})」', ' '.join(d.get('problem', '') for d in r.get('defects', []))):
                        qhit += q in blob
                        qmiss += q not in blob
                    bad = False
                    if r.get('doc_sha'):
                        checked += 1
                        from nt_judge import doc_sha
                        if r['doc_sha'] != doc_sha(doc):
                            stale_sha += 1
                            bad = True
                    elif r.get('judged_at'):
                        jt = datetime.datetime.fromisoformat(r['judged_at']).timestamp()
                        if os.path.getmtime(dpath) > jt + 1:
                            stale_time += 1
                            bad = True
                    else:
                        legacy += 1
                        if os.path.getmtime(dpath) > jtime + 1:
                            stale_time += 1
                            bad = True
                    if bad:
                        stale_dirs.setdefault(os.path.basename(run), []).append(sid)
        if not judged:
            continue
        stale = stale_sha + stale_time
        pct = 100 * stale / judged
        verdict = 'STALE' if pct > 5 else ('clean' if pct == 0 else 'ok (<=5%)')
        if relaunched or both:
            verdict += ' / relaunched: hash-less records unverifiable' if legacy else ' / relaunched (hash-checked)'
        qpct = 100 * qmiss / max(qhit + qmiss, 1)
        if qpct > 45:
            verdict += f' / quotes missing {qpct:.0f}% (>45%)'
        print(f'{arm} | {spec} {source} | {len(runs)} | {judged} | {checked} | {stale_sha} | {stale_time} | {legacy} | '
              f'{qpct:.0f}% | {relaunched} | {both} | {verdict}')
        for rd, sids in sorted(stale_dirs.items()):
            print(f'    {rd}: re-judge {len(sids)} sense(s): {", ".join(sids)}')


def confirm_report(finalist, against='c_base100', judge='v3', nfatal=10):
    """Finalist confirmation: both arms judged by the same (independent) judge, paired by sense id."""
    import random
    spec = norm_spec(judge)
    proxy = arm_spec(finalist)
    data = {}
    for arm in (finalist, against):
        P = judge_passes(arm, spec)
        if not P:
            print(f'{arm}: no {spec} judgement yet (run nt_judge.py on its run dirs first)')
            return
        tags = sorted(P, key=lambda t: (t != '', t))
        data[arm] = (per_sense_means(P), P[tags[0]], len(tags))
    common = sorted(set(data[finalist][0]) & set(data[against][0]), key=int)
    n = len(common)
    d = [data[finalist][0][s] - data[against][0][s] for s in common]
    print(f'=== confirmation under judge {spec} ({spec_model(spec)[0]}/{spec_model(spec)[1]}), {n} common senses, '
          f'passes: {finalist} {data[finalist][2]}, {against} {data[against][2]}')
    print(f'{finalist} mean {statistics.mean(data[finalist][0][s] for s in common):.2f} | {against} mean '
          f'{statistics.mean(data[against][0][s] for s in common):.2f} | paired difference {statistics.mean(d):+.2f} '
          f'+- {2 * statistics.pstdev(d) / math.sqrt(n):.2f} (2*SE) | better/worse/same {sum(1 for v in d if v > 0)}/'
          f'{sum(1 for v in d if v < 0)}/{sum(1 for v in d if v == 0)}')
    for arm in (finalist, against):
        p1 = data[arm][1]
        f = [1 if sev_counts(p1[s])['fatal'] else 0 for s in common if s in p1]
        share = statistics.mean(f)
        fps = statistics.mean(sev_counts(p1[s])['fatal'] for s in common if s in p1)
        mps = statistics.mean(sev_counts(p1[s])['major'] for s in common if s in p1)
        mn = statistics.mean(sev_counts(p1[s])['minor'] for s in common if s in p1)
        sp = os.path.join(OPT, arm, 'summary.json')
        sm = json.load(open(sp)) if os.path.exists(sp) else {}
        print(f"{arm}: fatal share {share:.2f} +- {2 * math.sqrt(share * (1 - share) / len(f)):.2f} | fatal {fps:.2f} "
              f"major {mps:.2f} minor {mn:.2f} /sense | first-pass check {sm.get('first_pass_check', '-')} | "
              f"${sm.get('cost_per_sense', '-')}/sense")
    pf, pa = judge_passes(finalist, proxy), judge_passes(against, proxy)
    if pf and pa and proxy != spec:
        mf, ma = per_sense_means(pf), per_sense_means(pa)
        c2 = [s for s in common if s in mf and s in ma]
        dp = [mf[s] - ma[s] for s in c2]
        print(f'proxy {proxy} on the same {len(c2)} senses: paired difference {statistics.mean(dp):+.2f} +- '
              f'{2 * statistics.pstdev(dp) / math.sqrt(len(c2)):.2f}; judge-vs-proxy gap {statistics.mean(d) - statistics.mean(dp):+.2f}; '
              f'per-sense r({spec}, {proxy}) finalist {fmt(pearson([data[finalist][0][s] for s in c2], [mf[s] for s in c2]))}, '
              f'{against} {fmt(pearson([data[against][0][s] for s in c2], [ma[s] for s in c2]))}')
    print(f'next: --defects {finalist} {against} --judge {spec} ; --loss {finalist} --against {against} --judge {spec}')
    random.seed(0)
    for arm in (finalist, against):
        p1 = data[arm][1]
        pool = [(s, dd) for s in common if s in p1 for dd in p1[s].get('defects', []) if dd.get('severity') == 'fatal']
        random.shuffle(pool)
        picked, seen = [], set()
        for s, dd in pool:  # spread over distinct senses first
            if s not in seen:
                picked.append((s, dd))
                seen.add(s)
            if len(picked) == nfatal:
                break
        for s, dd in pool:
            if len(picked) >= nfatal:
                break
            if (s, dd) not in picked:
                picked.append((s, dd))
        print(f'\n--- {len(picked)} of {len(pool)} {spec} fatals in {arm} (blind read: is each a real fatal?)')
        for i, (s, dd) in enumerate(sorted(picked, key=lambda x: int(x[0])), 1):
            f = glob.glob(os.path.join(OPT, arm, 'r*', 'fat_seed', arm_source(arm), f'{s}.json'))
            doc = json.load(open(f[0])) if f else {}
            print(f"{i:2}. {s} {doc.get('lemma', '')} {dd.get('path')}\n    problem: {(dd.get('problem') or '')[:300]}")
            t = text_at(doc, dd.get('path'))
            if t:
                print(f'    text: {t[:300]}')


def resummarise(arms):
    """Rewrite opt/ARM/summary.json from the existing usage logs, check and judge files (no model calls)."""
    for arm in arms:
        cfg_path = os.path.join(OPT, arm, 'config.json')
        if not os.path.exists(cfg_path):
            print(f'{arm}: no config.json, skipped')
            continue
        cfg = json.load(open(cfg_path))
        runs = sorted(glob.glob(os.path.join(OPT, arm, 'r[0-9]*')))
        s = summarise(arm, runs, arm_source(arm), cfg)
        print(f"{arm}: first-pass check {s['first_pass_check']} | score {s['judge_mean_score']} | ${s['cost_per_sense']}/sense")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('arm', nargs='?')
    ap.add_argument('--author-model', default='sonnet')
    ap.add_argument('--author-effort', default='low')
    ap.add_argument('--review-model', default='opus')
    ap.add_argument('--review-effort', default='medium')
    ap.add_argument('--skip-l1', action='store_true')
    ap.add_argument('--width', type=int, default=0)
    ap.add_argument('--variant-batch', type=int, default=4)
    ap.add_argument('--review-batch', type=int, default=4)
    ap.add_argument('--no-review', action='store_true')
    ap.add_argument('--lint-all', action='store_true', help='A/B overlap lint on every option block')
    ap.add_argument('--cheatsheet', default='', help='alternative RULES_CHEATSHEET for the author')
    ap.add_argument('--chunks', type=int, default=2)
    ap.add_argument('--gold', default='gold', help='gold set directory under opt/ (gold = 23 senses, gold100 = 100)')
    ap.add_argument('--judge-model', default='', help='screening judge model (default: frozen opus/high)')
    ap.add_argument('--judge-effort', default='')
    ap.add_argument('--judge-rubric', type=int, default=0, help='2 (default) or 3')
    ap.add_argument('--author-args', default='', metavar='"FLAGS"',
                    help='extra nt_author.py flags, shlex-split and appended (env NT_AUTHOR_EXTRA_ARGS still works)')
    ap.add_argument('--review-args', default='', metavar='"FLAGS"',
                    help='extra nt_review.py flags, shlex-split and appended, e.g. "--fatal-only --keep-declines"')
    ap.add_argument('--compare', action='store_true')
    # Track C analysis flags (additive)
    ap.add_argument('--passes', action='store_true', help='all arms: mean over all frozen-judge passes + per-pass means')
    ap.add_argument('--defects', nargs='+', metavar='ARM', help='defect classes (block x severity) per sense per arm')
    ap.add_argument('--detail', action='store_true', help='with --defects: group by full path (indexes stripped)')
    ap.add_argument('--fatals', metavar='ARM', help="list one arm's fatal defects with sense ids and problems")
    ap.add_argument('--severity', default='fatal', help='with --fatals: fatal|major|minor|all')
    ap.add_argument('--block', default=None, help='with --fatals: only this block, e.g. level_7')
    ap.add_argument('--reliability', action='store_true', help='judge repeatability for arms with >= 2 passes')
    ap.add_argument('--proxy', metavar='NAME', help='proxy judge NAME (e.g. sonnet-high) vs the frozen judge')
    ap.add_argument('--show', nargs=2, metavar=('ARM', 'SID'), help='document context + all judge defects for one sense')
    ap.add_argument('--path', default=None, help='with --show: focus on this block/path')
    ap.add_argument('--judge', default=None, metavar='SPEC',
                    help="judge spec for the analysis flags, e.g. v2, v3.opus-medium, opus-medium (= v2 proxy); "
                         "default: each arm's own screening judge")
    ap.add_argument('--against', default=None, metavar='SPEC', help='with --proxy: reference judge (default v2); '
                    'with --loss: the reference ARM (default c_base100)')
    ap.add_argument('--loss', metavar='ARM', help='defect classes where ARM loses points vs --against, with examples')
    ap.add_argument('--stale', nargs='*', metavar='ARM', help='staleness audit of judge records vs current documents '
                    '(all arms when no ARM given)')
    ap.add_argument('--resummarise', nargs='+', metavar='ARM', help='rewrite summary.json from existing files')
    ap.add_argument('--confirm', metavar='FINALIST', help='finalist confirmation vs --against (default c_base100) '
                    'under --judge (default v3 = frozen Opus/high, rubric 3): paired diff, fatal shares, proxy, 20 fatals')
    ap.add_argument('--nfatal', type=int, default=10, help='with --confirm: fatals listed per arm')
    ap.add_argument('--top', type=int, default=3, help='with --loss: number of classes to exemplify')
    ap.add_argument('--examples', type=int, default=2, help='with --loss: examples per class')
    args = ap.parse_args()
    if args.compare:
        compare()
        return
    if args.passes:
        passes_table(args.judge)
        return
    if args.defects:
        defects_table(args.defects, args.detail, args.judge)
        return
    if args.fatals:
        list_defects(args.fatals, args.severity, args.block, args.judge)
        return
    if args.reliability:
        reliability(args.judge)
        return
    if args.proxy:
        proxy_report(args.proxy, args.against)
        return
    if args.show:
        show(args.show[0], args.show[1], args.path, args.judge)
        return
    if args.loss:
        loss_report(args.loss, args.against or 'c_base100', args.top, args.examples, args.judge)
        return
    if args.stale is not None:
        stale_report(args.stale or None, args.judge)
        return
    if args.confirm:
        confirm_report(args.confirm, args.against or 'c_base100', args.judge or 'v3', args.nfatal)
        return
    if args.resummarise:
        resummarise(args.resummarise)
        return
    if args.lint_all:
        os.environ['FAT_SEED_LINT_ALL_BLOCKS'] = '1'  # inherited by every runner subprocess
    runs = make_runs(args.arm, args.chunks, os.path.join(OPT, args.gold))
    config = {k: v for k, v in vars(args).items() if k not in ('arm', 'compare', 'chunks')}
    config['author_extra_args'] = os.environ.get('NT_AUTHOR_EXTRA_ARGS', '')  # nt_author.py reads this env var
    json.dump(config, open(os.path.join(OPT, args.arm, 'config.json'), 'w'), indent=1)
    with ThreadPoolExecutor(len(runs)) as ex:
        sources = list(ex.map(lambda r: process(r, args), runs))
    s = summarise(args.arm, runs, sources[0], config)
    print('ARM DONE', json.dumps(s), flush=True)


if __name__ == '__main__':
    main()
