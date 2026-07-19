"""Shape / totality / alias-resolution tests for the TASK-626 taxonomy v5 seed.

v5 grows each L2's subtype set to the tech-spec §5 sizes (EN 15 / JA 17 / ZH 17),
adds the new top-level `subtype_meta` key (dimension / default_severity /
treatable / cloze_suitable — the machinery TASK-627 derived scoring reads), and
authors per-L2 glosses + per-L1 Rule templates so no live prompt falls back to a
bare English slug.

These tests extract the taxonomy straight out of migrations/dt_taxonomy_v5_seed.sql
(the file is the source of truth for the seed) and prove:
  * shape: exactly the four top-level keys, incl. the NEW subtype_meta
  * per-L2 subtype lists match §5 exactly (sizes + membership + order = decode index)
  * subtype_meta totality: every subtype maps to exactly one of
    accuracy/fidelity/naturalness with a minor|major default_severity
  * every seeded (pair) subtype has a gloss in its L2 and a template in all 3 L1s —
    verified through the REAL grader_cascade resolution functions (no fallback logs)
  * historical alias `particle` still resolves (kept in subtype_meta, absent from
    every pairs list) so v1–v4 stored dt_error_instance rows decode under TASK-627
  * seed migration safety (single-active-row bump to v5)

Sibling seed tests (test_dual_translation_taxonomy_seed.py = v1,
test_dual_translation_taxonomy_localised.py = v2–v4) assert the older files still
carry exactly {pairs, glosses, templates}; this file is the v5 counterpart and is
the only one that expects the fourth `subtype_meta` key.
"""

import json
import pathlib
import re

import pytest

from services.dual_translation import grader_cascade

MIGRATIONS = pathlib.Path(__file__).resolve().parents[1] / "migrations"
V5_PATH = MIGRATIONS / "dt_taxonomy_v5_seed.sql"

L1S = ("en", "ja", "zh")
DIMENSIONS = {"accuracy", "fidelity", "naturalness"}

# §5 canonical sets (shared core 8 + per-target). Order matters — the list index
# IS the _decode_error subtype contract, so this pins order, not just membership.
CORE = ["omission", "addition", "word_choice", "collocation",
        "word_order", "register", "orthography", "cohesion_connective"]
EN_LIST = CORE + ["article", "preposition", "tense_aspect", "subject_verb_agreement",
                  "plural_number", "phrasal_verb", "pronoun_reference"]
JA_LIST = CORE + ["particle_wa_ga", "particle_case", "particle_other", "verb_conjugation",
                  "tense_aspect_ja", "keigo_register", "counter_classifier",
                  "script_choice", "topic_comment"]
ZH_LIST = CORE + ["classifier", "aspect_marker", "de_particles", "ba_construction",
                  "bei_passive", "resultative_complement", "directional_complement",
                  "adverbial_order", "topic_comment"]

# directed pair -> (l1, expected subtype list)
DIRECTED = {
    "en-ja": ("en", JA_LIST), "zh-ja": ("zh", JA_LIST),
    "en-zh": ("en", ZH_LIST), "ja-zh": ("ja", ZH_LIST),
    "ja-en": ("ja", EN_LIST), "zh-en": ("zh", EN_LIST),
}
BASELINES = {"en": EN_LIST, "ja": JA_LIST, "zh": ZH_LIST}

# §5 dimension + default_severity assignments (authoritative). treatable /
# cloze_suitable are project judgment (adjudicated), asserted only for type.
EXPECTED_META = {
    "omission": ("fidelity", "major"), "addition": ("fidelity", "minor"),
    "word_choice": ("fidelity", "minor"), "collocation": ("naturalness", "minor"),
    "word_order": ("accuracy", "major"), "register": ("fidelity", "major"),
    "orthography": ("accuracy", "minor"), "cohesion_connective": ("naturalness", "minor"),
    "article": ("accuracy", "minor"), "preposition": ("accuracy", "minor"),
    "tense_aspect": ("accuracy", "major"), "subject_verb_agreement": ("accuracy", "minor"),
    "plural_number": ("accuracy", "minor"), "phrasal_verb": ("fidelity", "minor"),
    "pronoun_reference": ("accuracy", "major"),
    "particle_wa_ga": ("accuracy", "major"), "particle_case": ("accuracy", "major"),
    "particle_other": ("accuracy", "minor"), "verb_conjugation": ("accuracy", "major"),
    "tense_aspect_ja": ("accuracy", "major"), "keigo_register": ("fidelity", "major"),
    "counter_classifier": ("accuracy", "minor"), "script_choice": ("accuracy", "minor"),
    "topic_comment": ("naturalness", "minor"),
    "classifier": ("accuracy", "minor"), "aspect_marker": ("accuracy", "major"),
    "de_particles": ("accuracy", "minor"), "ba_construction": ("accuracy", "major"),
    "bei_passive": ("accuracy", "major"), "resultative_complement": ("accuracy", "major"),
    "directional_complement": ("accuracy", "minor"), "adverbial_order": ("accuracy", "major"),
}


def _extract_taxonomy(path: pathlib.Path) -> dict:
    m = re.search(r"\$taxonomy\$(.*?)\$taxonomy\$", path.read_text(encoding="utf-8"), re.DOTALL)
    assert m, f"could not find the $taxonomy$...$taxonomy$ literal in {path.name}"
    return json.loads(m.group(1))


@pytest.fixture(scope="module")
def tax() -> dict:
    return _extract_taxonomy(V5_PATH)


# ---------------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------------

def test_top_level_shape_adds_subtype_meta(tax):
    assert set(tax.keys()) == {"pairs", "subtype_meta", "subtype_glosses", "templates"}


