"""Shape + §8-pattern tests for the rubric v6 seed (TASK-629): band descriptors
v3 rewrite.

v6 is a *descriptors-only* bump on top of v5 (TASK-627). These tests feed the
real seeded config — extracted straight out of ``migrations/dt_rubric_v6_seed.sql``
— through both production consumer access paths (no live DB), and lint the new
band-descriptor text against the tech spec §8 pattern acceptance criteria:

  * observable behaviour + a parenthetical error profile in every descriptor;
  * no frequency adverbs (EN lint);
  * no two adjacent bands differ only by an adverb (EN lint);
  * distinct content per band;
  * the old "(content level: ...)" suffix is retired.

Carry-forward is asserted too: weights / acceptable_variation / exemplars /
severity_weights / understandability_weights / band_thresholds must equal v5
byte-value (this is a descriptors-only change), and band_descriptors must NOT
equal v5 (it is the thing that changed).
"""

import json
import pathlib
import re

import pytest

import routes.dual_translation as dt_routes
from services.dual_translation import grader_cascade, prompts
from services.dual_translation.tier0 import RUBRIC_DIMENSIONS, MAX_BAND

MIGRATIONS = pathlib.Path(__file__).resolve().parents[1] / "migrations"
V6_PATH = MIGRATIONS / "dt_rubric_v6_seed.sql"
V5_PATH = MIGRATIONS / "dt_rubric_v5_seed.sql"

L2_CODES = ("zh", "en", "ja")
TIERS = (1, 2, 3, 4, 5, 6)
BANDS = {"1", "2", "3", "4"}
DERIVED_DIMS = ("accuracy", "fidelity", "understandability")
JUDGE_DIMS = ("naturalness", "range")

# The AC "no frequency adverbs" lint set (EN). "throughout" is an adverb of
# extent, not frequency, and is used by the tech spec §8 exemplar itself.
FREQUENCY_ADVERBS = (
    "usually", "often", "sometimes", "rarely", "occasionally", "frequently",
    "generally", "seldom", "always", "never", "mostly", "normally", "typically",
    "ordinarily",
)
# Stripped before the adjacent-band comparison so "differ only by an adverb" is
# actually tested (frequency + the degree adverbs the descriptors use).
_STRIP_ADVERBS = set(FREQUENCY_ADVERBS) | {
    "slightly", "clearly", "largely", "nearly", "almost", "visibly",
    "recognisably", "recognizably", "genuinely", "subtly", "plainly", "fully",
}


# ---------------------------------------------------------------------------
# Load the real seed shapes out of the SQL artifacts
# ---------------------------------------------------------------------------

def _extract_config(path: pathlib.Path) -> dict:
    sql = path.read_text(encoding="utf-8")
    m = re.search(r"\$rubric\$(.*?)\$rubric\$", sql, re.DOTALL)
    assert m, f"no dollar-quoted ($rubric$...$rubric$) config literal in {path.name}"
    return json.loads(m.group(1))


@pytest.fixture(scope="module")
def v6() -> dict:
    return _extract_config(V6_PATH)


@pytest.fixture(scope="module")
def v5() -> dict:
    return _extract_config(V5_PATH)


@pytest.fixture(autouse=True)
def _clear_grader_cascade_caches():
    """get_active_rubric caches process-wide (TASK-642); drop it either side of
    every test so these _FakeDB reads hit the real query code."""
    grader_cascade.clear_caches()
    yield
    grader_cascade.clear_caches()


# Minimal fake Supabase query-builder returning the seeded rubric row, so the
# REAL get_active_rubric / _rubric_descriptors_for code runs end-to-end.
class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return _FakeResult(self._rows)


class _FakeDB:
    def __init__(self, config):
        self._config = config

    def table(self, name):
        assert name == "dt_rubric_version", f"unexpected table read: {name!r}"
        return _FakeQuery([{"config": self._config}])


def _leaves(bd: dict):
    """Yield (tier, dim, l2, band, text) for every descriptor leaf."""
    for tier, dims in bd.items():
        for dim, per_lang in dims.items():
            for l2, bands in per_lang.items():
                for band, text in bands.items():
                    yield tier, dim, l2, band, text


# ---------------------------------------------------------------------------
# Structure: 6 tiers, dims per tier, both reader paths KeyError-free
# ---------------------------------------------------------------------------

def test_band_descriptors_cover_all_six_tiers(v6):
    assert set(v6["band_descriptors"]) == {str(t) for t in TIERS}


def test_dims_present_per_tier(v6):
    bd = v6["band_descriptors"]
    for tier in (1, 2):
        assert set(bd[str(tier)]) == set(DERIVED_DIMS) | {"range"}, tier
        assert "naturalness" not in bd[str(tier)], tier
    for tier in (3, 4, 5, 6):
        assert set(bd[str(tier)]) == set(RUBRIC_DIMENSIONS), tier


