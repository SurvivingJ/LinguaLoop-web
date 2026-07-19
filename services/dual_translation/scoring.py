"""Derived scoring for Dual Translation grading (TASK-627, tech spec §4).

Pure functions — no I/O, no DB, no model calls. They turn the merged error list
plus the active taxonomy `subtype_meta` and the active `dt_rubric_version.config`
into per-dimension bands, and a weighted-mean overall band that renormalizes when
some dimensions are missing.

The three DERIVED dimensions (accuracy, fidelity, understandability) come from
severity-weighted penalties over the errors:

    penalty[accuracy]   = Σ severity_weights[e.severity]  for e where dim(e)==accuracy
    penalty[fidelity]   = Σ severity_weights[e.severity]  for e where dim(e)==fidelity
    penalty[understand] = Σ understandability_weights[e.severity]  for ALL errors

    band[d] = 4 if penalty[d] <= t4 else 3 if <= t3 else 2 if <= t2 else 1

`is_mistake` errors are excluded from every penalty (displayed, never scored —
ADR-019). Naturalness-mapped subtypes (dim==naturalness) still cost
understandability, but contribute nothing to accuracy/fidelity — their own band
comes from the Verifier's judgment, not from here.

`naturalness` and `range` are model-judged and are NOT produced by this module;
the caller (TASK-628) merges them in before calling `compute_overall`.

The weights/thresholds live in the versioned rubric config under the exact keys
the offline gold-seed fallback pins (`severity_weights` /
`understandability_weights` / `band_thresholds`, see
`scripts/dt_gold_seed_helper.OFFLINE_SCORING_CONFIG` and TASK-641). A config that
predates the TASK-627 v5 seed carries none of them; `scoring_params` raises rather
than defaulting to constants — silently full-marking a submission because the
scoring config is missing is exactly the leniency hole TASK-623 closed elsewhere.

Not yet wired into `grade_submission` — TASK-628 swaps the call flow and consumes
this module. Keeping it pure makes the worked-example test the contract.
"""

from __future__ import annotations

from services.dual_translation.tier0 import MAX_BAND, RUBRIC_DIMENSIONS

# The severity vocabulary this module scores (MQM triad, TASK-625). Kept local so
# the module stays import-light; pinned equal to prompts.SEVERITY_ENUM by test.
SEVERITIES = ("minor", "major", "critical")

# Dimensions whose band is derived here from penalties. `understandability` is
# derived but is NOT a subtype_meta dimension — every error feeds it.
PENALTY_DIMENSIONS = ("accuracy", "fidelity")
DERIVED_DIMENSIONS = ("accuracy", "fidelity", "understandability")

# The three keys the TASK-627 rubric v5 seed adds to dt_rubric_version.config.
# `band_thresholds[dim] = [t4, t3, t2]` (ascending): penalty <= t4 -> band 4,
# <= t3 -> 3, <= t2 -> 2, else band 1.
SCORING_KEYS = ("severity_weights", "understandability_weights", "band_thresholds")


def scoring_params(rubric_cfg: dict) -> dict:
    """Extract + validate the derived-scoring keys off the active rubric config.

    Raises RuntimeError if the config predates the TASK-627 v5 seed (carries none
    of SCORING_KEYS) — never silently degrades to constants that may no longer
    match the fixtures/grader. Raises ValueError on a partial/malformed config.
    """
    missing = [k for k in SCORING_KEYS if k not in (rubric_cfg or {})]
    if missing:
        raise RuntimeError(
            f"active rubric config carries no {missing} — it predates the TASK-627 "
            "rubric v5 seed (dt_rubric_v5_seed.sql). Seed + activate v5 before "
            "deriving bands."
        )
    return _validated({k: rubric_cfg[k] for k in SCORING_KEYS})


def _validated(cfg: dict) -> dict:
    """Fail loudly on a partial/malformed scoring config, rather than surfacing a
    KeyError deep in a band computation or — worse — a quietly wrong band."""
    for key in ("severity_weights", "understandability_weights"):
        w = cfg[key]
        bad = [s for s in SEVERITIES if not isinstance(w.get(s), (int, float))]
        if bad:
            raise ValueError(f"{key} missing/non-numeric for: {bad}")
    for dim in DERIVED_DIMENSIONS:
        t = cfg["band_thresholds"].get(dim)
        if not (isinstance(t, (list, tuple)) and len(t) == 3 and all(isinstance(x, int) for x in t)):
            raise ValueError(f"band_thresholds[{dim!r}] must be 3 ints [t4, t3, t2], got {t!r}")
        if not t[0] <= t[1] <= t[2]:
            raise ValueError(f"band_thresholds[{dim!r}] must be ascending [t4 <= t3 <= t2], got {t!r}")
    return cfg


