# -*- coding: utf-8 -*-
"""Merges silver/en_draft.json (rater1) + en_rater2.json + en_rater3.json
(independent, blind) into silver/en_final3.json via 2-of-3 majority, per
scripts/dt_gold_seed_helper.py's derive_bands(offline=True) for re-deriving
accuracy/fidelity/understandability from the majority-approved error list.

Per item:
  1. Match each rater's error list into clusters via learner_form text
     similarity (SequenceMatcher ratio >= 0.5), anchored on draft (rater1)
     since draft alone carries the spans this pipeline reuses.
  2. existence: a draft-anchored cluster survives iff >=2 of the 3 raters
     are present in it (draft counts as 1 vote automatically; r2/r3 count
     if matched). A cluster with only 1 vote (draft-only, unmatched by
     both r2/r3) is dropped.
  3. subtype / severity: majority = the value shared by >=2 of the voters
     actually present in a surviving cluster. No majority -> the WHOLE
     error is dropped (subtype/severity are required by derive_bands; a
     partial error cannot be scored) -- logged, not silently kept as draft.
  4. naturalness / range: item-level scalar majority across draft's
     expected_bands value + rater2 + rater3. No majority -> logged and the
     draft's value is kept as a documented fallback (these two fields are
     required by every downstream consumer; "drop" isn't a valid state for
     a single required scalar the way it is for a whole error record).
  5. accuracy/fidelity/understandability are always RE-DERIVED from the
     majority error list via derive_bands(offline=True) -- never copied
     from any single rater, including when the item is otherwise unchanged.
  6. r2/r3 errors that could not be matched to any draft error (draft
     missed something 2 minority raters agree on) cannot be included in
     the rebuilt item -- there is no draft span for them. Logged as
     "orphaned_majority_error" (should be reviewed by a human later); NOT
     silently dropped from the log, only from the frozen item.

No DB writes. Reads only silver/en_{draft,rater2,rater3}.json.
"""
from __future__ import annotations

import difflib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SILVER_DIR = os.path.join(HERE, "silver")
sys.path.insert(0, REPO)

from scripts.dt_gold_seed_helper import derive_bands, verify_item, OFFLINE_SCORING_CONFIG, _band  # noqa: E402

SIM_THRESHOLD = 0.5


def load(name: str) -> dict:
    with open(os.path.join(SILVER_DIR, name), encoding="utf-8") as f:
        items = json.load(f)
    return {it["id"]: it for it in items}


def sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a or "", b or "").ratio()


def match_errors(anchors: list[dict], candidates: list[dict]) -> dict[int, int]:
    """Greedy best-first match anchors[i] -> candidates[j] by learner_form
    similarity >= SIM_THRESHOLD, one-to-one. Returns {anchor_idx: cand_idx}."""
    pairs = []
    for i, a in enumerate(anchors):
        for j, c in enumerate(candidates):
            s = sim(a["learner_form"], c["learner_form"])
            if s >= SIM_THRESHOLD:
                pairs.append((s, i, j))
    pairs.sort(key=lambda p: -p[0])
    used_a, used_c, out = set(), set(), {}
    for s, i, j in pairs:
        if i in used_a or j in used_c:
            continue
        used_a.add(i)
        used_c.add(j)
        out[i] = j
    return out


def majority_of(values: list) -> tuple[object | None, bool]:
    """(majority_value_or_None, had_majority). values may contain None entries
    (rater absent from this cluster) which are ignored for voting."""
    present = [v for v in values if v is not None]
    if len(present) < 2:
        return None, False
    counts: dict = {}
    for v in present:
        counts[v] = counts.get(v, 0) + 1
    best_v, best_n = max(counts.items(), key=lambda kv: kv[1])
    return (best_v, True) if best_n >= 2 else (None, False)


