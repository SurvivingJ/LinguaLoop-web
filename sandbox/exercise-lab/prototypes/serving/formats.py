"""
EXPERIMENT 1: multi-selection items as a chance-floor attack.

The live selector's ELO term has an equilibrium at ~-191 points because a
4-option MC item's chance floor c=0.25 means P(correct) never drops below
0.25 no matter how far below the item's difficulty a learner's true ability
sits (docs/recon-serving.md SS4, docs/redteam-serving.md). This module asks:
if the *format* changes so that a single graded event requires several
independent correct selections, how far does that floor move, and does it
actually buy back estimable ability range (not just a lower equilibrium
constant)?

Everything here is closed-form 3PL math plus a Monte Carlo ability-recovery
simulation. No live data, no learner_sim import needed for SS1 (item
statistics) - learner_sim-style simulation is used only for the
items-to-converge experiment below, and is self-contained in this file so
this module has no cross-package dependency.

PARAMETERIZATION (read this before trusting any number below):
We work in "ELO points", the same unit the live selector and
`sec_submission_rpcs_auth_gate.sql`'s first-attempt update use. The base
logistic is the literal ELO expected-score function

    s(x) = 1 / (1 + 10^(-x/400))      x = theta - b, in points

3PL response probability:  P(theta) = c + (1-c) * s(theta - b)
This is NOT an approximation grafted onto ELO - it's the live ELO formula
with a guessing floor spliced in, which is exactly the mechanism
docs/recon-serving.md SS4 and learner_sim.py's docstring describe as the
source of the -191pt cap. Discrimination a=1 (in ELO-point units, a is
absorbed into the /400 scale) throughout; we are not modeling item
discrimination heterogeneity here, only the chance-floor effect - a
deliberate scope cut, stated once here rather than everywhere.
"""
from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass

LN10 = math.log(10)
K = LN10 / 400.0  # natural-log logistic rate equivalent to the /400 ELO base-10 logistic


@dataclass(frozen=True)
class Format:
    name: str
    description: str
    c: float                 # chance floor: P(correct) for a learner with zero relevant ability
    seconds_per_item: float  # stated assumption, not measured - see docs/results-serving.md SS1.5


# ---------------------------------------------------------------------------
# Format catalogue
# ---------------------------------------------------------------------------
# select_all_6: modeled as an uninformed guesser flipping a fair in/out coin
# independently for each of 6 options and being graded all-or-nothing -
# c = 2^-6. This is a stated modeling choice (an uninformed test-taker could
# instead use base-rate priors on how many options are usually correct,
# which would raise their effective floor above this) - the number is a
# lower bound on the achievable chance floor for this format, not a
# measurement.
# ordering_5 / ordering_4: c = 1/n! for a jumbled-token reordering task.
# matching_4: c = 1/4! for a 4-pair matching task (bijection guess).
# cloze3: three independent 4-way blanks scored all-or-nothing, c = 0.25**3.

FORMATS: list[Format] = [
    Format("mc4", "Standard 4-option multiple choice", 0.25, 15.0),
    Format("mc5", "5-option multiple choice", 0.20, 16.0),
    Format("mc6", "6-option multiple choice", 1.0 / 6.0, 17.0),
    Format("select_all_6", "Select-all-that-apply over 6 options, all-or-nothing", 2.0 ** -6, 30.0),
    Format("cloze3", "3-blank cloze, each blank a 4-way choice, all-or-nothing", 0.25 ** 3, 40.0),
    Format("matching_4", "Match 4 pairs (bijection)", 1.0 / math.factorial(4), 35.0),
    Format("ordering_4", "Reorder 4 jumbled tokens", 1.0 / math.factorial(4), 28.0),
    Format("ordering_5", "Reorder 5 jumbled tokens", 1.0 / math.factorial(5), 35.0),
    Format("ordering_6", "Reorder 6 jumbled tokens", 1.0 / math.factorial(6), 42.0),
]


def elo_equilibrium(c: float) -> float:
    """400*log10(1/c - 1): the point-gap at which expected score under the
    live ELO formula equals the format's chance floor - i.e. how far below
    an item's difficulty a learner's *visible* ELO settles and then stops
    moving, because being wrong below this gap yields expected >= actual
    score (E[update] ~ 0) at the floor. Reproduces the documented -191 for
    c=0.25: 400*log10(3) = 400*0.4771 = 190.85."""
    return 400.0 * math.log10(1.0 / c - 1.0)


