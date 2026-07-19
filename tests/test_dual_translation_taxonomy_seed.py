"""Shape tests for the taxonomy v1 baseline seed (TASK-620).

The taxonomy twin of tests/test_dual_translation_rubric_seed.py. These feed the
*real* seeded taxonomy — extracted straight out of
``migrations/dt_taxonomy_v1_seed.sql`` (the exact artifact applied live) — through
every production consumer access path, with no live DB:

  * ``grader_cascade.get_active_taxonomy``       (load: is_active row's taxonomy)
  * ``grader_cascade._resolve_subtypes``         (pairs["<l1>-<l2>"] -> "<l2>" fallback)
  * ``grader_cascade._resolve_subtype_labels``   (subtype_glosses[subtype][l2])
  * ``grader_cascade.render_explanation``        (templates[subtype][l1].format(...))
  * ``grader_cascade._decode_error``             (numeric subtype index -> slug round-trip)

The point is to catch a config-shape regression here, before the live apply and
before any OpenRouter spend. Acceptance criteria mirrored as assertions:
category/source/severity NOT in taxonomy; an <l2>-baseline per L2 with no per-pair
key (every (l1,l2) resolves via the fallback path); every subtype has an L2 gloss
and en/zh/ja templates; the model's subtype index round-trips back to the slug;
seed is idempotent and activates exactly v1.
"""

import json
import pathlib
import re

import pytest

from services.dual_translation import grader_cascade, prompts

SEED_PATH = pathlib.Path(__file__).resolve().parents[1] / "migrations" / "dt_taxonomy_v1_seed.sql"
# The languages live in dim_languages today (no 'es' row): every L1 and every L2
# the cascade can actually receive is one of these three.
L2_CODES = ("zh", "en", "ja")
L1_CODES = ("zh", "en", "ja")


# ---------------------------------------------------------------------------
# Load the real seed shape out of the SQL artifact
# ---------------------------------------------------------------------------

def _load_seed_sql() -> str:
    return SEED_PATH.read_text(encoding="utf-8")


def _load_seed_taxonomy() -> dict:
    sql = _load_seed_sql()
    m = re.search(r"\$taxonomy\$(.*?)\$taxonomy\$", sql, re.DOTALL)
    assert m, "could not find the dollar-quoted ($taxonomy$...$taxonomy$) literal in the seed SQL"
    return json.loads(m.group(1))


@pytest.fixture(scope="module")
def taxonomy() -> dict:
    return _load_seed_taxonomy()


@pytest.fixture(autouse=True)
def _clear_grader_cascade_caches():
    """get_active_taxonomy caches process-wide (TASK-642); drop it either side of
    every test so these _FakeDB reads actually hit the real query code and don't
    leak a taxonomy into another module's tests."""
    grader_cascade.clear_caches()
    yield
    grader_cascade.clear_caches()


# ---------------------------------------------------------------------------
# Minimal fake Supabase query-builder returning the seeded taxonomy row, so the
# REAL get_active_taxonomy code runs end-to-end (mirrors the rubric seed test).
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
    """Returns a single active dt_taxonomy_version row carrying the seeded taxonomy."""

    def __init__(self, taxonomy):
        self._taxonomy = taxonomy

    def table(self, name):
        assert name == "dt_taxonomy_version", f"unexpected table read: {name!r}"
        return _FakeQuery([{"taxonomy": self._taxonomy}])


# ---------------------------------------------------------------------------
# get_active_taxonomy — loads without raising
# ---------------------------------------------------------------------------

def test_get_active_taxonomy_loads_seed_without_raising(taxonomy):
    loaded = grader_cascade.get_active_taxonomy(_FakeDB(taxonomy))
    assert loaded == taxonomy


def test_top_level_keys_are_exactly_pairs_glosses_templates(taxonomy):
    assert set(taxonomy) == {"pairs", "subtype_glosses", "templates"}


def test_category_source_severity_are_not_versioned_here(taxonomy):
    """Acceptance: those three are hardcoded enums + dt_error_instance CHECK; only
    `subtype` is versioned in the taxonomy."""
    for forbidden in ("category", "source", "severity"):
        assert forbidden not in taxonomy, forbidden
    # also not smuggled in as a pairs key
    assert "category" not in taxonomy["pairs"]


# ---------------------------------------------------------------------------
# pairs: an <l2>-baseline per L2, and NO per-pair "<l1>-<l2>" key (fallback path)
# ---------------------------------------------------------------------------

def test_every_l2_has_a_baseline_and_no_per_pair_keys(taxonomy):
    pairs = taxonomy["pairs"]
    assert set(pairs) == set(L2_CODES), pairs.keys()
    # baseline-only: a per-pair table would contain a '-' (e.g. "ja-en"); TASK-616 adds those
    assert all("-" not in k for k in pairs), "baseline seed must not carry per-pair keys"
    for l2 in L2_CODES:
        subs = pairs[l2]["subtypes"]
        assert subs, l2
        assert len(subs) == len(set(subs)), f"duplicate subtype in {l2}: {subs}"