def _band(penalty: float, t4: int, t3: int, t2: int) -> int:
    return 4 if penalty <= t4 else 3 if penalty <= t3 else 2 if penalty <= t2 else 1


def compute_dimension_bands(
    final_errors: list[dict], subtype_meta: dict, rubric_cfg: dict
) -> dict:
    """Derive the accuracy/fidelity/understandability bands from severity-weighted
    penalties (tech spec §4). Pure — no I/O.

    Args:
        final_errors: post-merge error dicts (grader_cascade decode shape), each
            with `severity` (SEVERITIES slug), `subtype` (taxonomy slug) and
            optional `is_mistake`.
        subtype_meta: the active taxonomy's `subtype_meta` — `{slug: {"dimension":
            "accuracy"|"fidelity"|"naturalness", ...}}`.
        rubric_cfg: the active `dt_rubric_version.config` (must carry SCORING_KEYS).

    Returns:
        {"accuracy": int, "fidelity": int, "understandability": int}. naturalness
        and range are model-judged and merged in by the caller, not here.
    """
    cfg = scoring_params(rubric_cfg)
    sev_w = cfg["severity_weights"]
    und_w = cfg["understandability_weights"]
    thresh = cfg["band_thresholds"]

    penalty = {"accuracy": 0, "fidelity": 0}
    understandability = 0
    for e in final_errors:
        if e.get("is_mistake"):
            continue  # displayed, never scored (ADR-019)
        severity = e["severity"]
        # An error whose subtype is unknown to the taxonomy still registers on
        # understandability (it IS an error), but we cannot attribute it to
        # accuracy/fidelity — so it never inflates those. Naturalness-mapped
        # subtypes land in the same "not a penalty dimension" bucket by design:
        # their band comes from the judge, not from a penalty.
        dimension = subtype_meta.get(e["subtype"], {}).get("dimension")
        if dimension in penalty:
            penalty[dimension] += sev_w[severity]
        understandability += und_w[severity]

    return {
        "accuracy": _band(penalty["accuracy"], *thresh["accuracy"]),
        "fidelity": _band(penalty["fidelity"], *thresh["fidelity"]),
        "understandability": _band(understandability, *thresh["understandability"]),
    }


def resolve_weights(rubric_cfg: dict, l2_code: str) -> dict:
    """The effective per-dimension aggregation weights for one L2 — default
    weights with the language overrides applied. Mirror of the weight resolution
    in `grader_cascade.compute_overall_band` so both paths weight identically."""
    weights_cfg = (rubric_cfg or {}).get("weights", {})
    default_weights = weights_cfg.get("default", {})
    overrides = weights_cfg.get("by_language", {}).get(l2_code, {})
    return {
        dim: overrides.get(dim, default_weights.get(dim, 1.0 / len(RUBRIC_DIMENSIONS)))
        for dim in RUBRIC_DIMENSIONS
    }


def compute_overall(bands: dict, weights: dict, present_dims) -> int:
    """Weighted-mean overall band over `present_dims`, renormalized and clipped to
    [1, MAX_BAND]. Pure — no I/O.

    Unlike the legacy `compute_overall_band` (which defaults a missing dimension to
    MAX_BAND), a dimension absent from `present_dims` is dropped from BOTH the
    numerator and the denominator — the mean renormalizes over what is present.
    This is how a Verifier judgment discarded for lacking evidence spans (tech spec
    §4) stops silently pulling the grade toward band 4.

    Args:
        bands: dim -> band (int).
        weights: dim -> weight (already language-resolved, see `resolve_weights`).
        present_dims: the dimensions to include. Any dim not also present in both
            `bands` and `weights` is skipped.

    Returns:
        The overall band, rounded to the nearest integer and clipped to [1, MAX_BAND].
    """
    present = [d for d in present_dims if d in bands and d in weights]
    total_weight = sum(weights[d] for d in present)
    if total_weight <= 0:
        # No usable weighted signal (all-zero weights, or nothing present): fall
        # back to an equal-weight mean over the present bands, else a full mark.
        present_bands = [bands[d] for d in present]
        if not present_bands:
            return MAX_BAND
        band = round(sum(present_bands) / len(present_bands))
        return max(1, min(MAX_BAND, band))

    weighted_sum = sum(bands[d] * weights[d] for d in present)
    band = round(weighted_sum / total_weight)
    return max(1, min(MAX_BAND, band))
