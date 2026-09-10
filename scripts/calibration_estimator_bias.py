#!/usr/bin/env python3
"""Measure the bias of calibration_ability() against a known ground truth.

Why this exists
---------------
`ability_zipf_85` is the statistic ADR-024 §1.2 wants, and the wiki log
records that its *definition* alone swings the derived ELO by 430 points. A
statistic that sensitive cannot be shipped on the assumption that the estimator
is unbiased — it has to be measured against a learner whose true ability is known,
which is impossible with real users and trivial with a simulated one.

Two simulated learners, and the difference between them is the point:

* ``--learner step`` (default) knows everything at or above a Zipf threshold and
  guesses at 0.25 below it. Its true 85% crossing is exactly the threshold. This
  is an ADVERSARIAL case — an infinitely sharp step cannot be represented by a
  finite-slope logistic — so it bounds the error rather than predicting it.
* ``--learner logistic`` has a gradual knowledge curve, which is what a real
  learner looks like and what the estimator actually models. Here the model is
  correctly specified, so any residual error is the estimator's own.

Reporting only the step case would overstate the error; reporting only the
logistic case would hide the model-mismatch bound. Both are below.

Live run, ``--learner logistic --items 120``, 2026-09-08: mean err85 **+0.029**,
mean err50 +0.046.

BEFORE TASK-764 - piecewise-linear interpolation between band midpoints
(84 items per trial, ja/en, 2026-09-08):

    true    z85   err85     z50   err50
    3.30  3.450   +0.15   3.000   -0.30
    3.80  3.950   +0.15   3.375   -0.42
    4.30  4.600   +0.30   4.250   -0.05
    4.80  5.100   +0.30   4.750   -0.05
    5.30  5.621   +0.32   5.321   +0.02

Biased HIGH in every trial, mean ~+0.24 Zipf. A discretization artifact, not a
guessing one: for a step learner the 0.25 guess floor cancels out of the crossing
exactly, but interpolating between the midpoints of 0.5-wide bands cannot resolve
a step that falls *inside* a band, and interpolating up to a high target lands late.

AFTER TASK-764 - maximum-likelihood logistic fit on raw responses, with the guess
floor fixed at 0.25 (same trials, --learner step):

    true    z85   err85     z50   err50
    3.30  3.403   +0.10   3.312   +0.01
    3.80  3.874   +0.07   3.782   -0.02
    4.30  4.416   +0.12   4.324   +0.02
    4.80  4.849   +0.05   4.758   -0.04
    5.30  5.379   +0.08   5.287   -0.01

    mean err85 = +0.084   mean err50 = -0.008

Roughly a 3x improvement, and err50 is now essentially unbiased. The residual
+0.08 on err85 is **model mismatch, not estimator bias**: the simulated learner is
an infinitely sharp step, which a finite-slope logistic cannot represent, so the
fitted slope stays finite and z85 = midpoint + logit(0.85)/slope sits slightly
above the step. Against a correctly specified learner (--learner logistic) the fit
is unbiased - mean error -0.028 over 15 trials. Real learners have gradual
knowledge curves, so the step case is an adversarial bound, not the expected error.

PRECISION IS NOW THE BINDING CONSTRAINT, NOT BIAS. 60 logistic learners per row:

    items    bias      sd   p90|err|
       20  -0.118   0.631      0.95
       40  -0.053   0.416      0.57
       60  -0.035   0.270      0.43
       84  -0.040   0.238      0.39
      120  -0.044   0.157      0.26
      200  -0.002   0.156      0.26
      300  -0.051   0.109      0.20

Bias is negligible everywhere; the standard error is what limits usefulness. This
table is the source for `calibration_service.expected_sd()` and for the confidence
labels, which are now read off measured precision rather than guessed from an item
count. For ADR-024, whose Zipf->ELO map swings 430 points across plausible
definitions, a 60-item run still carries +-0.27 Zipf - read `ability_zipf_85_sd`
and propagate it rather than treating the point estimate as exact.

Usage::

    PYTHONIOENCODING=utf-8 python -m scripts.calibration_estimator_bias
    PYTHONIOENCODING=utf-8 python -m scripts.calibration_estimator_bias --items 120
"""

from __future__ import annotations

import argparse
import math
import os
import random
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

#: Chance of a correct answer below the learner's threshold. Four options, so a
#: pure guess is 1-in-4. Must stay in step with
#: services.calibration_service.OPTIONS_PER_ITEM.
GUESS_RATE = 0.25