def test_all_nine_pairs_present(tax):
    assert set(tax["pairs"]) == set(DIRECTED) | set(BASELINES)


@pytest.mark.parametrize("pair,expected", [
    *[(p, exp) for p, (_l1, exp) in DIRECTED.items()],
    *[(p, exp) for p, exp in BASELINES.items()],
])
def test_pair_subtype_lists_match_spec_exactly(tax, pair, expected):
    # membership AND order (index = decode contract) AND size (15/17/17)
    assert tax["pairs"][pair]["subtypes"] == expected


# ---------------------------------------------------------------------------
# subtype_meta totality
# ---------------------------------------------------------------------------

def test_subtype_meta_totality_over_every_pair_subtype(tax):
    meta = tax["subtype_meta"]
    seen = set()
    for pair, spec in tax["pairs"].items():
        for st in spec["subtypes"]:
            seen.add(st)
            assert st in meta, f"{st} (in pair {pair}) missing from subtype_meta"
            m = meta[st]
            assert m["dimension"] in DIMENSIONS, f"{st}.dimension={m['dimension']!r}"
            assert m["default_severity"] in ("minor", "major"), f"{st}.default_severity"
            assert isinstance(m["treatable"], bool)
            assert isinstance(m["cloze_suitable"], bool)
    # exactly the 32 distinct pair subtypes (topic_comment shared JA+ZH)
    assert len(seen) == 32


def test_subtype_meta_dimension_and_default_severity_match_spec(tax):
    meta = tax["subtype_meta"]
    for st, (dim, sev) in EXPECTED_META.items():
        assert meta[st]["dimension"] == dim, f"{st} dimension"
        assert meta[st]["default_severity"] == sev, f"{st} default_severity"


def test_default_severity_speaks_triad_not_global_local(tax):
    # post-TASK-625: no retired global/local anywhere in default_severity
    for st, m in tax["subtype_meta"].items():
        assert m["default_severity"] not in ("global", "local"), st


# ---------------------------------------------------------------------------
# Historical alias: `particle` resolves, is not a live subtype
# ---------------------------------------------------------------------------

def test_particle_alias_kept_in_meta_but_absent_from_pairs(tax):
    meta = tax["subtype_meta"]
    assert "particle" in meta, "historical alias `particle` must stay in subtype_meta"
    assert meta["particle"]["dimension"] == "accuracy"
    assert meta["particle"].get("historical_alias") is True
    for pair, spec in tax["pairs"].items():
        assert "particle" not in spec["subtypes"], f"`particle` leaked into pair {pair}"


def test_live_historical_subtypes_all_resolve_in_meta(tax):
    # the four subtype names currently stored in live dt_error_instance
    for st in ("word_choice", "omission", "word_order", "aspect_marker"):
        assert st in tax["subtype_meta"]
        assert tax["subtype_meta"][st]["dimension"] in DIMENSIONS


def test_subtype_meta_has_exactly_33_entries(tax):
    # 32 distinct pair subtypes + the `particle` alias
    assert len(tax["subtype_meta"]) == 33


# ---------------------------------------------------------------------------
# No live prompt falls back to a bare slug — via the REAL resolution functions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pair,l1", [(p, l1) for p, (l1, _e) in DIRECTED.items()])
def test_directed_pair_resolves_subtypes_glosses_and_templates(tax, pair, l1):
    l2 = pair.split("-")[1]
    subtypes = grader_cascade._resolve_subtypes(tax, l1, l2)
    assert subtypes == DIRECTED[pair][1]

    # every gloss is a real L2 gloss, never the bare slug fallback
    labels = grader_cascade._resolve_subtype_labels(tax, subtypes, l2)
    assert len(labels) == len(subtypes)
    for st, label in zip(subtypes, labels):
        assert label and label != st, f"{st} fell back to bare slug in {l2} gloss"

    # every (subtype, l1) renders from a template, never the generic fallback
    for st in subtypes:
        text, used_fallback = grader_cascade.render_explanation(
            tax, st, l1, learner_form="X", corrected_form="Y")
        assert not used_fallback, f"template[{st}][{l1}] missing (pair {pair})"
        assert text


@pytest.mark.parametrize("l2,expected", list(BASELINES.items()))
def test_baseline_pairs_resolve_for_every_l1(tax, l2, expected):
    # baselines are the fallback when pairs[l1-l2] is absent (incl. l1==l2);
    # they must resolve glosses + templates for all three possible L1s.
    subtypes = grader_cascade._resolve_subtypes(tax, l2, l2)  # forces baseline
    assert subtypes == expected
    for l1 in L1S:
        for st in subtypes:
            _text, used_fallback = grader_cascade.render_explanation(
                tax, st, l1, learner_form="X", corrected_form="Y")
            assert not used_fallback, f"template[{st}][{l1}] missing (baseline {l2})"


# ---------------------------------------------------------------------------
# JA particle three-way split present (re-adjudication, not rename)
# ---------------------------------------------------------------------------

def test_ja_particle_split_present_and_old_name_gone_from_pairs(tax):
    ja = tax["pairs"]["ja"]["subtypes"]
    assert {"particle_wa_ga", "particle_case", "particle_other"} <= set(ja)
    assert "particle" not in ja


# ---------------------------------------------------------------------------
# Seed migration safety
# ---------------------------------------------------------------------------

def test_seed_bumps_to_v5_single_active_row():
    sql = V5_PATH.read_text(encoding="utf-8")
    assert "VALUES (\n    5," in sql
    assert "SET is_active = false WHERE is_active AND version <> 5" in sql
    assert "ON CONFLICT (version) DO UPDATE" in sql
    do_update = sql.split("ON CONFLICT (version) DO UPDATE", 1)[1]
    assert "is_active = true" in do_update.split(";", 1)[0]
