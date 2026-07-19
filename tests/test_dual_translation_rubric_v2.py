"""Shape + weight-effect tests for the TASK-616 rubric v2 seed.

The taxonomy carries no weights; compute_overall_band reads them only from
dt_rubric_version. So the "JA keigo -> fidelity up-weighted" and "ZH classifier/
aspect -> accuracy up-weighted" acceptance criteria are met by *this* seed, not by
the taxonomy. These tests extract the real config out of
migrations/dt_rubric_v2_seed.sql and prove:

  * ja.fidelity and zh.accuracy are raised above the v1 baseline (and above the
    default), the default weights are untouched, and the band descriptors are
    byte-identical to v1 (only weights change).
  * The up-weight actually MOVES grades: for a reproduction weak on the up-weighted
    dimension, v2's weighted score is strictly lower than v1's (via the real
    grader_cascade.compute_overall_band math).
"""

import json
import pathlib
import re

import pytest

from services.dual_translation import grader_cascade, prompts
from services.dual_translation.tier0 import MAX_BAND, RUBRIC_DIMENSIONS

MIGRATIONS = pathlib.Path(__file__).resolve().parents[1] / "migrations"
V1_PATH = MIGRATIONS / "dt_rubric_v1_seed.sql"
V2_PATH = MIGRATIONS / "dt_rubric_v2_seed.sql"
V4_PATH = MIGRATIONS / "dt_rubric_v4_seed.sql"
TAXONOMY_V5_PATH = MIGRATIONS / "dt_taxonomy_v5_seed.sql"


def _extract_config(path: pathlib.Path) -> dict:
    m = re.search(r"\$rubric\$(.*?)\$rubric\$", path.read_text(encoding="utf-8"), re.DOTALL)
    assert m, f"could not find the $rubric$...$rubric$ literal in {path.name}"
    return json.loads(m.group(1))


def _extract_taxonomy(path: pathlib.Path) -> dict:
    """The taxonomy seed dollar-quotes its literal with its own tag. Strip the
    leading `--` comment block first so prose mentioning a $tag$ can't shadow it."""
    body = "\n".join(
        line for line in path.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("--")
    )
    m = re.search(r"\$[a-zA-Z_]*\$(.*?)\$[a-zA-Z_]*\$", body, re.DOTALL)
    assert m, f"could not find the dollar-quoted literal in {path.name}"
    return json.loads(m.group(1))


@pytest.fixture(scope="module")
def v1() -> dict:
    return _extract_config(V1_PATH)


@pytest.fixture(scope="module")
def v2() -> dict:
    return _extract_config(V2_PATH)


def _weighted_mean(scores: dict, cfg: dict, l2: str) -> float:
    """Mirror of compute_overall_band's pre-rounding weighted mean, so we can assert
    the raw grade moves even when it doesn't cross a rounding boundary."""
    weights_cfg = cfg.get("weights", {})
    default = weights_cfg.get("default", {})
    overrides = weights_cfg.get("by_language", {}).get(l2, {})
    raw = {d: overrides.get(d, default.get(d, 1.0 / len(RUBRIC_DIMENSIONS))) for d in RUBRIC_DIMENSIONS}
    total = sum(raw.values()) or 1.0
    return sum(scores.get(d, MAX_BAND) * (w / total) for d, w in raw.items())


# ---------------------------------------------------------------------------
# Weight values
# ---------------------------------------------------------------------------

def test_ja_fidelity_raised_above_baseline_and_default(v1, v2):
    assert v1["weights"]["by_language"]["ja"]["fidelity"] == 0.25
    assert v2["weights"]["by_language"]["ja"]["fidelity"] == 0.30
    # 0.25 <= 0.30 <= 0.35 per the task's stated band, and strictly above baseline + default
    assert 0.25 <= v2["weights"]["by_language"]["ja"]["fidelity"] <= 0.35
    assert v2["weights"]["by_language"]["ja"]["fidelity"] > v2["weights"]["default"]["fidelity"]


