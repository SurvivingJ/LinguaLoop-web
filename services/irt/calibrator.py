"""
IRT 2PL calibration job.

Fits per-exercise difficulty (b) and discrimination (a) from accumulated
first-attempt responses in `user_exercise_history`, then UPDATEs
`exercises.irt_difficulty`, `irt_discrimination`, `irt_n_attempts`,
`irt_se_difficulty`, `irt_calibrated_at`.

Model: P(correct | theta) = sigmoid(a * (theta - b))
Theta per user: logit of overall first-attempt accuracy in the language,
clipped to [0.05, 0.95] before the logit so a perfect or all-wrong user
doesn't produce an infinite theta.

Triggered manually via /admin/api/calibrate-irt and nightly via APScheduler
(see app.py). Both call into `calibrate_language(language_id)`. A Postgres
advisory lock guards against duplicate concurrent runs across gunicorn
workers.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from typing import Iterable

import numpy as np
from scipy.optimize import minimize

logger = logging.getLogger(__name__)

# Bayesian shrinkage toward the tier-seeded `b_seed` at small N. With k=10,
# an exercise with n=20 attempts blends 2:1 fitted-vs-seed; n=100 blends
# 10:1 (essentially the fit). Keeps newly-eligible exercises from swinging
# violently on one lucky cohort.
PRIOR_PSEUDOCOUNT = 10

# 2PL parameter clamps. Outside these ranges the optimiser is almost
# certainly chasing noise, not signal.
A_MIN, A_MAX = 0.3, 3.0
B_MIN, B_MAX = -3.0, 3.0

# Theta clamps for the per-user logit. A user with 0% or 100% accuracy
# would otherwise produce ±inf and break the optimiser.
THETA_P_MIN, THETA_P_MAX = 0.05, 0.95

DEFAULT_MIN_ATTEMPTS = 20
DEFAULT_BATCH_SIZE = 1000  # supabase-py pagination page size


# ---------------------------------------------------------------------------
# 2PL fitter
# ---------------------------------------------------------------------------

def _neg_log_likelihood(params: np.ndarray, theta: np.ndarray, y: np.ndarray) -> float:
    a, b = params
    z = a * (theta - b)
    log_p = -np.logaddexp(0.0, -z)
    log_1mp = -np.logaddexp(0.0, z)
    return float(-(y * log_p + (1 - y) * log_1mp).sum())


def _neg_log_likelihood_grad(params: np.ndarray, theta: np.ndarray, y: np.ndarray) -> np.ndarray:
    a, b = params
    p = 1.0 / (1.0 + np.exp(-a * (theta - b)))
    diff = y - p
    da = -(diff * (theta - b)).sum()
    db = -(diff * (-a)).sum()
    return np.array([da, db])


def fit_2pl(
    theta: np.ndarray,
    y: np.ndarray,
    b_seed: float,
) -> tuple[float, float, float]:
    """Fit (a, b) on a single exercise's observations.

    Returns (a, b, se_b). se_b is from the inverse Hessian diagonal at the
    optimum; NaN if the Hessian couldn't be inverted (rare; flagged by
    callers as a low-confidence calibration).
    """
    x0 = np.array([1.0, b_seed], dtype=float)
    result = minimize(
        _neg_log_likelihood,
        x0,
        args=(theta, y),
        jac=_neg_log_likelihood_grad,
        method='L-BFGS-B',
        bounds=[(A_MIN, A_MAX), (B_MIN, B_MAX)],
    )
    a_fit, b_fit = float(result.x[0]), float(result.x[1])

    se_b = float('nan')
    try:
        p = 1.0 / (1.0 + np.exp(-a_fit * (theta - b_fit)))
        w = p * (1.0 - p)
        # Hessian of the negative log-likelihood for 2PL.
        h_aa = (w * (theta - b_fit) ** 2).sum()
        h_bb = (w * a_fit ** 2).sum()
        h_ab = -(w * a_fit * (theta - b_fit)).sum() + (((y - p)) * 1.0).sum() * 0.0
        det = h_aa * h_bb - h_ab * h_ab
        if det > 0:
            var_b = h_aa / det
            if var_b > 0:
                se_b = float(math.sqrt(var_b))
    except (ValueError, FloatingPointError):
        pass

    return a_fit, b_fit, se_b


def apply_prior(b_fit: float, b_seed: float, n: int, k: int = PRIOR_PSEUDOCOUNT) -> float:
    """Shrink the fitted difficulty toward the seeded value at small N."""
    return (n * b_fit + k * b_seed) / (n + k)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_first_attempts(db, language_id: int) -> list[dict]:
    """Page through user_exercise_history first-attempt rows for a language."""
    rows: list[dict] = []
    offset = 0
    while True:
        page = (
            db.table('user_exercise_history')
            .select('user_id, exercise_id, is_correct')
            .eq('language_id', language_id)
            .eq('is_first_attempt', True)
            .range(offset, offset + DEFAULT_BATCH_SIZE - 1)
            .execute()
            .data or []
        )
        rows.extend(page)
        if len(page) < DEFAULT_BATCH_SIZE:
            break
        offset += DEFAULT_BATCH_SIZE
    return rows


def _load_exercise_seeds(db, exercise_ids: Iterable[str]) -> dict[str, float]:
    """Fetch tier-seeded irt_difficulty for the exercises we're about to fit."""
    seeds: dict[str, float] = {}
    ids = list(exercise_ids)
    for i in range(0, len(ids), DEFAULT_BATCH_SIZE):
        chunk = ids[i:i + DEFAULT_BATCH_SIZE]
        page = (
            db.table('exercises')
            .select('id, irt_difficulty')
            .in_('id', chunk)
            .execute()
            .data or []
        )
        for r in page:
            seeds[r['id']] = float(r.get('irt_difficulty') or 0.0)
    return seeds


