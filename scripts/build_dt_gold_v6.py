"""Build the v6-taxonomy DT gold + silver fixtures from the v6 label overlay (TASK-847).

NOT part of the running app. Offline, deterministic, no DB / no API.

Inputs (read-only):
  * tests/fixtures/dt_gold/{zh,ja,en}.json                 — v5 gold (FROZEN; never written here)
  * data/eval/jev_dt_2026-09-26/silver/{l}_final3.json     — v5 silver
  * data/eval/jev_dt_2026-09-26/silver/en_silver_24_fix.json — the en_silver_24 error record
  * data/eval/taxonomy_merge_2026-09-27/v6_label_overlay.json — final v6 labels, one per error
  * data/eval/taxonomy_merge_2026-09-27/v6_only_gold_items.json — v6-native gold specs with
    no v5 counterpart (TASK-848 wrong_sense coverage), appended to the gold files only

Outputs:
  * tests/fixtures/dt_gold_v6/{zh,ja,en}.json
  * tests/fixtures/dt_silver_v6/{zh,ja,en}.json

Per error, matched to the overlay by (item_id, error_index):
  subtype = subtype_v6_target = overlay v6_type, severity_v2 = overlay v6_severity,
  explanation_variant (word_choice only) and variant_uncertain carried when present,
  subtype_v5_target kept as provenance. severity_v1 (pre-TASK-625 residue) is dropped:
  severity_v2 may have moved under v6, so a carried global/local would be stale.

expected_bands: accuracy/fidelity/understandability are re-derived with
derive_bands(offline=True, taxonomy_version=6); range/naturalness are adjudicated
inputs and are carried over unchanged. Every item must pass verify_item.

The build fails on any error without an overlay label, any overlay label without an
error, or any learner_form/corrected_form disagreement between the two. Items in
HELD_OUT (no adjudicated label to carry) are skipped and reported.

Usage:
    PYTHONPATH=. python scripts/build_dt_gold_v6.py           # write fixtures
    PYTHONPATH=. python scripts/build_dt_gold_v6.py --check   # build + compare, write nothing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.dt_gold_seed_helper import (  # noqa: E402
    BANDS,
    DERIVED_DIMENSIONS,
    build_item,
    derive_bands,
    verify_item,
)

LANGS = ("zh", "ja", "en")
GOLD_V5_DIR = REPO / "tests" / "fixtures" / "dt_gold"
GOLD_V6_DIR = REPO / "tests" / "fixtures" / "dt_gold_v6"
SILVER_V6_DIR = REPO / "tests" / "fixtures" / "dt_silver_v6"
SILVER_SRC_DIR = REPO / "data" / "eval" / "jev_dt_2026-09-26" / "silver"
OVERLAY_DIR = REPO / "data" / "eval" / "taxonomy_merge_2026-09-27"
OVERLAY_PATH = OVERLAY_DIR / "v6_label_overlay.json"
EN_SILVER_24_FIX = SILVER_SRC_DIR / "en_silver_24_fix.json"
# v6-native gold items with no v5 counterpart (TASK-848), appended after the v5-derived
# gold items. Built from find/replace specs with build_item; no overlay label.
V6_ONLY_PATH = OVERLAY_DIR / "v6_only_gold_items.json"


# Source items that are NOT carried into the v6 fixtures because they have no
# adjudicated label to carry. (Empty since 2026-10-04: en_silver_26, the last
# remaining held-out item, was repaired the same way en_silver_24 was on 2026-09-28
# -- see en_silver_26_fix.json and en_final3.json's note on that item. The build
# fails if a held-out item ever gains errors upstream, so this list cannot go stale
# silently if it is ever repopulated.)
HELD_OUT: dict[str, str] = {}


class BuildError(RuntimeError):
    pass


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_en_silver_24(items: list[dict]) -> str:
    """en_silver_24 lost its only error in the silver merge (3 raters, no subtype
    majority). en_final3.json was repaired on 2026-09-28; if a source predating that
    repair is ever fed in, re-insert the error from en_silver_24_fix.json here so the
    v6 silver file always carries it. Returns what happened, for the report."""
    item = next((i for i in items if i["id"] == "en_silver_24"), None)
    if item is None:
        raise BuildError("en_silver_24 missing from en silver source")
    if item["expected_errors"]:
        return "already present in en_final3.json (2026-09-28 repair)"
    diff = _load(EN_SILVER_24_FIX)["blind_analysis"]["differences"][0]
    lf, cf = diff["learner_form"], diff["corrected_form"]
    ref, repro = item["reference"], item["reproduction"]
    if ref.count(cf) != 1 or repro.count(lf) != 1:
        raise BuildError("en_silver_24 fix: learner/corrected form not uniquely locatable")
    r0, p0 = ref.index(cf), repro.index(lf)
    item["expected_errors"] = [{
        "span_repro": [p0, p0 + len(lf)],
        "span_ref": [r0, r0 + len(cf)],
        "subtype": diff["v5_subtype"],
        "subtype_v5_target": diff["v5_subtype"],
        "severity_v2": diff["severity"],
        "learner_form": lf,
        "corrected_form": cf,
    }]
    return "inserted from en_silver_24_fix.json"


def _v6_error(err: dict, label: dict) -> dict:
    out = {
        "span_repro": err["span_repro"],
        "span_ref": err["span_ref"],
        "subtype": label["v6_type"],
        "subtype_v5_target": err["subtype_v5_target"],
        "subtype_v6_target": label["v6_type"],
        "severity_v2": label["v6_severity"],
    }
    if "explanation_variant" in label:
        out["explanation_variant"] = label["explanation_variant"]
        if label.get("variant_uncertain"):
            out["variant_uncertain"] = True
    out["learner_form"] = err["learner_form"]
    out["corrected_form"] = err["corrected_form"]
    return out


def _convert(items: list[dict], lang: str, set_name: str, labels: dict, used: set,
             band_changes: list, problems: list) -> list[dict]:
    out = []
    for item in items:
        if item["id"] in HELD_OUT:
            if item["expected_errors"]:
                raise BuildError(f"{item['id']} is HELD_OUT but now has errors upstream — "
                                 "remove it from HELD_OUT and label it in the overlay")
            continue
        new_errors = []
        for idx, err in enumerate(item["expected_errors"]):
            key = (item["id"], idx)
            label = labels.get(key)
            if label is None:
                raise BuildError(f"no overlay label for {key}")
            if (label["set"], label["lang"]) != (set_name, lang):
                raise BuildError(f"{key}: overlay says {label['set']}/{label['lang']}, source is {set_name}/{lang}")
            if (label["learner_form"], label["corrected_form"]) != (err["learner_form"], err["corrected_form"]):
                raise BuildError(f"{key}: overlay forms disagree with the fixture error")
            used.add(key)
            new_errors.append(_v6_error(err, label))

        old_bands = item["expected_bands"]
        derived = derive_bands(
            new_errors,
            judged={"range": old_bands["range"], "naturalness": old_bands["naturalness"]},
            offline=True,
            taxonomy_version=6,
        )
        changed = {d: [old_bands[d], derived[d]] for d in DERIVED_DIMENSIONS if old_bands[d] != derived[d]}
        if changed:
            band_changes.append({"item_id": item["id"], "set": set_name, "lang": lang, "changed": changed})

        new_item = {k: v for k, v in item.items() if k not in ("expected_errors", "expected_bands")}
        new_item["expected_errors"] = new_errors
        new_item["expected_bands"] = {b: derived[b] for b in BANDS}
        # Keep the source's key order (expected_errors/expected_bands before any
        # silver-only provenance keys such as label_source).
        ordered = {}
        for k in item:
            ordered[k] = new_item[k]
        problems.extend(verify_item(ordered, lang))
        out.append(ordered)
    return out


def _v6_only_items(lang: str, existing_ids: set, problems: list) -> list[dict]:
    """Build the v6-native gold items for `lang` from V6_ONLY_PATH (TASK-848).

    Same item schema as the overlay-derived v6 gold; errors carry subtype ==
    subtype_v6_target == the spec's subtype, and explanation_variant on word_choice."""
    specs = _load(V6_ONLY_PATH)["items"].get(lang, [])
    out = []
    for spec in specs:
        if spec["id"] in existing_ids:
            raise BuildError(f"v6-only item id {spec['id']} collides with an existing item")
        item = build_item({**spec, "expected_bands": {b: 4 for b in BANDS}}, spec["reference"], lang)
        errors = []
        for err, edit in zip(item["expected_errors"], [e for e in spec["edits"] if e.get("is_error", True)]):
            if (edit["subtype"] == "word_choice") != ("explanation_variant" in edit):
                raise BuildError(f"{spec['id']}: explanation_variant must be set on word_choice errors only")
            e = {
                "span_repro": err["span_repro"],
                "span_ref": err["span_ref"],
                "subtype": edit["subtype"],
                "subtype_v5_target": err["subtype_v5_target"],
                "subtype_v6_target": edit["subtype"],
                "severity_v2": err["severity_v2"],
            }
            if "explanation_variant" in edit:
                e["explanation_variant"] = edit["explanation_variant"]
            e["learner_form"] = err["learner_form"]
            e["corrected_form"] = err["corrected_form"]
            errors.append(e)
        item["expected_errors"] = errors
        item["expected_bands"] = derive_bands(errors, judged=spec["judged"], offline=True, taxonomy_version=6)
        problems.extend(verify_item(item, lang))
        out.append(item)
    return out