def test_zh_accuracy_raised_above_baseline(v1, v2):
    assert v1["weights"]["by_language"]["zh"]["accuracy"] == 0.35
    assert v2["weights"]["by_language"]["zh"]["accuracy"] == 0.40
    assert v2["weights"]["by_language"]["zh"]["accuracy"] > 0.35  # task: "0.35+, higher than baseline"
    assert v2["weights"]["by_language"]["zh"]["accuracy"] > v2["weights"]["default"]["accuracy"]


def test_default_weights_unchanged(v1, v2):
    assert v2["weights"]["default"] == v1["weights"]["default"]


def test_band_descriptors_byte_identical_to_v1(v1, v2):
    assert v2["band_descriptors"] == v1["band_descriptors"], "v2 must change weights only"


# ---------------------------------------------------------------------------
# The up-weight actually moves grades (via the real compute_overall_band math)
# ---------------------------------------------------------------------------

def test_ja_fidelity_upweight_lowers_a_keigo_weak_grade(v1, v2):
    # A reproduction that is fine everywhere except fidelity (the keigo/register
    # dimension) — the v2 up-weight must pull the aggregate score down.
    scores = {"accuracy": 4, "understandability": 4, "fidelity": 1, "naturalness": 4, "range": 4}
    assert _weighted_mean(scores, v2, "ja") < _weighted_mean(scores, v1, "ja")
    assert grader_cascade.compute_overall_band(scores, v2, "ja") <= grader_cascade.compute_overall_band(scores, v1, "ja")


def test_zh_accuracy_upweight_lowers_a_classifier_weak_grade(v1, v2):
    # Weak only on accuracy (where classifier/aspect errors land) — v2 pulls it down.
    scores = {"accuracy": 1, "understandability": 4, "fidelity": 4, "naturalness": 4, "range": 4}
    assert _weighted_mean(scores, v2, "zh") < _weighted_mean(scores, v1, "zh")
    assert grader_cascade.compute_overall_band(scores, v2, "zh") <= grader_cascade.compute_overall_band(scores, v1, "zh")


def test_upweight_is_language_scoped(v1, v2):
    # An all-4 reproduction is unaffected; and en has no overrides in either version.
    perfect = {d: MAX_BAND for d in RUBRIC_DIMENSIONS}
    assert grader_cascade.compute_overall_band(perfect, v2, "ja") == MAX_BAND
    scores = {"accuracy": 2, "understandability": 3, "fidelity": 2, "naturalness": 3, "range": 3}
    assert _weighted_mean(scores, v2, "en") == _weighted_mean(scores, v1, "en")


# ---------------------------------------------------------------------------
# Seed migration safety
# ---------------------------------------------------------------------------

def test_seed_bumps_to_v2_single_active_row():
    sql = V2_PATH.read_text(encoding="utf-8")
    assert "VALUES (\n    2," in sql
    assert "SET is_active = false WHERE is_active AND version <> 2" in sql
    assert "ON CONFLICT (version) DO UPDATE" in sql
    do_update = sql.split("ON CONFLICT (version) DO UPDATE", 1)[1]
    assert "is_active = true" in do_update.split(";", 1)[0]


# ---------------------------------------------------------------------------
# TASK-624 rubric v4: acceptable_variation + exemplars, on top of v2's
# descriptors/weights. TASK-636 made this row SELF-CONTAINED (see ADR-020): it
# used to build its config as `src.config || $add$...$add$` via an INSERT..SELECT
# gated on `WHERE src.version = 2`, which made a superseded row a runtime
# dependency and could commit ZERO active rows on an env without v2. The
# descriptors/weights are now held equal to v2 by test, not by construction.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def v4() -> dict:
    return _extract_config(V4_PATH)


@pytest.fixture(scope="module")
def v4_additions(v4) -> dict:
    """The two prompt-content keys v4 adds on top of v2. No longer a separate SQL
    literal now that v4 states its whole config (TASK-636)."""
    return {k: v4[k] for k in ("acceptable_variation", "exemplars") if k in v4}


@pytest.fixture(scope="module")
def taxonomy_v5() -> dict:
    return _extract_taxonomy(TAXONOMY_V5_PATH)


def test_v4_adds_only_the_two_prompt_content_keys(v4, v2):
    # v4 carries v2's keys plus EXACTLY the two new prompt-content keys.
    assert set(v4) == set(v2) | {"acceptable_variation", "exemplars"}
    assert set(v4) == {"band_descriptors", "weights", "acceptable_variation", "exemplars"}