def test_every_leaf_has_all_bands_in_all_l2s(v6):
    bd = v6["band_descriptors"]
    for tier, dims in bd.items():
        for dim, per_lang in dims.items():
            assert set(per_lang) == {"en", "ja", "zh"}, (tier, dim)
            for l2, bands in per_lang.items():
                assert set(bands) == BANDS, (tier, dim, l2)


@pytest.mark.parametrize("tier", TIERS)
@pytest.mark.parametrize("l2_code", L2_CODES)
def test_rubric_descriptors_for_reads_without_keyerror(v6, tier, l2_code):
    descriptors = dt_routes._rubric_descriptors_for(_FakeDB(v6), tier, l2_code)
    assert descriptors, (tier, l2_code)
    for dim, leaf in descriptors.items():
        assert isinstance(leaf, dict) and set(leaf) == BANDS, (tier, l2_code, dim, leaf)
    if tier in (1, 2):
        assert "naturalness" not in descriptors, (tier, "naturalness hidden at tiers 1-2")
    else:
        assert "naturalness" in descriptors, (tier, l2_code)


@pytest.mark.parametrize("tier", TIERS)
@pytest.mark.parametrize("l2_code", L2_CODES)
def test_prompts_band_descriptors_text_renders(v6, tier, l2_code):
    graded = [d for d in RUBRIC_DIMENSIONS if not (d == "naturalness" and tier in (1, 2))]
    text = prompts._band_descriptors_text(v6, tuple(graded), tier, l2_code)
    assert text.strip(), (tier, l2_code)
    assert text.count("- ") == len(graded), (tier, l2_code, text)


def test_naturalness_absent_in_raw_config_at_low_tiers(v6):
    bd = v6["band_descriptors"]
    assert "naturalness" not in bd["1"]
    assert "naturalness" not in bd["2"]
    for tier in ("3", "4", "5", "6"):
        assert "naturalness" in bd[tier], tier


# ---------------------------------------------------------------------------
# §8 pattern lint (the TASK-629 acceptance criteria)
# ---------------------------------------------------------------------------

def test_every_descriptor_has_a_parenthetical_error_profile(v6):
    """AC: observable behaviour + a parenthetical error profile. ASCII or
    fullwidth parens (ZH/JA use （）)."""
    for tier, dim, l2, band, text in _leaves(v6["band_descriptors"]):
        assert ("(" in text and ")" in text) or ("（" in text and "）" in text), (
            "no parenthetical", tier, dim, l2, band, text)


def test_no_content_level_suffix_survives(v6):
    """The v1-v5 "(content level: ...)" / 内容レベル / 内容层级 suffix is retired."""
    for tier, dim, l2, band, text in _leaves(v6["band_descriptors"]):
        low = text.lower()
        assert "content level" not in low, (tier, dim, l2, band, text)
        assert "内容レベル" not in text, (tier, dim, l2, band, text)
        assert "内容层级" not in text, (tier, dim, l2, band, text)


def test_distinct_content_per_band(v6):
    """AC: distinct content per band — the four bands of a (tier, dim, l2) are
    pairwise distinct in every language."""
    bd = v6["band_descriptors"]
    for tier, dims in bd.items():
        for dim, per_lang in dims.items():
            for l2, bands in per_lang.items():
                texts = [bands[b] for b in ("1", "2", "3", "4")]
                assert len(set(texts)) == 4, ("duplicate band text", tier, dim, l2, texts)


def test_no_frequency_adverbs_in_english(v6):
    """AC: no frequency adverbs (EN lint; ZH/JA covered by native review)."""
    pat = re.compile(r"\b(" + "|".join(FREQUENCY_ADVERBS) + r")\b", re.I)
    for tier, dim, l2, band, text in _leaves(v6["band_descriptors"]):
        if l2 != "en":
            continue
        m = pat.search(text)
        assert not m, ("frequency adverb", tier, dim, band, m and m.group(0), text)


def _skeleton(text: str) -> tuple:
    """Lowercase alphabetic word multiset with adverbs removed — the content
    'skeleton' that must differ between adjacent bands."""
    words = re.findall(r"[a-z]+", text.lower())
    return tuple(w for w in words if w not in _STRIP_ADVERBS)


def test_no_adjacent_bands_differ_only_by_an_adverb(v6):
    """AC: no two adjacent bands differ only by an adverb (EN lint). After
    stripping adverbs, the remaining content of adjacent bands must still
    differ — else the bands separated on an adverb alone."""
    bd = v6["band_descriptors"]
    for tier, dims in bd.items():
        for dim, per_lang in dims.items():
            bands = per_lang["en"]
            for lo, hi in (("1", "2"), ("2", "3"), ("3", "4")):
                assert _skeleton(bands[lo]) != _skeleton(bands[hi]), (
                    "adjacent bands differ only by an adverb", tier, dim, lo, hi,
                    bands[lo], bands[hi])