def build() -> dict:
    overlay = _load(OVERLAY_PATH)
    if not overlay.get("final"):
        raise BuildError("v6_label_overlay.json is not marked final")
    labels = {}
    for e in overlay["entries"]:
        key = (e["item_id"], e["error_index"])
        if key in labels:
            raise BuildError(f"duplicate overlay label {key}")
        labels[key] = e

    used: set = set()
    band_changes: list = []
    problems: list = []
    outputs: dict[Path, list] = {}
    notes = {}
    for lang in LANGS:
        gold = _load(GOLD_V5_DIR / f"{lang}.json")
        silver = _load(SILVER_SRC_DIR / f"{lang}_final3.json")
        if lang == "en":
            notes["en_silver_24"] = _ensure_en_silver_24(silver)
        gold_v6 = _convert(gold, lang, "gold", labels, used, band_changes, problems)
        all_ids = {i["id"] for i in gold} | {i["id"] for i in silver}
        gold_v6 += _v6_only_items(lang, all_ids, problems)
        outputs[GOLD_V6_DIR / f"{lang}.json"] = gold_v6
        outputs[SILVER_V6_DIR / f"{lang}.json"] = _convert(silver, lang, "silver", labels, used, band_changes, problems)

    unused = sorted(set(labels) - used)
    if unused:
        raise BuildError(f"overlay labels with no fixture error: {unused}")
    if problems:
        raise BuildError("verify_item failures:\n  " + "\n  ".join(problems))
    return {"outputs": outputs, "band_changes": band_changes, "labels": len(labels), "notes": notes}


def _serialise(items: list) -> str:
    return json.dumps(items, ensure_ascii=False, indent=2) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="build and compare against the files on disk; write nothing")
    args = ap.parse_args(argv)

    try:
        result = build()
    except BuildError as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        return 1

    stale = []
    for path, items in result["outputs"].items():
        text = _serialise(items)
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path.relative_to(REPO).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        n_err = sum(len(i["expected_errors"]) for i in items)
        print(f"{path.relative_to(REPO).as_posix()}: {len(items)} items, {n_err} errors")

    print(f"overlay labels consumed: {result['labels']}")
    for k, v in HELD_OUT.items():
        print(f"held out: {k} — {v}")
    for k, v in result["notes"].items():
        print(f"{k}: {v}")
    print(f"band changes vs v5 expected_bands: {len(result['band_changes'])}")
    for c in result["band_changes"]:
        print(f"  {c['item_id']}: {c['changed']}")
    if stale:
        print(f"STALE (re-run without --check): {stale}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
