"""Gold-seed helper tests: scoring-config resolution + spec shape (TASK-641).

`scripts/dt_gold_seed_helper.py` derives the frozen `expected_bands` in
tests/fixtures/dt_gold/ from severity-weighted penalties. Those weights/thresholds
are ALSO destined for `dt_rubric_version.config` under the `severity_weights` /
`understandability_weights` / `band_thresholds` keys that TASK-627 reserves (see the
dt_rubric_v4_seed.sql header) — which is exactly how the gold set and the live grader
could come to disagree while both look healthy.

The load-bearing test here is `test_seeded_scoring_config_matches_pinned_fallback`:
it is inert today (no rubric seed carries those keys yet) and starts biting the
moment TASK-627 seeds them with values that differ from the pinned fallback. When
it fires, the fixtures' expected_bands must be re-derived — do not just edit the
constants to match.
"""

import json
import pathlib
import re

import pytest

from scripts.dt_gold_seed_helper import (
    DERIVED_DIMENSIONS,
    OFFLINE_SCORING_CONFIG,
    SCORING_KEYS,
    SEVERITIES,
    build_item,
    derive_bands,
    scoring_config,
)

REPO = pathlib.Path(__file__).resolve().parents[1]
MIGRATIONS = REPO / "migrations"
FIXTURE_DIR = REPO / "tests" / "fixtures" / "dt_gold"
L2_CODES = ("en", "ja", "zh")


# ---------------------------------------------------------------------------
# Pinning: the live seed must not drift away from the offline fallback
# ---------------------------------------------------------------------------

def _dollar_quoted_configs(sql: str) -> list[dict]:
    """Every dollar-quoted ($tag$...$tag$) JSON literal in a seed migration."""
    out = []
    for _, body in re.findall(r"\$(\w+)\$(.*?)\$\1\$", sql, re.DOTALL):
        try:
            parsed = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            continue  # non-JSON dollar-quoted block (e.g. a DO $guard$ body)
        if isinstance(parsed, dict):
            out.append(parsed)
    return out


def _seeded_scoring_configs() -> list[tuple[str, dict]]:
    """(migration name, config) for every rubric seed carrying the TASK-627 keys."""
    found = []
    for path in sorted(MIGRATIONS.glob("dt_rubric_v*_seed.sql")):
        for cfg in _dollar_quoted_configs(path.read_text(encoding="utf-8")):
            if any(k in cfg for k in SCORING_KEYS):
                found.append((path.name, cfg))
    return found


def test_seeded_scoring_config_matches_pinned_fallback():
    """Once TASK-627 seeds the scoring keys, they must agree with the constants the
    frozen fixtures were derived under — else the gold set's expected_bands and the
    live grader silently disagree."""
    seeded = _seeded_scoring_configs()
    if not seeded:
        pytest.skip(f"no rubric seed carries {list(SCORING_KEYS)} yet (TASK-627 pending)")
    for name, cfg in seeded:
        resolved = scoring_config(cfg)
        for key in ("severity_weights", "understandability_weights"):
            assert resolved[key] == OFFLINE_SCORING_CONFIG[key], (
                f"{name}: seeded {key} differ from the pinned fallback — "
                "re-derive tests/fixtures/dt_gold/ expected_bands (TASK-641)"
            )
        assert {d: list(resolved["band_thresholds"][d]) for d in DERIVED_DIMENSIONS} == {
            d: list(OFFLINE_SCORING_CONFIG["band_thresholds"][d]) for d in DERIVED_DIMENSIONS
        }, (
            f"{name}: seeded band_thresholds differ from the pinned fallback — "
            "re-derive tests/fixtures/dt_gold/ expected_bands (TASK-641)"
        )


