"""Shape tests for the rubric v1 seed (TASK-604).

These feed the *real* seeded config — extracted straight out of
``migrations/dt_rubric_v1_seed.sql`` (the exact artifact applied live) — through
both production consumer access paths, with no live DB:

  * ``services.dual_translation.grader_cascade.get_active_rubric`` (load) and
    ``compute_overall_band`` (weights: ``config.weights.default[dim]`` +
    ``config.weights.by_language[l2][dim]``).
  * ``routes.dual_translation._rubric_descriptors_for`` (feed-up:
    ``config.band_descriptors[str(age_tier)][dim][l2] -> {band: text}``) and
    ``services.dual_translation.prompts._band_descriptors_text`` (the strictest
    leaf reader — it iterates ``bands.items()``).

The point is to catch a config-shape regression here, before the live apply and
before any OpenRouter spend. Acceptance criteria mirrored as assertions: age
tiers (not CEFR); understandability+accuracy highest weight, naturalness lowest
and absent at tiers 1-2; both access paths KeyError-free; seed is idempotent.
"""

import json
import pathlib
import re

import pytest

import routes.dual_translation as dt_routes
from services.dual_translation import grader_cascade, prompts
from services.dual_translation.tier0 import RUBRIC_DIMENSIONS, MAX_BAND

SEED_PATH = pathlib.Path(__file__).resolve().parents[1] / "migrations" / "dt_rubric_v1_seed.sql"
L2_CODES = ("zh", "en", "ja")
TIERS = (1, 2, 3, 4, 5, 6)
BANDS = {"1", "2", "3", "4"}


# ---------------------------------------------------------------------------
# Load the real seed shape out of the SQL artifact
# ---------------------------------------------------------------------------

def _load_seed_sql() -> str:
    return SEED_PATH.read_text(encoding="utf-8")


def _load_seed_config() -> dict:
    sql = _load_seed_sql()
    m = re.search(r"\$rubric\$(.*?)\$rubric\$", sql, re.DOTALL)
    assert m, "could not find the dollar-quoted ($rubric$...$rubric$) config literal in the seed SQL"
    return json.loads(m.group(1))


@pytest.fixture(scope="module")
def seed_config() -> dict:
    return _load_seed_config()


# ---------------------------------------------------------------------------
# Minimal fake Supabase query-builder returning the seeded rubric row, so the
# REAL get_active_rubric / _rubric_descriptors_for code runs end-to-end.
# ---------------------------------------------------------------------------

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
    """Returns a single active dt_rubric_version row carrying the seeded config."""

    def __init__(self, config):
        self._config = config

    def table(self, name):
        assert name == "dt_rubric_version", f"unexpected table read: {name!r}"
        return _FakeQuery([{"config": self._config}])


def _effective_weights(config, l2_code):
    """Replicates grader_cascade.compute_overall_band's weight resolution."""
    weights = config["weights"]
    default = weights["default"]
    overrides = weights.get("by_language", {}).get(l2_code, {})
    return {dim: overrides.get(dim, default[dim]) for dim in RUBRIC_DIMENSIONS}


# ---------------------------------------------------------------------------
# get_active_rubric — loads without raising
# ---------------------------------------------------------------------------

def test_get_active_rubric_loads_seed_without_raising(seed_config):
    loaded = grader_cascade.get_active_rubric(_FakeDB(seed_config))
    assert loaded == seed_config
    assert set(loaded) == {"weights", "band_descriptors"}


# ---------------------------------------------------------------------------
# Weights: understandability+accuracy highest, naturalness lowest, per language
# ---------------------------------------------------------------------------

def test_default_weights_cover_all_five_dimensions(seed_config):
    default = seed_config["weights"]["default"]
    assert set(default) == set(RUBRIC_DIMENSIONS)


@pytest.mark.parametrize("l2_code", L2_CODES)
def test_weight_ordering_invariant(seed_config, l2_code):
    eff = _effective_weights(seed_config, l2_code)
    top2 = {dim for dim, _ in sorted(eff.items(), key=lambda kv: kv[1], reverse=True)[:2]}
    assert top2 == {"accuracy", "understandability"}, (l2_code, eff)
    assert eff["naturalness"] == min(eff.values()), (l2_code, eff)
    assert all(eff["naturalness"] < eff[d] for d in eff if d != "naturalness"), (l2_code, eff)


