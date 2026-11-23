"""Coverage of the displayed interval (knowledge-report tech §2.6 simulation grid). Slow: run with -m slow.

Synthetic learners draw n words per band without replacement from the frame, answer known words right,
skip unknown ones with probability sigma and otherwise guess (1 in 4). The displayed range, or the
one-sided bound, must contain the true count in ≥ 93% of shown outputs, with no zero-width output."""
import random
import zlib

import pytest

from services.vocabulary import knowledge_estimate as ke

FRAME_JA = [577, 425, 621, 655, 537, 283, 77]
FRAME_ZH = [303, 617, 742, 691, 664, 435, 171]
ZH_BEGINNER = [0, 0, 0, .01, .03, .15, .5]
CASES = [
    ('ja de6fd05b-like', [.222, .222, .308, .333, .48, .59, .897], 0.6, FRAME_JA),
    ('ja advanced, no skips', [.5, .6, .75, .85, .92, .97, .99], 0.0, FRAME_JA),
    ('ja near-ceiling, no skips', [.9, .95, .97, .98, .99, 1, 1], 0.0, FRAME_JA),
    ('zh beginner, never skips', ZH_BEGINNER, 0.0, FRAME_ZH),
    ('zh beginner, honest skips', ZH_BEGINNER, 1.0, FRAME_ZH),
    ('zh intermediate, some skips', [.1, .15, .25, .4, .6, .8, .95], 0.5, FRAME_ZH),
]
REPS = 3000


def _simulate(profile, sigma, n, frame, seed):
    rng = random.Random(seed)
    known = [int(round(p * N)) for p, N in zip(profile, frame)]
    truth = sum(known)
    covered = shown = zero_width = 0
    for _ in range(REPS):
        bands = []
        for k, N in zip(known, frame):
            c = s = 0
            for i in rng.sample(range(N), min(n, N)):
                if i < k:
                    c += 1
                elif rng.random() < sigma:
                    s += 1
                elif rng.random() < ke.G:
                    c += 1
            bands.append([min(n, N), s, c])
        e = ke.estimate_range(bands, frame)
        if not e['shown']:
            continue
        shown += 1
        lo = 0.0 if e['kind'] == 'upper_only' else e['lo']
        covered += lo <= truth <= e['hi']
        zero_width += (e['hi'] - lo) < 1
    return shown, covered, zero_width


@pytest.mark.slow
@pytest.mark.parametrize('n', [10, 20, 30])
@pytest.mark.parametrize('name,profile,sigma,frame', CASES, ids=[c[0] for c in CASES])
def test_coverage_grid(name, profile, sigma, frame, n):
    shown, covered, zero_width = _simulate(profile, sigma, n, frame, seed=zlib.crc32(f'{name}/{n}'.encode()))
    assert shown == REPS, f'{name} n={n}: {REPS - shown} runs gave no estimate'
    assert covered / shown >= 0.93, f'{name} n={n}: coverage {covered / shown:.3f}'
    assert zero_width == 0