def test_rubric_v5_seed_carries_the_scoring_keys():
    """The pinning test above skips while TASK-627 is pending — which would also skip
    forever, silently, if TASK-627 landed under different key names. Fail loudly the
    moment the v5 seed exists without the keys this module reads."""
    v5 = MIGRATIONS / "dt_rubric_v5_seed.sql"
    if not v5.exists():
        pytest.skip("TASK-627 rubric v5 seed not written yet")
    configs = _dollar_quoted_configs(v5.read_text(encoding="utf-8"))
    assert any(all(k in cfg for k in SCORING_KEYS) for cfg in configs), (
        f"dt_rubric_v5_seed.sql carries no config with all of {list(SCORING_KEYS)} — "
        "either TASK-627 renamed the keys (realign SCORING_KEYS + OFFLINE_SCORING_CONFIG "
        "and re-derive the gold fixtures) or the seed is incomplete (TASK-641)"
    )


@pytest.mark.parametrize("l2_code", L2_CODES)
def test_offline_fallback_still_reproduces_frozen_fixture_bands(l2_code):
    """The pinned constants are only meaningful if they still derive the bands the
    fixtures were frozen with. range/naturalness are model-judged, not derived."""
    items = json.loads((FIXTURE_DIR / f"{l2_code}.json").read_text(encoding="utf-8"))
    if isinstance(items, dict):
        items = items.get("items", [])
    for item in items:
        derived = derive_bands(item["expected_errors"], offline=True)
        for dim in DERIVED_DIMENSIONS:
            assert derived[dim] == item["expected_bands"][dim], (
                l2_code, item["id"], dim, derived, item["expected_bands"]
            )


# ---------------------------------------------------------------------------
# scoring_config — explicit source, no silent constant fallback
# ---------------------------------------------------------------------------

def test_scoring_config_requires_an_explicit_source():
    with pytest.raises(ValueError, match="no scoring source"):
        scoring_config()


def test_scoring_config_rejects_both_sources():
    with pytest.raises(ValueError, match="not both"):
        scoring_config(OFFLINE_SCORING_CONFIG, offline=True)


def test_scoring_config_offline_returns_pinned_constants():
    assert scoring_config(offline=True) == OFFLINE_SCORING_CONFIG


def test_scoring_config_raises_on_pre_task_627_rubric():
    """A v4-era config (weights/band_descriptors only) must NOT quietly degrade to
    the constants — that is the drift this task exists to prevent."""
    with pytest.raises(RuntimeError, match="TASK-627"):
        scoring_config({"weights": {"default": {}}, "band_descriptors": {}})


def _cfg(**overrides):
    return {**OFFLINE_SCORING_CONFIG, **overrides}


@pytest.mark.parametrize("broken, match", [
    (_cfg(severity_weights={"minor": 1, "major": 5}), "missing/non-numeric"),
    (_cfg(understandability_weights={"minor": 0, "major": "2", "critical": 25}),
     "missing/non-numeric"),
    (_cfg(band_thresholds={"accuracy": [1, 6], "fidelity": [1, 6, 15],
                           "understandability": [2, 6, 25]}), "3 ints"),
    (_cfg(band_thresholds={"accuracy": [15, 6, 1], "fidelity": [1, 6, 15],
                           "understandability": [2, 6, 25]}), "ascending"),
])
def test_scoring_config_rejects_malformed_config(broken, match):
    with pytest.raises(ValueError, match=match):
        scoring_config(broken)


# ---------------------------------------------------------------------------
# derive_bands actually reads the config it is handed
# ---------------------------------------------------------------------------

def _err(subtype_v5, severity):
    return {"subtype_v5_target": subtype_v5, "severity_v2": severity}


def test_derive_bands_reads_seeded_weights_not_constants():
    """Same error, harsher seeded weights -> lower band. If derive_bands were still
    reading the module constants this would come back band 4."""
    errors = [_err("article", "minor")]
    assert derive_bands(errors, offline=True)["accuracy"] == 4  # weight 1 <= t4 (1)
    harsher = _cfg(severity_weights={"minor": 20, "major": 5, "critical": 25})
    assert derive_bands(errors, rubric_cfg=harsher)["accuracy"] == 1  # 20 > t2 (15)