def _answers_correctly(zipf: float, threshold: float, learner: str,
                       slope: float) -> bool:
    """Did the simulated learner get this item right?"""
    if learner == 'logistic':
        knowledge = 1.0 / (1.0 + math.exp(-slope * (zipf - threshold)))
    else:
        knowledge = 1.0 if zipf >= threshold else 0.0
    return random.random() < (GUESS_RATE + (1.0 - GUESS_RATE) * knowledge)


def run_trial(cs, db, threshold: float, items: int, seed: int,
              word_lang: int, def_lang: int, learner: str = 'step',
              slope: float = 3.0) -> dict:
    """One simulated learner. Returns the estimator's output."""
    user_id = str(uuid.uuid4())
    session = cs.start_session(user_id, word_lang, def_lang)
    random.seed(seed)

    try:
        for _ in range(items):
            try:
                item = cs.next_item(user_id, session)
            except cs.CalibrationError:
                continue
            if item is None:
                break

            row = (db.table('calibration_responses')
                     .select('anchor_zipf')
                     .eq('id', item['response_id']).limit(1).execute().data[0])
            zipf = row['anchor_zipf'] or 0.0

            opts = (db.table('calibration_response_options')
                      .select('position, is_key')
                      .eq('response_id', item['response_id']).execute().data)
            key_pos = next(o['position'] for o in opts if o['is_key'])
            wrong = [o['position'] for o in opts if not o['is_key']]

            correct = _answers_correctly(zipf, threshold, learner, slope)
            pos = key_pos if correct else random.choice(wrong)
            cs.record_answer(user_id, session, item['response_id'], pos, latency_ms=1000)

        return cs.ability(user_id, session)
    finally:
        # Synthetic sessions must never pollute real calibration data.
        db.table('calibration_sessions').delete().eq('id', session['id']).execute()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--items', type=int, default=84)
    ap.add_argument('--word-language', type=int, default=3)
    ap.add_argument('--definition-language', type=int, default=2)
    ap.add_argument('--thresholds', type=float, nargs='+',
                    default=[3.30, 3.80, 4.30, 4.80, 5.30])
    ap.add_argument('--learner', choices=['step', 'logistic'], default='step',
                    help='step: knows everything above the threshold - adversarial, '
                         'unrepresentable by a finite-slope logistic. logistic: a '
                         'realistic gradual curve, where the model is correctly '
                         'specified and the fit should be unbiased.')
    ap.add_argument('--slope', type=float, default=3.0,
                    help='knowledge-curve steepness for --learner logistic')
    args = ap.parse_args()

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    SupabaseFactory.initialize()
    db = get_supabase_admin()
    from services import calibration_service as cs

    print(f"{'true':>6} {'z85':>8} {'err85':>7} {'z50':>8} {'err50':>7}  known-share by band")
    errors_85, errors_50 = [], []

    for seed, threshold in enumerate(args.thresholds, start=1):
        ability = run_trial(cs, db, threshold, args.items, seed,
                            args.word_language, args.definition_language,
                            args.learner, args.slope)
        z85, z50 = ability.get('ability_zipf_85'), ability.get('ability_zipf_50')

        # For a logistic learner the true 85%-knowledge point is not the
        # threshold itself (that is the 50% point) but logit(0.85)/slope above it.
        true_85 = threshold + (math.log(0.85 / 0.15) / args.slope
                               if args.learner == 'logistic' else 0.0)
        e85 = f'{z85 - true_85:+.2f}' if z85 is not None else '  n/a'
        e50 = f'{z50 - threshold:+.2f}' if z50 is not None else '  n/a'
        if z85 is not None:
            errors_85.append(z85 - true_85)
        if z50 is not None:
            errors_50.append(z50 - threshold)

        bands = ''.join(f"{int(round(b['known_share'] * 100)):>4}"
                        for b in ability.get('bands', []))
        print(f"{threshold:>6.2f} {(f'{z85:.3f}' if z85 is not None else 'None'):>8} {e85:>7} "
              f"{(f'{z50:.3f}' if z50 is not None else 'None'):>8} {e50:>7}  {bands}")

    if errors_85:
        print(f"\nmean err85 = {sum(errors_85)/len(errors_85):+.3f} "
              f"(min {min(errors_85):+.2f}, max {max(errors_85):+.2f})")
    if errors_50:
        print(f"mean err50 = {sum(errors_50)/len(errors_50):+.3f} "
              f"(min {min(errors_50):+.2f}, max {max(errors_50):+.2f})")


if __name__ == '__main__':
    main()
