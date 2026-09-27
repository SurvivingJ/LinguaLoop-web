#!/usr/bin/env python3
"""Counts, over the DT gold + silver error labels, how many map unambiguously to the
proposed v6 merged taxonomy (ADR-031) vs need per-instance relabelling.

Unambiguous = the v5 subtype's mapping_kind is 1:1 or merge (deterministic rename/collapse).
Needs relabel = mapping_kind is split (v6's definition is narrower/ambiguous) or dropped
(jev rules the v5 subtype out as not-an-error).

Run from the repo root:  python3 data/eval/taxonomy_merge_2026-09-27/impact.py
Writes data/eval/taxonomy_merge_2026-09-27/impact.json.
"""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.dirname(os.path.abspath(__file__))

# Same v5 -> v6 mapping kinds as v5_to_merged.csv (see that file for full notes).
V5_MAP = {
    "zh": [
        ("omission", "1:1"), ("addition", "1:1"), ("word_choice", "1:1"),
        ("collocation", "1:1"), ("word_order", "1:1"), ("register", "1:1"),
        ("orthography", "1:1"), ("cohesion_connective", "1:1"),
        ("classifier", "1:1"), ("aspect_marker", "merge"), ("de_particles", "split"),
        ("ba_construction", "merge"), ("bei_passive", "merge"),
        ("resultative_complement", "merge"), ("directional_complement", "merge"),
        ("adverbial_order", "merge"), ("topic_comment", "1:1"),
    ],
    "ja": [
        ("omission", "1:1"), ("addition", "1:1"), ("word_choice", "1:1"),
        ("collocation", "1:1"), ("word_order", "1:1"), ("register", "1:1"),
        ("orthography", "1:1"), ("cohesion_connective", "1:1"),
        ("particle_wa_ga", "split"), ("particle_case", "1:1"), ("particle_other", "1:1"),
        ("verb_conjugation", "1:1"), ("tense_aspect_ja", "merge"), ("keigo_register", "1:1"),
        ("counter_classifier", "1:1"), ("script_choice", "dropped"), ("topic_comment", "1:1"),
        ("particle", "split"),  # pre-v5 historical_alias
    ],
    "en": [
        ("omission", "1:1"), ("addition", "1:1"), ("word_choice", "1:1"),
        ("collocation", "1:1"), ("word_order", "1:1"), ("register", "1:1"),
        ("orthography", "1:1"), ("cohesion_connective", "1:1"),
        ("article", "1:1"), ("preposition", "1:1"), ("tense_aspect", "1:1"),
        ("subject_verb_agreement", "1:1"), ("plural_number", "1:1"),
        ("phrasal_verb", "1:1"), ("pronoun_reference", "split"),
    ],
}

UNAMBIGUOUS_KINDS = {"1:1", "merge"}
NEEDS_RELABEL_KINDS = {"split", "dropped"}

FILES = {
    "zh": [
        "tests/fixtures/dt_gold/zh.json",
        "data/eval/jev_dt_2026-09-26/silver/zh_final3.json",
    ],
    "ja": [
        "tests/fixtures/dt_gold/ja.json",
        "data/eval/jev_dt_2026-09-26/silver/ja_final3.json",
    ],
    "en": [
        "tests/fixtures/dt_gold/en.json",
        "data/eval/jev_dt_2026-09-26/silver/en_final3.json",
    ],
}


def main():
    v5_kind = {(lang, subtype): kind for lang, rows in V5_MAP.items() for subtype, kind in rows}

    impact = {
        "per_language": {},
        "totals": {"unambiguous": 0, "needs_relabel": 0, "unknown_subtype": 0, "total_labels": 0},
    }

    for lang, files in FILES.items():
        counts = {"unambiguous": 0, "needs_relabel": 0, "unknown_subtype": 0, "total_labels": 0}
        by_subtype = {}
        for rel in files:
            path = os.path.join(ROOT, rel)
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as f:
                items = json.load(f)
            for item in items:
                for err in item.get("expected_errors", []) or []:
                    subtype = err.get("subtype")
                    if subtype is None:
                        continue
                    counts["total_labels"] += 1
                    kind = v5_kind.get((lang, subtype))
                    if kind is None:
                        counts["unknown_subtype"] += 1
                        bucket = "unknown_subtype"
                    elif kind in UNAMBIGUOUS_KINDS:
                        counts["unambiguous"] += 1
                        bucket = "unambiguous"
                    else:
                        counts["needs_relabel"] += 1
                        bucket = "needs_relabel"
                    by_subtype.setdefault(subtype, {"kind": kind or "unknown", "bucket": bucket, "n": 0})
                    by_subtype[subtype]["n"] += 1
        impact["per_language"][lang] = {"counts": counts, "by_subtype": by_subtype, "files": files}
        for k in impact["totals"]:
            impact["totals"][k] += counts[k]

    out_path = os.path.join(OUT, "impact.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(impact, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(json.dumps(impact["totals"], indent=2))
    for lang in impact["per_language"]:
        print(lang, impact["per_language"][lang]["counts"])


if __name__ == "__main__":
    main()