def test_derive_bands_understandability_counts_naturalness_mapped_errors():
    """collocation maps to naturalness — it adds no accuracy/fidelity penalty, but
    it still costs understandability."""
    errors = [_err("collocation", "critical")]
    bands = derive_bands(errors, offline=True)
    assert bands["accuracy"] == 4 and bands["fidelity"] == 4
    assert bands["understandability"] == 2  # und weight 25 <= t2 (25)


def test_derive_bands_takes_judged_dimensions_from_adjudicator():
    bands = derive_bands([], judged={"range": 2, "naturalness": 3}, offline=True)
    assert bands == {"accuracy": 4, "understandability": 4, "fidelity": 4,
                     "range": 2, "naturalness": 3}


# ---------------------------------------------------------------------------
# build_item — severity_v1 is optional residue
# ---------------------------------------------------------------------------

def _spec(edit):
    return {
        "id": "syn_01",
        "kind": "single",
        "source_passage_id": 1,
        "edits": [edit],
        "expected_bands": {"accuracy": 3, "understandability": 4, "fidelity": 4,
                           "range": 4, "naturalness": 4},
    }


BASE_EDIT = {
    "find": "the",
    "replace": "a",
    "subtype": "article",
    "subtype_v5_target": "article",
    "severity_v2": "major",
}
REFERENCE = "I saw the cat."


def test_build_item_without_severity_v1():
    """TASK-641 verification: a synthetic spec omitting severity_v1 must build."""
    item = build_item(_spec(dict(BASE_EDIT)), REFERENCE, "en")
    assert item["reproduction"] == "I saw a cat."
    err = item["expected_errors"][0]
    assert "severity_v1" not in err, "absent severity_v1 must be omitted, not nulled"
    assert err["severity_v2"] == "major"
    assert REFERENCE[err["span_ref"][0]:err["span_ref"][1]] == "the"
    assert item["reproduction"][err["span_repro"][0]:err["span_repro"][1]] == "a"


def test_build_item_carries_severity_v1_when_supplied():
    """Frozen fixtures still round-trip: supplied severity_v1 survives, in position."""
    item = build_item(_spec({**BASE_EDIT, "severity_v1": "global"}), REFERENCE, "en")
    err = item["expected_errors"][0]
    assert err["severity_v1"] == "global"
    assert list(err) == ["span_repro", "span_ref", "subtype", "subtype_v5_target",
                         "severity_v1", "severity_v2", "learner_form", "corrected_form"]


def test_offline_config_covers_every_severity_and_dimension():
    assert set(OFFLINE_SCORING_CONFIG) == set(SCORING_KEYS)
    for dim in DERIVED_DIMENSIONS:
        assert dim in OFFLINE_SCORING_CONFIG["band_thresholds"]
    for key in ("severity_weights", "understandability_weights"):
        assert set(OFFLINE_SCORING_CONFIG[key]) == set(SEVERITIES)


# ---------------------------------------------------------------------------
# taxonomy v6 (TASK-847): derive_bands(taxonomy_version=6) + the v6 fixtures
# ---------------------------------------------------------------------------

from scripts.dt_gold_seed_helper import V6_DIMENSION, verify_item  # noqa: E402

GOLD_V6_DIR = REPO / "tests" / "fixtures" / "dt_gold_v6"
SILVER_V6_DIR = REPO / "tests" / "fixtures" / "dt_silver_v6"
OVERLAY_DIR = REPO / "data" / "eval" / "taxonomy_merge_2026-09-27"
V6_FIXTURES = [(d, l) for d in (GOLD_V6_DIR, SILVER_V6_DIR) for l in L2_CODES]


def _v6_items(fixture_dir, l2_code):
    return json.loads((fixture_dir / f"{l2_code}.json").read_text(encoding="utf-8"))


def _all_v6_errors():
    return [e for d, l in V6_FIXTURES for i in _v6_items(d, l) for e in i["expected_errors"]]


