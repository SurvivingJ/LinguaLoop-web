"""Shape tests for the TASK-616 localised taxonomy seeds (v2/v3/v4).

The Stage-4 successor to tests/test_dual_translation_taxonomy_seed.py (TASK-620,
the v1 baseline). These feed the *real* seeded taxonomies — extracted straight out
of migrations/dt_taxonomy_{en,ja,zh}_seed.sql (the exact artifacts applied live) —
through every production consumer access path, with no live DB:

  * grader_cascade.get_active_taxonomy       (load the active row's taxonomy)
  * grader_cascade._resolve_subtypes         (now via the pairs["<l1>-<l2>"] path, NOT the L2 fallback)
  * grader_cascade._resolve_subtype_labels   (subtype_glosses[subtype][l2])
  * grader_cascade.render_explanation        (templates[subtype][l1].format(...))
  * grader_cascade._decode_error             (numeric subtype index -> slug round-trip)

Acceptance criteria mirrored as assertions:
  * Subtypes resolved from config, per DIRECTED pair (each l1-l2 key present; every
    directed (l1,l2) resolves via the pair path, not the baseline fallback).
  * Cumulative EN->JA->ZH build: v2 adds the EN (l2=en) pairs, v3 the JA, v4 the ZH;
    pair-key sets are strictly nested (v2 < v3 < v4) and v4 carries all 6 directed pairs.
  * The localisation payload is real: enriched glosses/templates carry the language-
    specific content (article definiteness; は/が; teineigo/sonkeigo/kenjougo; 个/measure
    word; 了/过/着 aspect-not-tense).
  * Every subtype in every pair still has an L2 gloss + en/zh/ja templates; the model's
    subtype index round-trips back to the slug; seed is idempotent + single-active-row.

Weights are intentionally NOT here — the taxonomy carries none (see
tests/test_dual_translation_rubric_v2.py for the JA-fidelity / ZH-accuracy up-weight).
"""

import json
import pathlib
import re

import pytest

from services.dual_translation import grader_cascade, prompts

MIGRATIONS = pathlib.Path(__file__).resolve().parents[1] / "migrations"
SEED_FILES = {
    2: MIGRATIONS / "dt_taxonomy_en_seed.sql",
    3: MIGRATIONS / "dt_taxonomy_ja_seed.sql",
    4: MIGRATIONS / "dt_taxonomy_zh_seed.sql",
}
L2_CODES = ("zh", "en", "ja")
L1_CODES = ("zh", "en", "ja")
DIRECTED_PAIRS = [(l1, l2) for l2 in L2_CODES for l1 in L1_CODES if l1 != l2]


# ---------------------------------------------------------------------------
# Load the real seed shapes out of the SQL artifacts
# ---------------------------------------------------------------------------

def _load_sql(version: int) -> str:
    return SEED_FILES[version].read_text(encoding="utf-8")


def _load_taxonomy(version: int) -> dict:
    m = re.search(r"\$taxonomy\$(.*?)\$taxonomy\$", _load_sql(version), re.DOTALL)
    assert m, f"could not find the $taxonomy$...$taxonomy$ literal in the v{version} seed SQL"
    return json.loads(m.group(1))


@pytest.fixture(scope="module")
def taxonomies() -> dict:
    return {v: _load_taxonomy(v) for v in SEED_FILES}


@pytest.fixture(scope="module")
def final(taxonomies) -> dict:
    """The v4 (ZH) seed — the final localised taxonomy that ends up active."""
    return taxonomies[4]


@pytest.fixture(autouse=True)
def _clear_grader_cascade_caches():
    """get_active_taxonomy caches process-wide (TASK-642); drop it either side of
    every test so each seed version is really re-read rather than served from a
    sibling module's cached taxonomy."""
    grader_cascade.clear_caches()
    yield
    grader_cascade.clear_caches()


# Minimal fake Supabase query-builder returning the seeded taxonomy row (mirrors the
# baseline test), so the REAL get_active_taxonomy code runs end-to-end.
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
    def __init__(self, taxonomy):
        self._taxonomy = taxonomy

    def table(self, name):
        assert name == "dt_taxonomy_version", f"unexpected table read: {name!r}"
        return _FakeQuery([{"taxonomy": self._taxonomy}])


# ---------------------------------------------------------------------------
# get_active_taxonomy + top-level shape
# ---------------------------------------------------------------------------

def test_get_active_taxonomy_loads_final_seed(final):
    assert grader_cascade.get_active_taxonomy(_FakeDB(final)) == final


@pytest.mark.parametrize("version", sorted(SEED_FILES))
def test_top_level_keys_are_exactly_pairs_glosses_templates(taxonomies, version):
    assert set(taxonomies[version]) == {"pairs", "subtype_glosses", "templates"}


@pytest.mark.parametrize("version", sorted(SEED_FILES))
def test_category_source_severity_not_versioned(taxonomies, version):
    tax = taxonomies[version]
    for forbidden in ("category", "source", "severity"):
        assert forbidden not in tax
    assert "weights" not in tax, "taxonomy must carry no weights (they live in dt_rubric_version)"


# ---------------------------------------------------------------------------
# Per-directed-pair tables + cumulative EN->JA->ZH build
# ---------------------------------------------------------------------------

def test_cumulative_pair_keys_are_strictly_nested(taxonomies):
    k2 = set(taxonomies[2]["pairs"])
    k3 = set(taxonomies[3]["pairs"])
    k4 = set(taxonomies[4]["pairs"])
    assert k2 < k3 < k4, (k2, k3, k4)
    # each step introduces exactly the two directed pairs for that L2
    assert k3 - k2 == {f"{l1}-ja" for l1 in ("en", "zh")}
    assert k4 - k3 == {f"{l1}-zh" for l1 in ("en", "ja")}
    assert k2 - {"en", "ja", "zh"} == {f"{l1}-en" for l1 in ("ja", "zh")}


