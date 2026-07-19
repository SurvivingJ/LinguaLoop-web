"""Gold-set perturbation + span/normalization verifier for DT grading eval (TASK-621).

NOT part of the running app. Turns declarative edit specs into gold items with
programmatically-computed character-offset spans, and verifies two invariants that
the gold set depends on:

  1. Span integrity — for every seeded error,
     reproduction[span_repro[0]:span_repro[1]] == learner_form  AND
     reference   [span_ref[0]  :span_ref[1]]   == corrected_form.

  2. Normalization survival — a seeded error must NOT be a normalization-class diff,
     i.e. it must still register as a real difference after the Tier-0 normalization
     the deterministic pre-pass applies (services.dual_translation.tier0._normalize_l2
     + services.dictation.tokenizer.normalize). Otherwise Tier 0 would silently award
     full marks and the item would never reach the grader it is meant to measure.

Input model — an *item spec*:

    {
      "id": "ja_seed_01",
      "kind": "clean" | "single" | "multi",
      "source_passage_id": 21,
      "note": "provenance / rationale (free text)",
      "edits": [ <edit>, ... ],
      "expected_bands": {"accuracy":4,"understandability":4,"fidelity":4,"range":4,"naturalness":4}
    }

An *edit* rewrites one span of the reference to produce the reproduction:

    {
      "find": "は",            # exact reference substring to locate
      "nth": 1,                # 1-based occurrence of `find` (default 1)
      "replace": "が",         # learner_form (may be "" for an omission)
      "is_error": true,        # false => acceptable variation (no expected_error emitted)
      "subtype": "particle",           # v4 taxonomy name (required when is_error)
      "subtype_v5_target": "particle_wa_ga",
      "severity_v1": "global",         # OPTIONAL: "global" | "local". Pre-TASK-625
                                       #   vocabulary; nothing reads it any more. Emitted
                                       #   only when the spec supplies it, so the frozen
                                       #   fixtures still round-trip byte-identically.
      "severity_v2": "major"           # "minor" | "major" | "critical"
    }

`build_item` returns the frozen gold item dict; `verify_item` raises AssertionError
on any integrity or normalization violation.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from anywhere in the repo.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.dictation.grader import grade_dictation  # noqa: E402
from services.dictation.tokenizer import normalize as dictation_normalize  # noqa: E402
from services.dual_translation.tier0 import _normalize_l2  # noqa: E402

BANDS = ("accuracy", "understandability", "fidelity", "range", "naturalness")

# v5 subtype -> scored dimension (tech spec §5 subtype_meta). Accuracy/fidelity feed the
# derived penalties; naturalness-mapped subtypes are recorded as errors but their band comes
# from the Verifier judgment, so they do NOT add to the accuracy/fidelity penalty sums.
V5_DIMENSION = {
    # shared core
    "omission": "fidelity", "addition": "fidelity", "word_choice": "fidelity",
    "collocation": "naturalness", "word_order": "accuracy", "register": "fidelity",
    "orthography": "accuracy", "cohesion_connective": "naturalness",
    # EN
    "article": "accuracy", "preposition": "accuracy", "tense_aspect": "accuracy",
    "subject_verb_agreement": "accuracy", "plural_number": "accuracy",
    "phrasal_verb": "fidelity", "pronoun_reference": "accuracy",
    # JA
    "particle_wa_ga": "accuracy", "particle_case": "accuracy", "particle_other": "accuracy",
    "verb_conjugation": "accuracy", "tense_aspect_ja": "accuracy", "keigo_register": "fidelity",
    "counter_classifier": "accuracy", "script_choice": "accuracy", "topic_comment": "naturalness",
    # ZH
    "classifier": "accuracy", "aspect_marker": "accuracy", "de_particles": "accuracy",
    "ba_construction": "accuracy", "bei_passive": "accuracy",
    "resultative_complement": "accuracy", "directional_complement": "accuracy",
    "adverbial_order": "accuracy",
}

SEVERITIES = ("minor", "major", "critical")
DERIVED_DIMENSIONS = ("accuracy", "fidelity", "understandability")

# tech spec §4 derived-scoring constants, keyed exactly as the TASK-627 rubric v5
# config declares them (`severity_weights` / `understandability_weights` /
# `band_thresholds` — the dt_rubric_v4_seed.sql header's "severity_weights/thresholds"
# is shorthand for the same three). These are the PINNED OFFLINE FALLBACK: the values
# the frozen fixtures in tests/fixtures/dt_gold/ were derived under. Once TASK-627
# seeds the live keys, test_dual_translation_gold_seed_helper.py fails if the seeded
# values disagree with these — the fixtures' expected_bands and the live grader must
# not drift apart silently.
#
# `band_thresholds[dim] = [t4, t3, t2]`: penalty <= t4 -> band 4, <= t3 -> 3,
# <= t2 -> 2, else band 1.
SCORING_KEYS = ("severity_weights", "understandability_weights", "band_thresholds")

OFFLINE_SCORING_CONFIG = {
    "severity_weights": {"minor": 1, "major": 5, "critical": 25},
    "understandability_weights": {"minor": 0, "major": 2, "critical": 25},
    "band_thresholds": {
        "accuracy": [1, 6, 15],
        "fidelity": [1, 6, 15],
        "understandability": [2, 6, 25],
    },
}


def scoring_config(rubric_cfg: dict | None = None, *, offline: bool = False) -> dict:
    """Resolve the derived-scoring config: live rubric config, or the pinned fallback.

    Exactly one source must be named — passing neither is the mistake this function
    exists to prevent, since defaulting to the constants is what let the fixtures and
    the live grader drift apart in the first place.

      * `scoring_config(rubric_cfg)` — read the SCORING_KEYS off the active
        `dt_rubric_version.config` (grader_cascade.get_active_rubric). Raises if that
        row predates TASK-627 and carries none of them, rather than silently falling
        back to constants that may no longer match the live grader.
      * `scoring_config(offline=True)` — the `--offline` path: use
        OFFLINE_SCORING_CONFIG. For rebuilding fixtures with no DB reachable.
    """
    if offline:
        if rubric_cfg is not None:
            raise ValueError("pass either rubric_cfg or offline=True, not both")
        return OFFLINE_SCORING_CONFIG
    if rubric_cfg is None:
        raise ValueError(
            "no scoring source: pass the active rubric config (grader_cascade."
            "get_active_rubric), or offline=True to use the pinned fallback constants"
        )

    missing = [k for k in SCORING_KEYS if k not in rubric_cfg]
    if missing:
        raise RuntimeError(
            f"active rubric config carries no {missing} — it predates the TASK-627 "
            "rubric v5 seed. Seed v5, or pass offline=True to accept the pinned "
            "fallback constants."
        )
    return _validated({k: rubric_cfg[k] for k in SCORING_KEYS})


def _validated(cfg: dict) -> dict:
    """Fail loudly on a partial/malformed scoring config.

    A missing severity or dimension would otherwise surface as a KeyError deep in a
    band computation, or — worse, if defaulted — as a quietly wrong expected_band.
    """
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


def _severity_weights_for(cfg: dict, dim: str) -> dict:
    """Understandability scores off its own severity axis (tech spec §4); accuracy and
    fidelity share the penalty weights."""
    return cfg["understandability_weights"] if dim == "understandability" else cfg["severity_weights"]


def _band(penalty: float, t4: int, t3: int, t2: int) -> int:
    return 4 if penalty <= t4 else 3 if penalty <= t3 else 2 if penalty <= t2 else 1


def derive_bands(
    expected_errors: list[dict],
    judged: dict | None = None,
    *,
    rubric_cfg: dict | None = None,
    offline: bool = False,
) -> dict:
    """Compute expected bands from seeded errors per tech spec §4.

    accuracy/fidelity/understandability are derived from severity-weighted penalties;
    naturalness and range are model-judged, so they are taken from `judged`
    (defaulting to 4 — a clean text — when not supplied by the adjudicator).
    `is_mistake` is not seeded in this gold set, so every error scores.

    Weights/thresholds come from `rubric_cfg` or the `offline` fallback — see
    `scoring_config`. Every error contributes to the understandability penalty,
    including naturalness-mapped ones, which do not feed accuracy/fidelity.
    """
    cfg = scoring_config(rubric_cfg, offline=offline)
    judged = judged or {}
    pen = {"accuracy": 0, "fidelity": 0}
    und = 0
    und_w = _severity_weights_for(cfg, "understandability")
    for e in expected_errors:
        sev = e["severity_v2"]
        dim = V5_DIMENSION[e["subtype_v5_target"]]
        if dim in pen:
            pen[dim] += _severity_weights_for(cfg, dim)[sev]
        und += und_w[sev]
    thresh = cfg["band_thresholds"]
    return {
        "accuracy": _band(pen["accuracy"], *thresh["accuracy"]),
        "understandability": _band(und, *thresh["understandability"]),
        "fidelity": _band(pen["fidelity"], *thresh["fidelity"]),
        "range": judged.get("range", 4),
        "naturalness": judged.get("naturalness", 4),
    }


def _nth_index(haystack: str, needle: str, nth: int) -> int:
    """0-based char index of the nth (1-based) occurrence of needle, or raise."""
    if not needle:
        raise ValueError("edit.find must be non-empty (use replace='' for omissions)")
    idx = -1
    for _ in range(nth):
        idx = haystack.find(needle, idx + 1)
        if idx == -1:
            raise ValueError(f"occurrence {nth} of {needle!r} not found")
    return idx


def _norm_class_equal(a: str, b: str, language_code: str) -> bool:
    """True if a and b collapse to the same string under Tier-0 normalization —
    i.e. the diff between them is normalization-class and Tier 0 would swallow it."""
    return dictation_normalize(_normalize_l2(a, language_code)) == dictation_normalize(
        _normalize_l2(b, language_code)
    )


def build_item(spec: dict, reference: str, language_code: str) -> dict:
    """Apply a spec's edits to `reference`, returning the frozen gold item with spans."""
    edits = spec.get("edits", [])
    # Resolve each edit to an absolute reference position first, then apply left→right
    # so we can track the reproduction-side offset shift as text length changes.
    resolved = []
    for e in edits:
        pos = _nth_index(reference, e["find"], e.get("nth", 1))
        resolved.append((pos, e))
    resolved.sort(key=lambda pe: pe[0])

    # Guard against overlapping edits (ambiguous spans).
    prev_end = -1
    for pos, e in resolved:
        if pos < prev_end:
            raise ValueError(f"overlapping edits near ref pos {pos} in {spec['id']}")
        prev_end = pos + len(e["find"])

    reproduction_parts: list[str] = []
    cursor = 0          # position in reference consumed so far
    delta = 0           # reproduction_len - reference_len up to `cursor`
    expected_errors: list[dict] = []

    for pos, e in resolved:
        find, repl = e["find"], e["replace"]
        reproduction_parts.append(reference[cursor:pos])   # untouched gap
        repro_pos = pos + delta
        reproduction_parts.append(repl)
        cursor = pos + len(find)
        delta += len(repl) - len(find)

        if e.get("is_error", True):
            err = {
                "span_repro": [repro_pos, repro_pos + len(repl)],
                "span_ref": [pos, pos + len(find)],
                "subtype": e["subtype"],
                "subtype_v5_target": e.get("subtype_v5_target", e["subtype"]),
            }
            # severity_v1 is pre-TASK-625 vocabulary that nothing reads any more.
            # Carried through (in position) when the spec supplies it so the frozen
            # fixtures round-trip byte-identically; omitted, not nulled, otherwise.
            if e.get("severity_v1") is not None:
                err["severity_v1"] = e["severity_v1"]
            err["severity_v2"] = e["severity_v2"]
            err["learner_form"] = repl
            err["corrected_form"] = find
            expected_errors.append(err)

    reproduction_parts.append(reference[cursor:])
    reproduction = "".join(reproduction_parts)

    return {
        "id": spec["id"],
        "kind": spec["kind"],
        "source_passage_id": spec["source_passage_id"],
        "note": spec.get("note", ""),
        "reference": reference,
        "reproduction": reproduction,
        "expected_errors": expected_errors,
        "expected_bands": {b: spec["expected_bands"][b] for b in BANDS},
    }