@pytest.mark.parametrize("l1_code", L1_CODES)
@pytest.mark.parametrize("l2_code", L2_CODES)
def test_resolve_subtypes_uses_l2_baseline_fallback(taxonomy, l1_code, l2_code):
    """No per-pair key exists, so EVERY (l1,l2) must resolve via the <l2> baseline
    fallback without raising."""
    subs = grader_cascade._resolve_subtypes(taxonomy, l1_code, l2_code)
    assert subs == taxonomy["pairs"][l2_code]["subtypes"], (l1_code, l2_code)


# ---------------------------------------------------------------------------
# subtype_glosses: every baseline subtype has an L2 gloss (no bare-slug fallback)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("l2_code", L2_CODES)
def test_resolve_subtype_labels_has_a_gloss_for_every_subtype(taxonomy, l2_code):
    subs = taxonomy["pairs"][l2_code]["subtypes"]
    labels = grader_cascade._resolve_subtype_labels(taxonomy, subs, l2_code)
    assert len(labels) == len(subs)
    for st, label in zip(subs, labels):
        # a missing gloss would fall back to the bare English slug — assert it did NOT
        assert label == taxonomy["subtype_glosses"][st][l2_code], (l2_code, st)
        assert label != st, f"{st}/{l2_code} fell back to the bare slug (missing gloss)"


# ---------------------------------------------------------------------------
# templates: every subtype renders in every L1 with both forms substituted
# ---------------------------------------------------------------------------

def _all_subtypes(taxonomy) -> set:
    return {st for blk in taxonomy["pairs"].values() for st in blk["subtypes"]}


@pytest.mark.parametrize("l1_code", L1_CODES)
def test_render_explanation_no_fallback_and_substitutes_forms(taxonomy, l1_code):
    for st in sorted(_all_subtypes(taxonomy)):
        text, used_fallback = grader_cascade.render_explanation(
            taxonomy, st, l1_code, learner_form="LEARNER_X", corrected_form="CORRECT_Y"
        )
        assert not used_fallback, f"{st}/{l1_code} used the generic fallback (missing template)"
        assert "LEARNER_X" in text and "CORRECT_Y" in text, (st, l1_code)


def test_render_explanation_uses_generic_fallback_for_unknown_subtype(taxonomy):
    """Sanity check the fallback path itself still works for a subtype with no template."""
    text, used_fallback = grader_cascade.render_explanation(
        taxonomy, "does_not_exist", "en", learner_form="L", corrected_form="C"
    )
    assert used_fallback and "C" in text


# ---------------------------------------------------------------------------
# _decode_error: the model's numeric subtype index round-trips back to the slug
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("l1_code", L1_CODES)
@pytest.mark.parametrize("l2_code", L2_CODES)
def test_subtype_index_round_trips_through_decode_error(taxonomy, l1_code, l2_code):
    subs = grader_cascade._resolve_subtypes(taxonomy, l1_code, l2_code)
    for i, slug in enumerate(subs):
        raw = {
            "span_repro": [0, 1],
            "span_ref": [0, 1],
            "category": 0,   # -> grammatical
            "source": 0,     # -> interlingual
            "severity": 0,   # -> minor
            "subtype": i,    # numeric index, as the model emits it
            "learner_form": "L",
            "corrected_form": "C",
            "confidence": 0.9,
            "is_mistake": False,
        }
        decoded = grader_cascade._decode_error(raw, subs, taxonomy, l1_code, "L", "C")
        assert decoded is not None, (l1_code, l2_code, i)
        assert decoded["subtype"] == slug, (l1_code, l2_code, i, slug)
        assert decoded["category"] == prompts.CATEGORY_ENUM[0]
        assert decoded["explanation"], (l1_code, l2_code, i)


def test_out_of_range_subtype_index_is_dropped(taxonomy):
    subs = taxonomy["pairs"]["en"]["subtypes"]
    raw = {
        "span_repro": [0, 1], "span_ref": [0, 1],
        "category": 0, "source": 0, "severity": 0,
        "subtype": len(subs),  # one past the end -> out of range
        "learner_form": "L", "corrected_form": "C", "confidence": 0.5,
    }
    assert grader_cascade._decode_error(raw, subs, taxonomy, "en", "L", "C") is None


# ---------------------------------------------------------------------------
# Idempotency / single-active-row safety of the seed migration itself
# ---------------------------------------------------------------------------

def test_seed_is_idempotent_and_activates_v1():
    sql = _load_seed_sql()
    assert "INSERT INTO public.dt_taxonomy_version" in sql
    assert "true," in sql  # is_active set true on the initial insert
    # Re-apply is an in-place upsert keyed on version -> no duplicate / no second active row
    assert "ON CONFLICT (version) DO UPDATE" in sql
    # The DO UPDATE clause must NOT re-set is_active (so re-applying after a later
    # version supersedes v1 cannot silently re-activate v1).
    do_update = sql.split("ON CONFLICT (version) DO UPDATE", 1)[1]
    assert "is_active" not in do_update.split(";", 1)[0]