def test_v4_band_descriptors_and_weights_match_v2(v4, v2):
    """TASK-636/ADR-020: this test is now the ONLY thing keeping v4's descriptors and
    weights from drifting from v2 — the `jsonb ||` inheritance that used to guarantee it
    by construction was removed because it made a superseded row a hard runtime dependency.
    If this fails, v4's config was hand-edited: regenerate it from v2 rather than patching."""
    assert v4["band_descriptors"] == v2["band_descriptors"]
    assert v4["weights"] == v2["weights"]


def _executable_sql(path: pathlib.Path) -> str:
    """The seed's header documents the mechanism TASK-636 removed, so a raw substring
    scan would match its own prose. Assert against executable statements only."""
    return "\n".join(
        line for line in path.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("--")
    )


def test_v4_seed_is_self_contained(v4):
    # The whole point of TASK-636: no cross-row derivation, no v2 gate.
    sql = _executable_sql(V4_PATH)
    assert "$add$" not in sql, "v4 must not reintroduce the additions-only literal"
    assert "src.config" not in sql, "v4 must not derive its config from another row"
    assert "FROM public.dt_rubric_version src" not in sql
    assert "WHERE src.version = 2" not in sql


def test_v4_acceptable_variation_has_all_three_l2s(v4_additions):
    av = v4_additions["acceptable_variation"]
    assert set(av) == {"en", "zh", "ja"}
    for l2, bullets in av.items():
        assert isinstance(bullets, list) and bullets, f"{l2} acceptable_variation must be a non-empty list"
        assert all(isinstance(b, str) and b for b in bullets)


def test_v4_exemplars_are_well_formed_for_all_three_l2s(v4_additions):
    exemplars = v4_additions["exemplars"]
    assert set(exemplars) == {"en", "zh", "ja"}
    for l2, ex in exemplars.items():
        assert ex.get("reference") and ex.get("learner"), f"{l2} exemplar needs reference + learner"
        assert isinstance(ex.get("scores"), dict) and ex["scores"], f"{l2} exemplar needs scores"
        err = ex.get("error", {})
        # Subtype and severity are stored as stable slugs (resolved to indices at
        # prompt build) — never as hardcoded indices. TASK-637.
        assert err.get("subtype_slug"), f"{l2} exemplar error needs a subtype_slug"
        assert err.get("severity_slug"), f"{l2} exemplar error needs a severity_slug"
        assert "subtype" not in err, f"{l2} exemplar must NOT hardcode a subtype index"
        assert "severity" not in err, f"{l2} exemplar must NOT hardcode a severity index"
        for k in ("span_repro", "span_ref", "learner_form", "corrected_form"):
            assert k in err, f"{l2} exemplar error missing {k}"
        # The exemplar's forms must sit exactly at their spans (span discipline).
        sr, srf = err["span_repro"], err["span_ref"]
        assert ex["learner"][sr[0]:sr[1]] == err["learner_form"]
        assert ex["reference"][srf[0]:srf[1]] == err["corrected_form"]


def test_v4_exemplar_severities_encode_the_triad_meaning(v4_additions):
    """The exemplar severities must carry the intended MQM triad MEANING.

    This began as a TASK-625 gotcha guard, when severity was a bare integer and a
    SEVERITY_ENUM reorder would silently re-point it at the wrong level. TASK-637
    moved these to slugs, which kills that failure mode at the root — a slug means
    what it says regardless of list order. The test stays because it pins the
    editorial judgement (which error is worth which level), which no mechanism can
    check: swapping these two slugs would still resolve cleanly and still be wrong.
    """
    exemplars = v4_additions["exemplars"]
    # EN tense slip ("lives" for "has lived") reads on -> minor.
    assert exemplars["en"]["error"]["severity_slug"] == "minor"
    # ZH missing 了 aspect marker changes the meaning -> major.
    assert exemplars["zh"]["error"]["severity_slug"] == "major"
    # JA は/が particle swap changes the meaning -> major.
    assert exemplars["ja"]["error"]["severity_slug"] == "major"