def p_response(theta_minus_b: float, c: float) -> float:
    s = 1.0 / (1.0 + 10.0 ** (-theta_minus_b / 400.0))
    return c + (1.0 - c) * s


def dp_dtheta(theta_minus_b: float, c: float) -> float:
    s = 1.0 / (1.0 + 10.0 ** (-theta_minus_b / 400.0))
    return (1.0 - c) * K * s * (1.0 - s)


def fisher_info(theta_minus_b: float, c: float) -> float:
    """General (model-free) Fisher information for one binary item:
    I(theta) = P'(theta)^2 / (P(theta)(1-P(theta))). For the 3PL functional
    form used here this is algebraically identical to the textbook closed
    form a^2*[(P-c)/(1-c)]^2*(1-P)/P (Lord 1980) - both are computed and
    cross-checked in tests/test_formats.py so a transcription error in
    either derivation would fail loudly rather than silently."""
    p = p_response(theta_minus_b, c)
    dp = dp_dtheta(theta_minus_b, c)
    denom = p * (1.0 - p)
    if denom <= 0:
        return 0.0
    return (dp * dp) / denom


def fisher_info_closed_form(theta_minus_b: float, c: float) -> float:
    """Textbook 3PL closed form, for cross-checking fisher_info()."""
    p = p_response(theta_minus_b, c)
    a = K  # discrimination in ELO-point units
    if p <= 0 or p >= 1:
        return 0.0
    return (a ** 2) * (((p - c) / (1.0 - c)) ** 2) * ((1.0 - p) / p)


def se_theta(theta_minus_b: float, c: float) -> float:
    info = fisher_info(theta_minus_b, c)
    return float("inf") if info <= 0 else 1.0 / math.sqrt(info)


def estimable_range(c: float, se_threshold: float = 100.0, lo: float = -1200.0,
                     hi: float = 1200.0, step: float = 2.0) -> tuple[float, float, float]:
    """Scans theta-b in [lo, hi] and returns (x_lo, x_hi, width) where
    SE(theta) <= se_threshold holds, i.e. the ability range (relative to
    item difficulty, in ELO points) over which this item's response is
    'estimable'. se_threshold=100 points is a stated design choice: 100
    points is roughly a third of the ADR-024 88-point assigned band, so it
    asks 'can this item resolve differences finer than the band production
    currently assigns a learner to.' Returns (nan, nan, 0.0) if no point in
    range clears the threshold."""
    xs = []
    x = lo
    while x <= hi:
        if se_theta(x, c) <= se_threshold:
            xs.append(x)
        x += step
    if not xs:
        return (float("nan"), float("nan"), 0.0)
    return (min(xs), max(xs), max(xs) - min(xs))


# ---------------------------------------------------------------------------
# Ability recovery: items-to-converge per format
# ---------------------------------------------------------------------------

def _log_likelihood(theta: float, responses: list[tuple[float, bool]], c: float) -> float:
    ll = 0.0
    for b, correct in responses:
        p = p_response(theta - b, c)
        p = min(max(p, 1e-9), 1 - 1e-9)
        ll += math.log(p) if correct else math.log(1 - p)
    return ll


_GOLDEN = (math.sqrt(5.0) - 1.0) / 2.0  # ~0.618


def _mle_theta(responses: list[tuple[float, bool]], c: float, lo: float = -800.0,
               hi: float = 2400.0, tol: float = 1.0) -> float:
    """MLE ability estimate given a fixed set of (b, correct) responses, via
    golden-section search on the log-likelihood (unimodal/concave in theta
    for a 3PL with fixed c) rather than a fixed-step grid - same guarantee
    (never diverges/oscillates the way Newton-Raphson can near the flat,
    low-information region below the guessing floor) at ~5x fewer
    likelihood evaluations per call, which matters here because this is
    called once per item per learner per format in the convergence
    experiment below."""
    a, b_ = lo, hi
    c1 = b_ - _GOLDEN * (b_ - a)
    c2 = a + _GOLDEN * (b_ - a)
    f1 = _log_likelihood(c1, responses, c)
    f2 = _log_likelihood(c2, responses, c)
    while (b_ - a) > tol:
        if f1 < f2:
            a, c1, f1 = c1, c2, f2
            c2 = a + _GOLDEN * (b_ - a)
            f2 = _log_likelihood(c2, responses, c)
        else:
            b_, c2, f2 = c2, c1, f1
            c1 = b_ - _GOLDEN * (b_ - a)
            f1 = _log_likelihood(c1, responses, c)
    return (a + b_) / 2.0