def test_per_language_overrides_match_documented_philosophy(seed_config):
    by_lang = seed_config["weights"]["by_language"]
    default = seed_config["weights"]["default"]
    # JA up-weights fidelity (particle / keigo register), ZH up-weights accuracy
    # (classifier / aspect) — relative to the default vector.
    assert _effective_weights(seed_config, "ja")["fidelity"] > default["fidelity"]
    assert _effective_weights(seed_config, "zh")["accuracy"] > default["accuracy"]
    assert set(by_lang) <= set(L2_CODES)


@pytest.mark.parametrize("l2_code", L2_CODES)
def test_compute_overall_band_reads_weights_without_keyerror(seed_config, l2_code):
    scores = {dim: 3 for dim in RUBRIC_DIMENSIONS}
    band = grader_cascade.compute_overall_band(scores, seed_config, l2_code)
    assert 1 <= band <= MAX_BAND
    # all-4 must collapse to band 4 regardless of weights
    assert grader_cascade.compute_overall_band(
        {dim: MAX_BAND for dim in RUBRIC_DIMENSIONS}, seed_config, l2_code
    ) == MAX_BAND


# ---------------------------------------------------------------------------
# Band descriptors: full grid, naturalness hidden at tiers 1-2, age-tier keyed
# ---------------------------------------------------------------------------

def test_band_descriptors_cover_all_six_tiers(seed_config):
    assert set(seed_config["band_descriptors"]) == {str(t) for t in TIERS}


@pytest.mark.parametrize("tier", TIERS)
@pytest.mark.parametrize("l2_code", L2_CODES)
def test_rubric_descriptors_for_reads_without_keyerror(seed_config, tier, l2_code):
    """The routes feed-up access path: band_descriptors[tier][dim][l2] -> {band: text}."""
    descriptors = dt_routes._rubric_descriptors_for(_FakeDB(seed_config), tier, l2_code)
    assert descriptors, (tier, l2_code)
    for dim, leaf in descriptors.items():
        assert isinstance(leaf, dict) and set(leaf) == BANDS, (tier, l2_code, dim, leaf)
    if tier in (1, 2):
        assert "naturalness" not in descriptors, (tier, "naturalness must be hidden at tiers 1-2")
    else:
        assert "naturalness" in descriptors, (tier, l2_code)


def test_naturalness_absent_in_raw_config_at_low_tiers(seed_config):
    bd = seed_config["band_descriptors"]
    assert "naturalness" not in bd["1"]
    assert "naturalness" not in bd["2"]
    for tier in ("3", "4", "5", "6"):
        assert "naturalness" in bd[tier], tier


@pytest.mark.parametrize("tier", TIERS)
@pytest.mark.parametrize("l2_code", L2_CODES)
def test_prompts_band_descriptors_text_renders(seed_config, tier, l2_code):
    """The strictest leaf reader (iterates bands.items()) must render non-empty
    text for every graded dimension at this tier."""
    graded = [d for d in RUBRIC_DIMENSIONS
              if not (d == "naturalness" and tier in (1, 2))]
    text = prompts._band_descriptors_text(seed_config, tuple(graded), tier, l2_code)
    assert text.strip(), (tier, l2_code)
    # one bullet line per graded dimension
    assert text.count("- ") == len(graded), (tier, l2_code, text)


# ---------------------------------------------------------------------------
# Age tiers, not CEFR (acceptance criterion)
# ---------------------------------------------------------------------------

def test_descriptors_reference_age_tiers_not_cefr(seed_config):
    cefr_token = re.compile(r"\b(?:CEFR|[ABC][12])\b")
    for tier, dims in seed_config["band_descriptors"].items():
        for dim, per_lang in dims.items():
            for l2_code, bands in per_lang.items():
                for band, text in bands.items():
                    assert "cefr" not in text.lower(), (tier, dim, l2_code, band, text)
                    assert not cefr_token.search(text), (tier, dim, l2_code, band, text)


# ---------------------------------------------------------------------------
# Idempotency / single-active-row safety of the seed migration itself
# ---------------------------------------------------------------------------

def test_seed_is_idempotent_and_activates_v1():
    sql = _load_seed_sql()
    # version=1, activated on insert
    assert "INSERT INTO public.dt_rubric_version" in sql
    assert "true," in sql  # is_active set true on the initial insert
    # Re-apply is an in-place upsert keyed on version → no duplicate / no second active row
    assert "ON CONFLICT (version) DO UPDATE" in sql
    # The DO UPDATE clause must NOT re-set is_active (so re-applying after a later
    # version supersedes v1 cannot silently re-activate v1).
    do_update = sql.split("ON CONFLICT (version) DO UPDATE", 1)[1]
    assert "is_active" not in do_update.split(";", 1)[0]