def verify_item(item: dict, language_code: str) -> list[str]:
    """Return a list of problems (empty == valid)."""
    problems: list[str] = []
    ref, repro = item["reference"], item["reproduction"]

    for i, err in enumerate(item["expected_errors"]):
        sr, sf = err["span_repro"], err["span_ref"]
        got_repro = repro[sr[0]:sr[1]]
        got_ref = ref[sf[0]:sf[1]]
        if got_repro != err["learner_form"]:
            problems.append(
                f"{item['id']} err#{i}: repro span {sr} -> {got_repro!r} != learner_form {err['learner_form']!r}"
            )
        if got_ref != err["corrected_form"]:
            problems.append(
                f"{item['id']} err#{i}: ref span {sf} -> {got_ref!r} != corrected_form {err['corrected_form']!r}"
            )
        if _norm_class_equal(err["learner_form"], err["corrected_form"], language_code):
            problems.append(
                f"{item['id']} err#{i}: NORMALIZATION-CLASS diff "
                f"{err['corrected_form']!r}->{err['learner_form']!r} (Tier 0 would swallow it)"
            )

    # Kind-level sanity.
    kind = item["kind"]
    n = len(item["expected_errors"])
    if kind == "clean" and n != 0:
        problems.append(f"{item['id']}: kind=clean but {n} expected_errors")
    if kind == "single" and n != 1:
        problems.append(f"{item['id']}: kind=single but {n} expected_errors")
    if kind == "multi" and not (2 <= n <= 4):
        problems.append(f"{item['id']}: kind=multi but {n} expected_errors (want 2-4)")

    # A seeded (non-clean) item must produce a real dictation-level diff, else the
    # grader never sees it. Clean items are allowed to be normalization-identical.
    if kind != "clean":
        g = grade_dictation(_normalize_l2(ref, language_code), _normalize_l2(repro, language_code), language_code)
        if g.accuracy >= 1.0:
            problems.append(f"{item['id']}: reproduction is fuzzy-identical to reference (accuracy=1.0)")

    for b in BANDS:
        v = item["expected_bands"].get(b)
        if v not in (1, 2, 3, 4):
            problems.append(f"{item['id']}: band {b}={v!r} not in 1..4")

    return problems


def build_and_verify(specs: list[dict], passages: dict[int, str], language_code: str):
    """Build every spec; return (items, all_problems)."""
    items, problems = [], []
    for spec in specs:
        ref = passages[spec["source_passage_id"]]
        item = build_item(spec, ref, language_code)
        items.append(item)
        problems.extend(verify_item(item, language_code))
    return items, problems