def test_derive_bands_defaults_to_v5():
    """Same error, labelled differently per taxonomy: the default must read v5."""
    errors = [{"subtype_v5_target": "article", "subtype_v6_target": "meaning_inversion",
               "severity_v2": "critical"}]
    v5 = derive_bands(errors, offline=True)
    assert (v5["accuracy"], v5["fidelity"]) == (1, 4)
    assert derive_bands(errors, offline=True, taxonomy_version=5) == v5
    v6 = derive_bands(errors, offline=True, taxonomy_version=6)
    assert (v6["accuracy"], v6["fidelity"]) == (4, 1)


def test_derive_bands_rejects_unknown_taxonomy_version():
    with pytest.raises(ValueError, match="taxonomy_version"):
        derive_bands([], offline=True, taxonomy_version=4)


def test_v6_dimension_matches_merged_taxonomy():
    taxonomy = json.loads((OVERLAY_DIR / "merged_taxonomy.json").read_text(encoding="utf-8"))
    for subtypes in taxonomy.values():
        for st in subtypes:
            assert V6_DIMENSION[st["id"]] == st["dimension"]
    assert V6_DIMENSION["meaning_inversion"] == "fidelity"
    assert V6_DIMENSION["word_choice"] == "fidelity"


@pytest.mark.parametrize("fixture_dir, l2_code", V6_FIXTURES)
def test_v6_fixture_bands_derive_under_v6(fixture_dir, l2_code):
    for item in _v6_items(fixture_dir, l2_code):
        derived = derive_bands(item["expected_errors"], offline=True, taxonomy_version=6)
        for dim in DERIVED_DIMENSIONS:
            assert derived[dim] == item["expected_bands"][dim], (
                fixture_dir.name, l2_code, item["id"], dim, derived, item["expected_bands"]
            )


@pytest.mark.parametrize("fixture_dir, l2_code", V6_FIXTURES)
def test_v6_fixture_items_verify(fixture_dir, l2_code):
    for item in _v6_items(fixture_dir, l2_code):
        assert verify_item(item, l2_code) == []
        for err in item["expected_errors"]:
            assert err["subtype"] == err["subtype_v6_target"] in V6_DIMENSION
            assert err["severity_v2"] in SEVERITIES
            assert "subtype_v5_target" in err
            assert ("explanation_variant" in err) == (err["subtype"] == "word_choice")


@pytest.mark.parametrize("l2_code", L2_CODES)
def test_v6_gold_keeps_v5_ids_and_order(l2_code):
    """v5 ids/order are kept as a prefix; anything after is a v6-only item (TASK-848)
    from v6_only_gold_items.json, in file order."""
    v5 = json.loads((FIXTURE_DIR / f"{l2_code}.json").read_text(encoding="utf-8"))
    v6 = _v6_items(GOLD_V6_DIR, l2_code)
    assert [i["id"] for i in v6[:30]] == [i["id"] for i in v5]
    assert len(v5) == 30
    only = json.loads((OVERLAY_DIR / "v6_only_gold_items.json").read_text(encoding="utf-8"))
    assert [i["id"] for i in v6[30:]] == [s["id"] for s in only["items"][l2_code]]
    assert all(i["id"].startswith(f"{l2_code}_v6_") for i in v6[30:])


def test_v6_label_counts():
    """177 overlay labels; 23 meaning_inversion (21 + the repaired en_silver_24 +
    the repaired en_silver_26, a quantity/degree flip) and 25 word_choice split
    17 wrong_word / 0 wrong_sense / 8 false_synonym. (en_silver_34's repaired
    error is 'register', which does not move either count.) Plus 1 v6-only error
    (TASK-848, en_v6_ws_02 like/likes), the only narrow wrong_sense: 178 errors,
    26 word_choice = 17 / 1 / 8.

    Developer decision 2026-10-09 (ADR-031): the three it/him-for-them errors
    (en_seed_10#0, en_multi_03#2, en_silver_13#0) moved word_choice/wrong_word ->
    pronoun; the four ja だ/です politeness-level keigo errors stay keigo and the two
    silver plain->polite items labelled register (ja_silver_30#0, ja_silver_32#1)
    move to keigo (4 + 2 = 6). The 4 zh 个-for-specific-classifier swaps stay
    measure_word errors (plus the reverse 只-for-个 zh_silver_23 = 5)."""
    errors = _all_v6_errors()
    assert len(errors) == 178
    assert sum(e["subtype"] == "meaning_inversion" for e in errors) == 23
    wc = [e["explanation_variant"] for e in errors if e["subtype"] == "word_choice"]
    assert len(wc) == 26
    assert (wc.count("wrong_word"), wc.count("wrong_sense"), wc.count("false_synonym")) == (17, 1, 8)
    assert sum(e["subtype"] == "pronoun" for e in errors) == 3
    assert sum(e["subtype"] == "keigo" for e in errors) == 6
    assert sum(e["subtype"] == "measure_word" for e in errors) == 5