def test_v4_exemplar_slugs_resolve_via_the_real_runtime_resolver(v4_additions, taxonomy_v5):
    """TASK-637 criterion 4: EVERY seeded slug — subtype and severity — resolves.

    Deliberately calls prompts._slug_index, the same function _exemplar_text uses, rather
    than re-checking membership with `in`. A test that reimplements the resolution it is
    guarding passes when the real resolver is broken; this one cannot.
    """
    for l2, ex in v4_additions["exemplars"].items():
        err = ex["error"]
        subtypes = taxonomy_v5["pairs"][l2]["subtypes"]
        subtype_index = prompts._slug_index(subtypes, err["subtype_slug"])
        severity_index = prompts._slug_index(prompts.SEVERITY_ENUM, err["severity_slug"])
        assert subtype_index is not None, (
            f"{l2} exemplar subtype_slug={err['subtype_slug']!r} does not resolve against the "
            f"active taxonomy's pairs/{l2} subtypes — _exemplar_text would drop this exemplar "
            f"and the prompt would lose its worked example. Available: {subtypes}"
        )
        assert severity_index is not None, (
            f"{l2} exemplar severity_slug={err['severity_slug']!r} does not resolve against "
            f"SEVERITY_ENUM={prompts.SEVERITY_ENUM}"
        )


def test_v4_exemplar_subtype_slugs_resolve_in_the_active_taxonomy(v4_additions, taxonomy_v5):
    """TASK-636/637 regression, and the seam ADR-020 is about.

    An exemplar's subtype_slug is a foreign key into the TAXONOMY's per-pair subtype list,
    but the two rows are versioned independently and Postgres cannot enforce a FK inside
    jsonb — so nothing except this test relates them.

    It fails on the pre-fix seed: taxonomy v5 split JA `particle` into particle_wa_ga /
    particle_case / particle_other and dropped `particle` from every pairs list, while the
    v4 seed still said `particle`. prompts._exemplar_text resolved the miss to index 0
    (= `omission`), so every JA prompt taught that a は/が swap is an omission — silently.
    """
    for l2, ex in v4_additions["exemplars"].items():
        slug = ex["error"]["subtype_slug"]
        subtypes = taxonomy_v5["pairs"][l2]["subtypes"]
        assert slug in subtypes, (
            f"{l2} exemplar subtype_slug={slug!r} is absent from the active taxonomy's "
            f"pairs/{l2} subtype list — the rubric and taxonomy rows have drifted (ADR-020). "
            f"Available: {subtypes}"
        )


def test_v4_ja_exemplar_uses_the_post_split_particle_slug(v4_additions):
    """Pin the exact regression: taxonomy v5 retired the bare `particle` slug."""
    assert v4_additions["exemplars"]["ja"]["error"]["subtype_slug"] == "particle_wa_ga"


def test_v4_seed_guards_the_single_active_row_invariant():
    """TASK-636: the seed must RAISE rather than commit a broken invariant. Both guards sit
    inside the BEGIN/COMMIT so a failure rolls back instead of leaving grading rubric-less."""
    sql = _executable_sql(V4_PATH)
    # Guard 1 — refuse to silently downgrade a NEWER active rubric (e.g. the TASK-627 v5).
    # A count check cannot catch this: after a downgrade exactly one row is still active.
    assert "WHERE is_active AND version > 4" in sql
    # Guard 2 — assert exactly one active row, and that it is v4, before COMMIT.
    assert "active_count <> 1" in sql
    assert "active_version <> 4" in sql
    assert sql.count("RAISE EXCEPTION") >= 3
    assert sql.index("BEGIN;") < sql.index("RAISE EXCEPTION") < sql.index("COMMIT;")


def test_v4_seed_bumps_to_v4_single_active_row():
    sql = V4_PATH.read_text(encoding="utf-8")
    assert "VALUES (\n    4," in sql
    assert "SET is_active = false WHERE is_active AND version <> 4" in sql
    assert "ON CONFLICT (version) DO UPDATE" in sql
    do_update = sql.split("ON CONFLICT (version) DO UPDATE", 1)[1]
    assert "is_active = true" in do_update.split(";", 1)[0]