def merge_item(item_id: str, d1: dict, d2: dict, d3: dict, log: dict) -> dict:
    draft = d1[item_id]
    r2 = d2[item_id]
    r3 = d3[item_id]

    e1 = [{"learner_form": e["learner_form"], "corrected_form": e["corrected_form"],
           "subtype": e.get("subtype_v5_target") or e["subtype"], "severity": e["severity_v2"],
           "span_repro": e["span_repro"], "span_ref": e["span_ref"]}
          for e in draft["expected_errors"]]
    e2 = r2["errors"]
    e3 = r3["errors"]

    m12 = match_errors(e1, e2)
    m13 = match_errors(e1, e3)
    m23 = match_errors(e2, e3)  # for orphan detection + pairwise agreement only

    item_log = {"id": item_id, "dropped_errors": [], "orphaned_majority_errors": [],
                "kept_errors": [], "understandability_only_errors": [],
                "naturalness_no_majority": False, "range_no_majority": False}

    final_errors = []
    understandability_only_severities: list[str] = []  # existence+severity majority, subtype had none
    matched_e2_idx, matched_e3_idx = set(m12.values()), set(m13.values())

    for i, anchor in enumerate(e1):
        j2 = m12.get(i)
        j3 = m13.get(i)
        votes_present = 1 + (1 if j2 is not None else 0) + (1 if j3 is not None else 0)
        if votes_present < 2:
            item_log["dropped_errors"].append({"reason": "no_existence_majority", "learner_form": anchor["learner_form"]})
            continue

        subtype_votes = [anchor["subtype"], e2[j2]["subtype"] if j2 is not None else None,
                          e3[j3]["subtype"] if j3 is not None else None]
        severity_votes = [anchor["severity"], e2[j2]["severity"] if j2 is not None else None,
                           e3[j3]["severity"] if j3 is not None else None]
        subtype_maj, sub_ok = majority_of(subtype_votes)
        severity_maj, sev_ok = majority_of(severity_votes)
        if not sev_ok:
            item_log["dropped_errors"].append({
                "reason": "no_severity_majority", "learner_form": anchor["learner_form"],
                "subtype_votes": subtype_votes, "severity_votes": severity_votes,
            })
            continue
        if not sub_ok:
            # Existence + severity both have a majority (an error is really
            # there, at an agreed severity), but WHICH subtype disagrees 3
            # ways -- we can't route it to accuracy/fidelity, but dropping
            # it entirely would silently erase a majority-confirmed error.
            # It still counts toward understandability (mirrors production
            # compute_dimension_bands: an unattributable subtype still
            # penalizes understandability, never accuracy/fidelity).
            understandability_only_severities.append(severity_maj)
            item_log["understandability_only_errors"].append({
                "reason": "no_subtype_majority_severity_only", "learner_form": anchor["learner_form"],
                "subtype_votes": subtype_votes, "severity_agreed": severity_maj,
            })
            continue

        final_errors.append({
            "span_repro": anchor["span_repro"], "span_ref": anchor["span_ref"],
            "subtype": subtype_maj, "subtype_v5_target": subtype_maj,
            "severity_v2": severity_maj,
            "learner_form": anchor["learner_form"], "corrected_form": anchor["corrected_form"],
        })
        item_log["kept_errors"].append({"learner_form": anchor["learner_form"], "subtype": subtype_maj, "severity": severity_maj})

    # orphaned: r2/r3 errors that agree with EACH OTHER but were never matched
    # to any draft anchor -> majority exists (2 of 3) but no draft span to reuse.
    for j2, j3 in m23.items():
        if j2 in matched_e2_idx or j3 in matched_e3_idx:
            continue  # already accounted for via a draft anchor
        if sim(e2[j2]["learner_form"], e3[j3]["learner_form"]) >= SIM_THRESHOLD:
            item_log["orphaned_majority_errors"].append({
                "rater2": e2[j2]["learner_form"], "rater3": e3[j3]["learner_form"],
                "subtype_r2": e2[j2]["subtype"], "subtype_r3": e3[j3]["subtype"],
            })

    nat_maj, nat_ok = majority_of([draft["expected_bands"]["naturalness"], r2["naturalness"], r3["naturalness"]])
    rng_maj, rng_ok = majority_of([draft["expected_bands"]["range"], r2["range"], r3["range"]])
    if not nat_ok:
        item_log["naturalness_no_majority"] = True
        nat_maj = draft["expected_bands"]["naturalness"]
    if not rng_ok:
        item_log["range_no_majority"] = True
        rng_maj = draft["expected_bands"]["range"]

    bands = derive_bands(final_errors, judged={"naturalness": nat_maj, "range": rng_maj}, offline=True)
    if understandability_only_severities:
        und_w = OFFLINE_SCORING_CONFIG["understandability_weights"]
        extra_pen = sum(und_w[s] for s in understandability_only_severities)
        base_pen = sum(und_w[e["severity_v2"]] for e in final_errors)
        thresh = OFFLINE_SCORING_CONFIG["band_thresholds"]["understandability"]
        bands = {**bands, "understandability": _band(base_pen + extra_pen, *thresh)}

    unchanged = (
        len(final_errors) == len(draft["expected_errors"])
        and all(fe["subtype_v5_target"] == oe["subtype_v5_target"] and fe["severity_v2"] == oe["severity_v2"]
                for fe, oe in zip(final_errors, draft["expected_errors"]))
        and not item_log["orphaned_majority_errors"] and not item_log["naturalness_no_majority"]
        and not item_log["range_no_majority"] and not item_log["understandability_only_errors"]
    )
    item_log["unchanged_from_draft"] = unchanged

    new_item = {
        "id": draft["id"], "kind": draft["kind"], "source_passage_id": draft["source_passage_id"],
        "note": draft["note"], "reference": draft["reference"], "reproduction": draft["reproduction"],
        "expected_errors": final_errors, "expected_bands": bands,
        "label_source": "silver_majority3",
    }
    log["items"].append(item_log)
    return new_item