def test_v6_only_wrong_sense_item():
    """TASK-848: the one reviewed narrow wrong_sense item (same headword 'like',
    verb 'enjoy' sense where the preposition 'similar to' sense is needed)."""
    item = next(i for i in _v6_items(GOLD_V6_DIR, "en") if i["id"] == "en_v6_ws_02")
    (err,) = item["expected_errors"]
    assert (err["subtype"], err["explanation_variant"], err["severity_v2"]) == (
        "word_choice", "wrong_sense", "major")
    assert (err["learner_form"], err["corrected_form"]) == ("likes", "is like")
    assert item["expected_bands"] == {"accuracy": 4, "understandability": 4, "fidelity": 3,
                                      "range": 4, "naturalness": 4}
    assert not any(i["id"].startswith("en_v6_") for i in _v6_items(SILVER_V6_DIR, "en"))


def test_en_silver_24_carries_its_meaning_inversion():
    item = next(i for i in _v6_items(SILVER_V6_DIR, "en") if i["id"] == "en_silver_24")
    (err,) = item["expected_errors"]
    assert (err["subtype"], err["severity_v2"]) == ("meaning_inversion", "critical")
    assert item["expected_bands"]["understandability"] == 2
    assert item["expected_bands"]["fidelity"] == 1


def test_v6_band_changes_match_overlay_report():
    """The v6 bands differ from v5 on exactly the items overlay_band_changes.json lists,
    except en_silver_24 — that report predates its 2026-09-28 repair (it had no error,
    hence 'understandability 2->4'); restored, meaning_inversion/critical derives the
    same bands as the v5 word_choice/critical label."""
    report = json.loads((OVERLAY_DIR / "overlay_band_changes.json").read_text(encoding="utf-8"))
    expected = {c["item_id"]: c["changed"] for c in report["changes"] if c["item_id"] != "en_silver_24"}
    v5_src = {
        **{i["id"]: i for l in L2_CODES
           for i in json.loads((FIXTURE_DIR / f"{l}.json").read_text(encoding="utf-8"))},
        **{i["id"]: i for l in L2_CODES
           for i in json.loads((REPO / "data" / "eval" / "jev_dt_2026-09-26" / "silver"
                                / f"{l}_final3.json").read_text(encoding="utf-8"))},
    }
    got = {}
    for d, l in V6_FIXTURES:
        for item in _v6_items(d, l):
            if item["id"] not in v5_src:  # v6-only item (TASK-848): no v5 bands to compare
                continue
            old = v5_src[item["id"]]["expected_bands"]
            changed = {dim: [old[dim], item["expected_bands"][dim]]
                       for dim in DERIVED_DIMENSIONS if old[dim] != item["expected_bands"][dim]}
            if changed:
                got[item["id"]] = changed
    assert got == expected
    # 11 -> 8 on 2026-10-09: the three it/him-for-them items are pronoun (accuracy) again,
    # which derives the same bands as v5 pronoun_reference.
    assert len(got) == 8


def test_v6_fixtures_are_fresh():
    """The committed v6 files are exactly what build_dt_gold_v6.py produces."""
    from scripts.build_dt_gold_v6 import _serialise, build

    for path, items in build()["outputs"].items():
        assert path.read_text(encoding="utf-8") == _serialise(items), (
            f"{path.name} is stale — run scripts/build_dt_gold_v6.py"
        )
