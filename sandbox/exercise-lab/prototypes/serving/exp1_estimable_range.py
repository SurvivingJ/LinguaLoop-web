"""
EXPERIMENT 1(a) follow-up: single-item Fisher information (as computed by
formats.py's estimable_range()) turns out to be too small, for every
format, to clear ANY SE(theta) threshold worth stating - see the note
below. This script computes the ability range estimable after ACCUMULATING
information across N independently-administered items (all at the same
b=0, a=1 ELO-point parameterization formats.py uses), which is the
comparison that actually matters given the established finding that item
calibration is hard-gated at DEFAULT_MIN_ATTEMPTS=20.

Why single-item SE never clears a useful threshold, in one line: max
single-item Fisher information (at P=0.5, c=0) is a^2*0.25 with
a = ln(10)/400 = 0.005756 (the ELO-point-unit discrimination formats.py
uses throughout) -> I_max = 8.29e-6 -> SE_min = 1/sqrt(I_max) = 347.6
points. No single MC-shaped item, at any chance floor, can ever resolve
theta to inside +-350 points let alone +-100. This is exactly the
"I(theta) accumulates too slowly, not just biased toward 0" restatement of
the redteam's SS2 point, quantified.

We also translate the prompt's literal "SE(theta) <= 0.3" criterion (stated
in dimensionless logit units, the standard IRT convention) into this file's
ELO-point parameterization: 1 logit-theta unit = 400/ln(10) = 173.7 ELO
points (since the ELO logistic s(y)=1/(1+10^(-y/400)) and the standard
logistic s(x)=1/(1+e^-x) coincide at x = y*ln(10)/400). So
SE(theta_logit) <= 0.3  <=>  SE(theta_points) <= 0.3 * 400/ln(10) = 52.1 points.
"""
from __future__ import annotations

import json
import math

from formats import FORMATS, fisher_info

SE_THRESHOLD_LOGIT = 0.3
POINTS_PER_LOGIT = 400.0 / math.log(10.0)
SE_THRESHOLD_POINTS = SE_THRESHOLD_LOGIT * POINTS_PER_LOGIT  # ~52.1


def accumulated_estimable_range(c: float, n_items: int, se_threshold_points: float,
                                 lo: float = -1200.0, hi: float = 1200.0, step: float = 4.0):
    """All N items assumed administered at the SAME b=0 (worst case for an
    adaptive test that hasn't moved yet; a real adaptive test that re-aims
    each item at the running theta-hat does better - that's what
    items_to_converge() in formats.py measures empirically). Information
    accumulates additively across independent items: I_N(theta) = N * I_1(theta)."""
    xs = []
    x = lo
    while x <= hi:
        info_n = n_items * fisher_info(x, c)
        se = float("inf") if info_n <= 0 else 1.0 / math.sqrt(info_n)
        if se <= se_threshold_points:
            xs.append(x)
        x += step
    if not xs:
        return None
    return (min(xs), max(xs), max(xs) - min(xs))


if __name__ == "__main__":
    print(f"# SE(theta_logit)<=0.3  <=>  SE(theta_points)<={SE_THRESHOLD_POINTS:.1f}")
    print(f"# single-item SE_min (any format, at P=0.5) = {1.0/math.sqrt(8.288e-6):.1f} points\n")
    out = {}
    for n_items in (1, 20, 50):
        out[n_items] = {}
        for fmt in FORMATS:
            r = accumulated_estimable_range(fmt.c, n_items, SE_THRESHOLD_POINTS)
            out[n_items][fmt.name] = {
                "c": round(fmt.c, 6),
                "estimable_width_points": None if r is None else round(r[2], 1),
                "estimable_range": None if r is None else (round(r[0], 1), round(r[1], 1)),
            }
    print(json.dumps(out, indent=2))