def items_to_converge(c: float, true_theta: float, *, start_theta: float = 1200.0,
                       tolerance: float = 50.0, max_items: int = 60,
                       rng: random.Random | None = None) -> int | None:
    """Adaptive test: each item's difficulty b is set to the CURRENT theta
    estimate (mirrors the live nearest-ELO rule), the learner responds via
    the 3PL model at true_theta, and theta-hat is re-estimated by MLE over
    the full response history so far. Returns the first item count N such
    that |theta_hat - true_theta| <= tolerance for every item count from N
    through max_items (a "stays converged" criterion, not a lucky single
    hit) - or None if it never stabilizes within max_items."""
    rng = rng or random.Random()
    responses: list[tuple[float, bool]] = []
    theta_hat = start_theta
    estimates: list[float] = []
    for _ in range(max_items):
        b = theta_hat
        p = p_response(true_theta - b, c)
        correct = rng.random() < p
        responses.append((b, correct))
        theta_hat = _mle_theta(responses, c)
        estimates.append(theta_hat)
    for i in range(len(estimates)):
        if all(abs(e - true_theta) <= tolerance for e in estimates[i:]):
            return i + 1
    return None


def run_convergence_experiment(formats: list[Format] | None = None, *, n_learners: int = 80,
                                true_spread_halfwidth: float = 224.0, seed: int = 7,
                                tolerance: float = 50.0, max_items: int = 40) -> dict:
    """Headline result: for each format, draw n_learners true abilities
    uniformly across a 2*true_spread_halfwidth point spread (448 points
    total, matching ADR-024's real figure - see
    wiki/decisions/ADR-024-vocabulary-aware-test-selection.md lines 24-26)
    centered on the live cold-start default (1200, i.e. inside the
    documented 88-point assigned band 1182-1270), and measure items-to-
    converge within `tolerance` points. Reports median/p25/p75 and the
    non-convergence rate, plus the same numbers converted to minutes using
    each format's stated seconds_per_item, and an info-per-minute score."""
    formats = formats or FORMATS
    rng = random.Random(seed)
    true_thetas = [1200.0 + rng.uniform(-true_spread_halfwidth, true_spread_halfwidth)
                   for _ in range(n_learners)]
    results = {}
    for fmt in formats:
        counts = []
        n_failed = 0
        for i, theta in enumerate(true_thetas):
            n = items_to_converge(fmt.c, theta, tolerance=tolerance, max_items=max_items,
                                   rng=random.Random(seed * 100003 + i))
            if n is None:
                n_failed += 1
            else:
                counts.append(n)
        if counts:
            counts_sorted = sorted(counts)
            median_n = statistics.median(counts_sorted)
            p25 = counts_sorted[int(0.25 * (len(counts_sorted) - 1))]
            p75 = counts_sorted[int(0.75 * (len(counts_sorted) - 1))]
        else:
            median_n = p25 = p75 = float("nan")
        results[fmt.name] = {
            "c": fmt.c,
            "seconds_per_item": fmt.seconds_per_item,
            "n_converged": len(counts),
            "n_total": n_learners,
            "non_convergence_rate": n_failed / n_learners,
            "median_items": median_n,
            "p25_items": p25,
            "p75_items": p75,
            "median_minutes": (median_n * fmt.seconds_per_item / 60.0
                                if not math.isnan(median_n) else float("nan")),
            "elo_equilibrium_points": elo_equilibrium(fmt.c),
        }
        est_lo, est_hi, est_width = estimable_range(fmt.c)
        results[fmt.name]["estimable_range_points"] = est_width
        results[fmt.name]["estimable_lo_relative_to_b"] = est_lo
        results[fmt.name]["estimable_hi_relative_to_b"] = est_hi
        if not math.isnan(median_n) and median_n > 0:
            results[fmt.name]["info_per_minute_relative"] = 1.0 / results[fmt.name]["median_minutes"]
        else:
            results[fmt.name]["info_per_minute_relative"] = 0.0
    return results


if __name__ == "__main__":
    import json
    res = run_convergence_experiment()
    print(json.dumps(res, indent=2))