def _normalize_rater(d: dict, iid: str, is_draft: bool) -> tuple[list[dict], int, int]:
    """One rater's (errors, naturalness, range) for item iid, in a common shape."""
    it = d[iid]
    if is_draft:
        errs = [{"learner_form": e["learner_form"],
                  "subtype": e.get("subtype_v5_target") or e["subtype"],
                  "severity": e["severity_v2"]} for e in it["expected_errors"]]
        return errs, it["expected_bands"]["naturalness"], it["expected_bands"]["range"]
    errs = [{"learner_form": e["learner_form"], "subtype": e["subtype"], "severity": e["severity"]} for e in it["errors"]]
    return errs, it["naturalness"], it["range"]


def pairwise_agreement(d1: dict, d2: dict, d3: dict) -> dict:
    """existence (item-level has_error boolean), subtype/severity (cluster-level,
    only where both raters in the pair flagged something matchable), naturalness/
    range (exact scalar match) -- for each of the 3 rater pairs."""
    pairs = {"r1_r2": (d1, True, d2, False), "r1_r3": (d1, True, d3, False), "r2_r3": (d2, False, d3, False)}
    out = {}
    for name, (da, a_draft, db, b_draft) in pairs.items():
        exist_agree = exist_n = 0
        sub_agree = sub_n = 0
        sev_agree = sev_n = 0
        nat_agree = nat_n = 0
        rng_agree = rng_n = 0
        for iid in da:
            ea, na, ra = _normalize_rater(da, iid, a_draft)
            eb, nb, rb = _normalize_rater(db, iid, b_draft)

            exist_n += 1
            if bool(ea) == bool(eb):
                exist_agree += 1

            m = match_errors(ea, eb)
            for i, j in m.items():
                sub_n += 1
                if ea[i]["subtype"] == eb[j]["subtype"]:
                    sub_agree += 1
                sev_n += 1
                if ea[i]["severity"] == eb[j]["severity"]:
                    sev_agree += 1

            nat_n += 1
            nat_agree += int(na == nb)
            rng_n += 1
            rng_agree += int(ra == rb)

        out[name] = {
            "existence": exist_agree / exist_n if exist_n else float("nan"),
            "subtype": (sub_agree / sub_n) if sub_n else float("nan"),
            "severity": (sev_agree / sev_n) if sev_n else float("nan"),
            "naturalness": nat_agree / nat_n if nat_n else float("nan"),
            "range": rng_agree / rng_n if rng_n else float("nan"),
            "n_items": exist_n, "n_matched_errors": sub_n,
        }
    return out


def main():
    d1 = load("en_draft.json")
    d2 = load("en_rater2.json")
    d3 = load("en_rater3.json")
    assert set(d1) == set(d2) == set(d3), "id sets differ across raters"

    log = {"items": []}
    final_items = [merge_item(iid, d1, d2, d3, log) for iid in sorted(d1, key=lambda x: d1[x]["id"])]

    problems = {}
    for it in final_items:
        p = verify_item(it, "en")
        if p:
            problems[it["id"]] = p
    log["verify_item_problems"] = problems
    log["agreement"] = pairwise_agreement(d1, d2, d3)
    log["n_items"] = len(final_items)
    log["n_unchanged_from_draft"] = sum(1 for it in log["items"] if it["unchanged_from_draft"])
    log["n_with_dropped_errors"] = sum(1 for it in log["items"] if it["dropped_errors"])
    log["n_with_orphaned_majority_errors"] = sum(1 for it in log["items"] if it["orphaned_majority_errors"])

    with open(os.path.join(SILVER_DIR, "en_final3.json"), "w", encoding="utf-8") as f:
        json.dump(final_items, f, indent=1, ensure_ascii=False)
    with open(os.path.join(SILVER_DIR, "en_merge_log.json"), "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    print(json.dumps({k: v for k, v in log.items() if k != "items"}, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