def test_descriptors_reference_age_tiers_not_cefr(v6):
    cefr_token = re.compile(r"\b(?:CEFR|[ABC][12])\b")
    for tier, dim, l2, band, text in _leaves(v6["band_descriptors"]):
        assert "cefr" not in text.lower(), (tier, dim, l2, band, text)
        assert not cefr_token.search(text), (tier, dim, l2, band, text)


# ---------------------------------------------------------------------------
# Tier-invariance / tier-variance of the design
# ---------------------------------------------------------------------------

def test_derived_dims_and_range_are_tier_invariant(v6):
    """accuracy/fidelity/understandability/range are level-neutral (ADR-018):
    identical text at every tier they appear in."""
    bd = v6["band_descriptors"]
    for dim in ("accuracy", "fidelity", "understandability", "range"):
        reference = bd["1"][dim]
        for tier in ("2", "3", "4", "5", "6"):
            assert bd[tier][dim] == reference, ("tier-variant derived/range dim", dim, tier)


def test_naturalness_is_tier_varying(v6):
    """naturalness is the one tier-dependent dim (ADR-018): band-4 text differs
    across tiers 3-6 (the register anchor scales)."""
    bd = v6["band_descriptors"]
    b4 = {tier: bd[tier]["naturalness"]["en"]["4"] for tier in ("3", "4", "5", "6")}
    assert len(set(b4.values())) == 4, ("naturalness band-4 not distinct per tier", b4)


# ---------------------------------------------------------------------------
# Carry-forward: descriptors-only bump on top of v5
# ---------------------------------------------------------------------------

def test_v6_changes_only_band_descriptors_vs_v5(v6, v5):
    assert set(v6) == set(v5), "v6 must carry exactly the v5 key set"
    for key in v6:
        if key == "band_descriptors":
            assert v6[key] != v5[key], "band_descriptors must change"
        else:
            assert v6[key] == v5[key], f"{key} must be carried forward from v5 unchanged"


def test_v6_scoring_keys_pinned_to_v5(v6):
    assert v6["severity_weights"] == {"minor": 1, "major": 5, "critical": 25}
    assert v6["understandability_weights"] == {"minor": 0, "major": 2, "critical": 25}
    assert {d: list(v6["band_thresholds"][d]) for d in DERIVED_DIMS} == {
        "accuracy": [1, 6, 15], "fidelity": [1, 6, 15], "understandability": [2, 6, 25],
    }


def test_compute_overall_band_reads_weights_without_keyerror(v6):
    for l2_code in L2_CODES:
        scores = {dim: 3 for dim in RUBRIC_DIMENSIONS}
        band = grader_cascade.compute_overall_band(scores, v6, l2_code)
        assert 1 <= band <= MAX_BAND
        assert grader_cascade.compute_overall_band(
            {dim: MAX_BAND for dim in RUBRIC_DIMENSIONS}, v6, l2_code
        ) == MAX_BAND


# ---------------------------------------------------------------------------
# Migration wrapper: version 6, single active row, guards, self-contained
# ---------------------------------------------------------------------------

def _executable_sql() -> str:
    return "\n".join(
        line for line in V6_PATH.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("--")
    )


def test_v6_seed_is_self_contained():
    sql = _executable_sql()
    assert "src.config" not in sql, "v6 must not derive its config from another row (TASK-636)"
    assert "FROM public.dt_rubric_version src" not in sql


def test_v6_seed_bumps_to_v6_single_active_row():
    sql = V6_PATH.read_text(encoding="utf-8")
    assert "VALUES (\n    6," in sql
    assert "SET is_active = false WHERE is_active AND version <> 6" in sql
    assert "ON CONFLICT (version) DO UPDATE" in sql
    do_update = sql.split("ON CONFLICT (version) DO UPDATE", 1)[1]
    assert "is_active = true" in do_update.split(";", 1)[0]


def test_v6_seed_guards_the_single_active_row_invariant():
    sql = _executable_sql()
    assert "WHERE is_active AND version > 6" in sql       # Guard 1: refuse downgrade
    assert "active_count <> 1" in sql                     # Guard 2: exactly one active
    assert "active_version <> 6" in sql                   # Guard 2: and it is v6
    assert sql.count("RAISE EXCEPTION") >= 3
    assert sql.index("BEGIN;") < sql.index("RAISE EXCEPTION") < sql.index("COMMIT;")
