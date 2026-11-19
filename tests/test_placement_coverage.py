"""V0 (vocab-placement tech §20; TASK-1087): the production placement rules on synthetic learners.

Slow: python -m pytest tests/test_placement_coverage.py -q -m slow. Prints a summary table (-s)."""
import random
import zlib
from statistics import mean

import pytest

from services import placement_design as pd
from tests import placement_sim_model as sm

N_PER_CELL = 600          # per IDK level: the bias SE is then ≈ 0.25% of the pool
POPS = [('zh', 'en'), ('zh', 'ja'), ('ja', 'en'), ('ja', 'zh'), ('en', 'en')]
SKIPS = (0.3, 0.7)


def _cell(lang, l1, skip, *, stop_at=None, n=N_PER_CELL):
    rng = random.Random(zlib.crc32(f'{lang}/{l1}/{skip}/{stop_at}'.encode()))
    pool = sm.build_pool(sm.LANG_IDS[lang], rng)
    rows = []
    for _ in range(n):
        L = sm.make_learner(lang, l1, skip, pool, rng)
        t = sm.truths(L, pool)
        r = sm.run_placement(L, pool, rng, stop_at=stop_at)
        r['truth'] = t
        rows.append(r)
    return rows


def _summ(rows, lang):
    N = sum(sm.FRAMES[sm.LANG_IDS[lang]])
    out = dict(items=mean(r['scored'] for r in rows), minutes=mean(r['minutes'] for r in rows),
               early=mean(r['reason'] == 'precision' for r in rows))
    for key, tkey in (('m', 'm'), ('mr', 'mr'), ('reading_gap', 'gap'), ('tone_gap', 'tone_gap')):
        cov, bias = [], []
        for r in rows:
            e = r['est'].get(key)
            if not e:
                continue
            if key.endswith('gap'):
                cov.append(e['lo'] <= r['truth'][tkey] <= e['hi'])
                bias.append((e['G'] - r['truth'][tkey]) / N)
                continue
            c = sm.covers(e, r['truth'][tkey])
            if c is not None:
                cov.append(c)
                bias.append((e['T'] - r['truth'][tkey]) / N)
        out[key] = (mean(cov) if cov else None, mean(bias) if bias else None, len(cov))
    return out


@pytest.mark.slow
@pytest.mark.parametrize('lang,l1', POPS, ids=[f'{a}-{b}' for a, b in POPS])
def test_v0_full_placements(lang, l1):
    rows = []
    for skip in SKIPS:
        rows += _cell(lang, l1, skip)
    s = _summ(rows, lang)
    print(f"\nV0 {lang}·{l1}: items {s['items']:.1f}, min {s['minutes']:.1f}, early {s['early']:.0%}; "
          + '; '.join(f"{k} cover {v[0]:.3f} bias {v[1]:+.4f} (n {v[2]})" for k, v in s.items()
                      if isinstance(v, tuple) and v[0] is not None))
    assert all(r['eligible'] for r in rows)
    m_cov, m_bias, _ = s['m']
    assert m_cov >= 0.90 and abs(m_bias) <= 0.015
    if lang == 'en':
        assert s['items'] <= 40
        return
    assert 53 <= s['items'] <= 61          # E31/E33 give 56.4–60.4; this model stops English-L1 beginners earlier
    mr_cov, mr_bias, _ = s['mr']
    assert mr_cov >= 0.90 and abs(mr_bias) <= 0.015
    g_cov, _, g_n = s['reading_gap']
    assert g_n and g_cov >= 0.90
    if lang == 'zh':
        t_cov, _, t_n = s['tone_gap']
        assert t_n and t_cov >= 0.90


@pytest.mark.slow
@pytest.mark.parametrize('stop_at', [20, 30])
@pytest.mark.parametrize('lang,l1', [('zh', 'en'), ('ja', 'zh')], ids=['zh-en', 'ja-zh'])
def test_v0_end_now(lang, l1, stop_at):
    rows = _cell(lang, l1, 0.5, stop_at=stop_at, n=200)
    s = _summ(rows, lang)
    assert all(r['eligible'] for r in rows)
    assert s['m'][0] >= 0.88 and s['mr'][0] >= 0.88