# ---------------------------------------------------------------------------
# Theta
# ---------------------------------------------------------------------------

def compute_user_thetas(rows: list[dict]) -> dict[str, float]:
    """Logit of clipped first-attempt accuracy, per user."""
    correct_by_user: dict[str, int] = defaultdict(int)
    total_by_user: dict[str, int] = defaultdict(int)
    for r in rows:
        uid = r['user_id']
        total_by_user[uid] += 1
        if r['is_correct']:
            correct_by_user[uid] += 1

    thetas: dict[str, float] = {}
    for uid, n in total_by_user.items():
        p = correct_by_user[uid] / n
        p = min(max(p, THETA_P_MIN), THETA_P_MAX)
        thetas[uid] = math.log(p / (1.0 - p))
    return thetas


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _persist_calibration(
    db,
    exercise_id: str,
    a: float,
    b: float,
    se_b: float,
    n: int,
) -> None:
    db.rpc('irt_apply_calibration', {
        'p_exercise_id':    exercise_id,
        'p_discrimination': round(a, 3),
        'p_difficulty':     round(b, 3),
        'p_se_difficulty':  None if math.isnan(se_b) else round(se_b, 3),
        'p_n_attempts':     n,
    }).execute()


# ---------------------------------------------------------------------------
# Advisory lock
# ---------------------------------------------------------------------------

def _try_advisory_lock(db) -> bool:
    """Best-effort cross-worker mutex. Falls through to True if the call
    fails (e.g. lock RPC not yet deployed), so a misconfigured environment
    doesn't block manual admin triggers.
    """
    try:
        resp = db.rpc('irt_try_lock', {}).execute()
        data = resp.data
        if isinstance(data, list) and data:
            return bool(data[0])
        return bool(data)
    except Exception as exc:
        logger.warning("Advisory lock unavailable, proceeding without it: %s", exc)
        return True


def _release_advisory_lock(db) -> None:
    try:
        db.rpc('irt_release_lock', {}).execute()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public entrypoints
# ---------------------------------------------------------------------------