def test_final_has_all_six_directed_pairs_plus_baselines(final):
    expected = {"en", "ja", "zh"} | {f"{l1}-{l2}" for (l1, l2) in DIRECTED_PAIRS}
    assert set(final["pairs"]) == expected
    assert len(DIRECTED_PAIRS) == 6


@pytest.mark.parametrize("l1_code,l2_code", DIRECTED_PAIRS)
def test_every_directed_pair_resolves_via_the_pair_path(final, l1_code, l2_code):
    pair_key = f"{l1_code}-{l2_code}"
    assert pair_key in final["pairs"], "acceptance: per-directed-pair table must exist"
    resolved = grader_cascade._resolve_subtypes(final, l1_code, l2_code)
    assert resolved == final["pairs"][pair_key]["subtypes"]
    # the pair list mirrors its L2 baseline set/order (guarantees gloss+template coverage)
    assert resolved == final["pairs"][l2_code]["subtypes"]


# ---------------------------------------------------------------------------
# Glosses + templates: full coverage, index round-trip
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("l2_code", L2_CODES)
def test_every_subtype_has_a_gloss(final, l2_code):
    subs = final["pairs"][l2_code]["subtypes"]
    labels = grader_cascade._resolve_subtype_labels(final, subs, l2_code)
    for st, label in zip(subs, labels):
        assert label == final["subtype_glosses"][st][l2_code], (l2_code, st)
        assert label != st, f"{st}/{l2_code} fell back to the bare English slug (missing gloss)"


@pytest.mark.parametrize("l1_code", L1_CODES)
def test_render_explanation_no_fallback_and_substitutes_forms(final, l1_code):
    all_subtypes = {st for blk in final["pairs"].values() for st in blk["subtypes"]}
    for st in sorted(all_subtypes):
        text, used_fallback = grader_cascade.render_explanation(
            final, st, l1_code, learner_form="LEARNER_X", corrected_form="CORRECT_Y"
        )
        assert not used_fallback, f"{st}/{l1_code} used the generic fallback (missing template)"
        assert "LEARNER_X" in text and "CORRECT_Y" in text, (st, l1_code)


@pytest.mark.parametrize("l1_code,l2_code", DIRECTED_PAIRS)
def test_subtype_index_round_trips_through_decode_error(final, l1_code, l2_code):
    subs = grader_cascade._resolve_subtypes(final, l1_code, l2_code)
    for i, slug in enumerate(subs):
        raw = {
            "span_repro": [0, 1], "span_ref": [0, 1],
            "category": 0, "source": 0, "severity": 0,
            "subtype": i, "learner_form": "L", "corrected_form": "C",
            "confidence": 0.9, "is_mistake": False,
        }
        decoded = grader_cascade._decode_error(raw, subs, final, l1_code, "L", "C")
        assert decoded is not None, (l1_code, l2_code, i)
        assert decoded["subtype"] == slug, (l1_code, l2_code, i, slug)
        assert decoded["category"] == prompts.CATEGORY_ENUM[0]
        assert decoded["explanation"], (l1_code, l2_code, i)


# ---------------------------------------------------------------------------
# The localisation payload is REAL — language-specific enriched content
# ---------------------------------------------------------------------------

def test_en_article_and_preposition_enriched(final):
    art = final["subtype_glosses"]["article"]["en"]
    assert "definiteness" in art and "a/an/the" in art
    art_tmpl = final["templates"]["article"]["en"]
    assert "definiteness" in art_tmpl.lower() or "the" in art_tmpl
    prep = final["templates"]["preposition"]["en"]
    assert "depend on" in prep or "interested in" in prep


def test_ja_particle_and_keigo_enriched(final):
    particle_en = final["templates"]["particle"]["en"]
    assert "は" in particle_en and "が" in particle_en, "は/が contrast must be spelled out"
    keigo_en = final["templates"]["keigo_register"]["en"]
    for level in ("teineigo", "sonkeigo", "kenjougo"):
        assert level in keigo_en, f"keigo template must name {level}"
    # keigo gloss shown to the JA-grading model names the three registers
    keigo_gloss = final["subtype_glosses"]["keigo_register"]["ja"]
    assert "丁寧語" in keigo_gloss and "尊敬語" in keigo_gloss and "謙譲語" in keigo_gloss


def test_zh_classifier_and_aspect_enriched(final):
    cls_en = final["templates"]["classifier"]["en"]
    assert "个" in cls_en and "measure word" in cls_en
    asp_en = final["templates"]["aspect_marker"]["en"]
    assert "了" in asp_en and "过" in asp_en and "着" in asp_en
    assert "aspect" in asp_en.lower() and "tense" in asp_en.lower()


# ---------------------------------------------------------------------------
# Seed migration safety: version bump + single-active-row + idempotency
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("version", sorted(SEED_FILES))
def test_seed_bumps_version_and_keeps_single_active_row(version):
    sql = _load_sql(version)
    assert f"VALUES (\n    {version}," in sql, "must INSERT this exact version"
    # deactivate every other active row before activating this one
    assert f"SET is_active = false WHERE is_active AND version <> {version}" in sql
    # idempotent re-apply keeps THIS version active
    assert "ON CONFLICT (version) DO UPDATE" in sql
    do_update = sql.split("ON CONFLICT (version) DO UPDATE", 1)[1]
    assert "is_active = true" in do_update.split(";", 1)[0]