def calibrate_language(
    language_id: int,
    min_attempts: int = DEFAULT_MIN_ATTEMPTS,
    db=None,
) -> dict:
    """Fit IRT parameters for every exercise in `language_id` with
    ≥ `min_attempts` first-attempt observations.

    Returns a summary dict {fitted, skipped_low_n, failed, language_id}.
    """
    if db is None:
        from services.supabase_factory import get_supabase_admin
        db = get_supabase_admin()

    logger.info("IRT calibration starting for language_id=%s (min_attempts=%d)",
                language_id, min_attempts)

    rows = _load_first_attempts(db, language_id)
    logger.info("Loaded %d first-attempt rows", len(rows))

    if not rows:
        logger.info("No data — nothing to calibrate.")
        return {'language_id': language_id, 'fitted': 0, 'skipped_low_n': 0, 'failed': 0}

    thetas = compute_user_thetas(rows)
    logger.info("Computed theta for %d users", len(thetas))

    # Bucket observations by exercise.
    obs_by_exercise: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for r in rows:
        uid = r['user_id']
        eid = r['exercise_id']
        if uid not in thetas:
            continue
        obs_by_exercise[eid].append((thetas[uid], 1 if r['is_correct'] else 0))

    eligible = [eid for eid, obs in obs_by_exercise.items() if len(obs) >= min_attempts]
    logger.info("%d exercises have ≥ %d attempts (skipping %d)",
                len(eligible), min_attempts,
                len(obs_by_exercise) - len(eligible))

    if not eligible:
        return {
            'language_id': language_id,
            'fitted': 0,
            'skipped_low_n': len(obs_by_exercise),
            'failed': 0,
        }

    seeds = _load_exercise_seeds(db, eligible)

    fitted = 0
    failed = 0
    for eid in eligible:
        obs = obs_by_exercise[eid]
        theta_arr = np.array([o[0] for o in obs], dtype=float)
        y_arr = np.array([o[1] for o in obs], dtype=float)
        b_seed = seeds.get(eid, 0.0)
        n = len(obs)

        try:
            a, b_fit, se_b = fit_2pl(theta_arr, y_arr, b_seed)
        except Exception as exc:
            logger.error("Fit failed for exercise %s: %s", eid, exc)
            failed += 1
            continue

        b_post = apply_prior(b_fit, b_seed, n)
        b_post = min(max(b_post, B_MIN), B_MAX)

        try:
            _persist_calibration(db, eid, a, b_post, se_b, n)
            fitted += 1
        except Exception as exc:
            logger.error("Persist failed for exercise %s: %s", eid, exc)
            failed += 1

        if fitted % 50 == 0 and fitted:
            logger.info("Progress: %d / %d fitted", fitted, len(eligible))

    logger.info("IRT calibration complete for language_id=%s: fitted=%d failed=%d",
                language_id, fitted, failed)

    return {
        'language_id': language_id,
        'fitted': fitted,
        'skipped_low_n': len(obs_by_exercise) - len(eligible),
        'failed': failed,
    }


def calibrate_all_active_languages(min_attempts: int = DEFAULT_MIN_ATTEMPTS) -> list[dict]:
    """Nightly entrypoint — calibrate every active language in dim_languages.

    Guarded by a Postgres advisory lock so only one gunicorn worker runs
    the full sweep at a time.
    """
    from services.supabase_factory import get_supabase_admin
    db = get_supabase_admin()

    if not _try_advisory_lock(db):
        logger.info("Another worker holds the IRT calibration lock; skipping.")
        return []

    try:
        langs = (
            db.table('dim_languages')
            .select('id, language_name')
            .eq('is_active', True)
            .execute()
            .data or []
        )
        summaries = []
        for lang in langs:
            try:
                summary = calibrate_language(int(lang['id']), min_attempts=min_attempts, db=db)
                summary['language_name'] = lang.get('language_name')
                summaries.append(summary)
            except Exception as exc:
                logger.exception("Calibration failed for language %s: %s", lang, exc)
                summaries.append({
                    'language_id': lang.get('id'),
                    'language_name': lang.get('language_name'),
                    'error': str(exc),
                })
        return summaries
    finally:
        _release_advisory_lock(db)


def compute_user_theta_for_selection(db, user_id: str, language_id: int) -> float:
    """Real-time theta used by get_exercise_session for IRT weighting.

    Delegates to the SQL helper `irt_compute_user_theta` so calibration time
    and selection time use the identical formula. Falls back to 0.0 on any
    error so a calibration outage doesn't break session serving.
    """
    try:
        resp = db.rpc('irt_compute_user_theta', {
            'p_user_id':     user_id,
            'p_language_id': language_id,
        }).execute()
        data = resp.data
        if isinstance(data, list) and data:
            return float(data[0]) if data[0] is not None else 0.0
        if data is None:
            return 0.0
        return float(data)
    except Exception as exc:
        logger.warning("Theta lookup failed for user %s lang %s: %s",
                       user_id, language_id, exc)
        return 0.0
