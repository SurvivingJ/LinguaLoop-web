"""Build the v6 (ADR-031) label overlay for the DT gold + silver sets.

Read-only over the fixtures: gold stays v5 for live regression; this writes an OVERLAY.

Outputs (next to this script):
  v6_label_overlay.json          one entry per labelled error (gold + silver)
  overlay_band_changes.json      items whose derived bands change vs expected_bands under v6
  overlay_blind_for_reviewer.json  non-deterministic entries only, without the v6 decision

Run from the repo root:  PYTHONPATH=. python data/eval/taxonomy_merge_2026-09-27/build_overlay.py

Decision sources, in precedence order:
  1. OVERRIDES below (user rule on 的/地/得, inversion-by-effect, reconciled.json relabels,
     and judgement calls) — every one carries a note.
  2. v5_to_merged.csv rows whose mapping_kind is 1:1 or merge (deterministic).
  A split/dropped CSV row with no override is a hard error (never guessed).

explanation_variant (word_choice only) is always a judgement, so it lives in WC_VARIANT with a
note, and those entries are sent to the blind reviewer file even when the type is deterministic.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

LANGS = ("zh", "ja", "en")
SETS = {
    "gold": lambda l: ROOT / "tests" / "fixtures" / "dt_gold" / f"{l}.json",
    "silver": lambda l: ROOT / "data" / "eval" / "jev_dt_2026-09-26" / "silver" / f"{l}_final3.json",
}

INV = "meaning_inversion"
DE_NOTE = ("User decision 2026-09-27: ALL 的/地/得 misuse is an error (de_particle); overrides "
           "reconciled.json ({rc}). Severity kept from source label (minor).")

# (item_id, error_index) -> (v6_type, v6_severity, basis, note)
OVERRIDES: dict[tuple[str, int], tuple[str, str, str, str]] = {
    # ---- user rule: 的/地/得 --------------------------------------------------------------
    ("zh_seed_11", 0): ("de_particle", "minor", "user_rule_de", DE_NOTE.format(rc="was ESCALATE") + " 的-for-得 before a degree complement."),
    ("zh_multi_02", 0): ("de_particle", "minor", "user_rule_de", DE_NOTE.format(rc="was ESCALATE") + " 的-for-得 before a degree complement."),
    ("zh_silver_20", 0): ("de_particle", "minor", "user_rule_de", DE_NOTE.format(rc="was variant_ok") + " 的-for-地 before a verb; v6 de_particle definition must drop its 的-for-地 exemption."),
    ("zh_silver_29", 0): ("de_particle", "minor", "user_rule_de", DE_NOTE.format(rc="agreed keep") + " Attributive 地-for-的; covered once the definition reads 'wrong 的/得/地 choice'."),
    # ---- reconciled.json relabels ----------------------------------------------------------
    ("ja_seed_01", 0): ("wa_ga", "major", "relabel_decision", "reconciled.json: keep wa_ga major — は marks a relative-clause subject (部品はセットになったもの), jev rule 2."),
    ("ja_multi_01", 0): ("wa_ga", "major", "relabel_decision", "reconciled.json: keep wa_ga major — same relative-clause subject error as ja_seed_01."),
    ("ja_multi_05", 0): ("wa_ga", "major", "relabel_decision", "reconciled.json: keep wa_ga major — 私たちは作るもの is a relative-clause subject, jev rule 2."),
    ("en_seed_10", 0): ("word_choice", "major", "relabel_decision", "reconciled.json: pronoun_reference split — antecedent-number error (it for them) is outside v6 `pronoun`; retyped word_choice, severity major (referent shift)."),
    ("en_multi_03", 2): ("word_choice", "major", "relabel_decision", "reconciled.json: same as en_seed_10 (it for them), word_choice major."),
    ("en_silver_13", 0): ("word_choice", "major", "relabel_decision", "reconciled.json: 'him' for 'them' unanchors the referent; word_choice major."),
    # ---- inversion by effect (relabels) ----------------------------------------------------
    ("zh_seed_13", 0): (INV, "critical", "inversion_by_effect", "Antonym substitution 伤心 (sad) for 开心 (happy) reverses the evaluative polarity of the core claim. word_choice -> meaning_inversion."),
    ("zh_multi_03", 1): (INV, "critical", "inversion_by_effect", "Same 伤心/开心 antonym reversal as zh_seed_13."),
    ("zh_silver_07", 0): (INV, "critical", "inversion_by_effect", "Added 不 negates the proposition (organs are NOT removed). Surface is an addition, effect is a polarity flip."),
    ("zh_silver_08", 0): (INV, "critical", "inversion_by_effect", "Dropped 不 flips polarity (it IS an expensive brand). Surface is an omission, effect is a polarity flip."),
    ("zh_silver_10", 0): (INV, "critical", "inversion_by_effect", "很少 (very few) for 很多 (very many): scalar antonym, quantity reversed."),
    ("zh_silver_11", 0): (INV, "critical", "inversion_by_effect", "运送出 (transport OUT of) for 运送到 (transport TO) the hospital reverses direction of movement. Source directional_complement/major; severity raised to critical per meaning_inversion default."),
    ("zh_silver_12", 0): (INV, "critical", "inversion_by_effect", "捐献者 (donor) for 受者 (recipient): searching the waiting list for a donor swaps the recipient role."),
    ("ja_seed_15", 0): (INV, "critical", "inversion_by_effect", "簡単 (simple) for 複雑 (complex): antonym, degree reversed."),
    ("ja_multi_04", 0): (INV, "critical", "inversion_by_effect", "Same 簡単/複雑 antonym reversal as ja_seed_15."),
    ("ja_silver_18", 0): (INV, "critical", "inversion_by_effect", "不要 (unnecessary) for 必要 (necessary): negated antonym, polarity flip."),
    ("ja_silver_21", 0): (INV, "critical", "inversion_by_effect", "Arm-to-move-the-motor for motor-to-move-the-arm: agent/patient swap."),
    ("ja_silver_22", 0): (INV, "critical", "inversion_by_effect", "Dropped negation (動く for 動かない) flips the condition's polarity."),
    ("ja_silver_23", 0): (INV, "critical", "inversion_by_effect", "関係なく (regardless of) for 次第で (depending on): denies the dependency the reference asserts."),
    ("en_seed_15", 0): (INV, "critical", "inversion_by_effect", "'without' for 'with' reverses polarity; user's canonical example. preposition -> meaning_inversion."),
    ("en_multi_04", 1): (INV, "critical", "inversion_by_effect", "Same with/without reversal as en_seed_15."),
    ("en_silver_20", 0): (INV, "critical", "inversion_by_effect", "Added negation 'cannot' flips polarity. Surface addition, effect polarity flip."),
    ("en_silver_21", 0): (INV, "critical", "inversion_by_effect", "Added negation 'can't' flips polarity."),
    ("en_silver_22", 0): (INV, "critical", "inversion_by_effect", "'from' for 'to' reverses direction of movement. preposition -> meaning_inversion."),
    ("en_silver_23", 0): (INV, "critical", "inversion_by_effect", "'few' for 'many': scalar antonym, quantity reversed (not a mere many->some weakening)."),
    ("en_silver_25", 0): (INV, "critical", "inversion_by_effect", "'first' for 'later' reverses temporal order (antonym on the before/after axis). Borderline: could be read as word_choice, but the ordering claim is inverted."),
    ("en_silver_27", 0): (INV, "critical", "inversion_by_effect", "'avoid' for 'use': antonym, the recommended action is reversed."),
    # ---- judged NOT an inversion (type unchanged from CSV, decision recorded) ------------
    ("zh_silver_09", 0): ("word_choice", "major", "judgement", "一点 (a little) for 很多 (a lot): quantity weakened, not reversed — the claim that the pattern evokes happiness/friendship still holds. Analogous to many->some, so NOT meaning_inversion."),
    # ---- user decisions 2026-09-27 (Decision B: reviewer's call on the item escalations) --
    ("zh_silver_18", 0): ("omission", "major", "user_decision", "User decision 2026-09-27 (reviewer's call): 会看情况 drops the matching criteria (condition, blood type, tissue match): content lost, nothing reversed, so omission not meaning_inversion; critical is reserved for inversion-grade effects -> major."),
    ("zh_silver_37", 0): ("ba_bei", "major", "user_decision", "User decision 2026-09-27 (reviewer's call): 把心情变好 uses 把 with a non-disposal (intransitive-result) verb where 觉得 was needed -> v6 ba_bei, a construction error, not a lexical choice. Severity major (reviewer's)."),
    ("ja_silver_19", 0): ("addition", "minor", "user_decision", "User decision 2026-09-27 (reviewer's call): the added ない sits inside a 'check whether' clause (掴めないか確認); the whether-check is truth-conditionally the same act, so the core claim is not reversed -> addition/minor, NOT meaning_inversion."),
    ("en_silver_17", 0): ("word_choice", "minor", "user_decision", "User decision 2026-09-27 (reviewer's call): 'says the motors' for 'tells the motors' - meaning fully recoverable -> minor (source major)."),
    ("ja_silver_20", 0): ("word_choice", "major", "judgement", "たくさん (many) for いくつか (some/several): degree change, not a reversal — the user's many->some example. NOT meaning_inversion."),
    ("en_silver_11", 0): ("word_choice", "major", "judgement", "'fourth' for 'third': wrong ordinal, a factual mismatch but not a polarity/direction/scalar reversal. NOT meaning_inversion."),
    ("ja_multi_04", 2): ("case_particle", "major", "judgement", "手が動かす for 手を動かす could be read as agent/patient swap, but the result is ill-formed (transitive 動かす with no object) rather than a coherent reversed proposition; the 'moving your hands' claim survives. Kept case_particle."),
    ("ja_silver_27", 0): ("cohesion_connective", "major", "judgement", "しかし (however) for そして (and): wrong logical relation, but the propositions themselves are not reversed; not meaning_inversion. Arguably v6 `contradiction` (wrong connective relation); kept cohesion_connective per CSV pending ADR-031 boundary rule."),
}

# word_choice explanation_variant (3-way, ADR-031 Decision A, 2026-09-27):
#   wrong_sense        = the SAME lemma used in a different one of its own senses (narrow)
#   shared_translation = a DIFFERENT word sharing an L1 gloss with the correct word
#   wrong_word         = anything else that does not fit the idea
# Precedence: same lemma -> wrong_sense; shared L1 gloss -> shared_translation; else wrong_word.
# L1 assumed: en for zh/ja L2 learners; zh or ja for en L2 learners.
# (variant, one-line note, uncertain). Applies to every final word_choice entry.
WC_VARIANT: dict[tuple[str, int], tuple[str, str, bool]] = {
    ("zh_seed_06", 0): ("shared_translation", "轻松 and 放松 are different words sharing the L1 gloss 'relaxed'; 轻松 is light/easy, not the unwound state. Resolves escalation (author: gloss overlap; reviewer: different lexeme, so not wrong_sense).", False),
    ("zh_seed_12", 0): ("wrong_word", "浅 (pale) is a different word from 正 (true/pure colour); no shared gloss.", False),
    ("zh_multi_02", 1): ("shared_translation", "普通 and 简单 are different words that can both be rendered 'plain' in English; 普通 is ordinary, not simple in design. Resolves escalation. UNCERTAIN: 'plain' is not a core dictionary gloss of 普通 (common/ordinary); if the sense-dictionary lookup finds no shared gloss this falls to wrong_word.", True),
    ("zh_silver_09", 0): ("wrong_word", "一点 is a different quantity word from 很多; no shared gloss, not a sense confusion.", False),
    ("zh_silver_17", 0): ("wrong_word", "很好看 (pretty) replaces 栩栩如生 (lifelike) with a different, vaguer word.", False),
    ("ja_seed_08", 0): ("shared_translation", "持つ and 掴む are different verbs sharing the L1 gloss 'hold'; 持つ is hold/carry, not grip/grasp. Resolves escalation.", False),
    ("ja_seed_14", 0): ("wrong_word", "難しい (difficult) for 面白い (interesting): different word, no shared gloss, not antonyms.", False),
    ("ja_multi_01", 1): ("wrong_word", "面白さ (fun) is a vaguer different word for 醍醐味 (the real pleasure); no shared core gloss.", False),
    ("ja_multi_02", 0): ("shared_translation", "最初 and まず are different words sharing the L1 gloss 'first'; 最初 is 'at the beginning', not enumerative 'first of all'. Was agreed wrong_sense under the 2-way; a different lemma cannot be narrow wrong_sense.", False),
    ("ja_multi_03", 0): ("wrong_word", "Same 難しい/面白い substitution as ja_seed_14.", False),
    ("ja_multi_04", 1): ("shared_translation", "仕事 used for a part's function via L1 'job' (the part's job); 役割 is the needed word. Was agreed wrong_sense; 役割 is a different lemma. UNCERTAIN: JMdict glosses (work/job/task vs role/part/function) share no exact gloss, so a strict lookup would give wrong_word.", True),
    ("ja_silver_20", 0): ("wrong_word", "たくさん for いくつか: different quantity word, no shared gloss.", False),
    ("ja_silver_24", 0): ("wrong_word", "高い for 格別: different word; loses 格別's intensity (reviewer concession: collocation claim dropped).", False),
    ("ja_silver_28", 0): ("wrong_word", "先にある (at the tip) for 指先にあたる (corresponds to the fingertip): different expression.", False),
    ("ja_silver_29", 0): ("wrong_word", "わかるようになる for 理解する手助けになる: different predicate, loses 'helps'.", False),
    ("en_seed_06", 0): ("wrong_word", "'nice' for 'fun': different word, no shared zh/ja gloss (好/いい vs 好玩/楽しい).", False),
    ("en_seed_10", 0): ("wrong_word", "'it' for 'them': wrong pronoun form (number), not a gloss or sense confusion.", False),
    ("en_seed_14", 0): ("wrong_word", "'foot' for 'hand': different word.", False),
    ("en_multi_03", 0): ("shared_translation", "'key' and 'important' share the L1 gloss 重要 (zh 重要的/关键的, ja 重要な); 'key' is used in its correct 'crucial' sense, so not wrong_sense. Resolves escalation. UNCERTAIN: arguably an acceptable near-synonym (not an error); en has no zh/ja glosses yet, so the lookup cannot confirm.", True),
    ("en_multi_03", 2): ("wrong_word", "'it' for 'them': wrong pronoun form (number).", False),
    ("en_silver_11", 0): ("wrong_word", "'fourth' for 'third': different word.", False),
    ("en_silver_13", 0): ("wrong_word", "'him' for 'them': wrong pronoun form (person/number).", False),
    ("en_silver_15", 0): ("wrong_word", "'everyone' for 'you' (plus inserted 'also'): different word.", False),
    ("en_silver_17", 0): ("shared_translation", "'say' and 'tell' share the L1 gloss 说 (zh) / 言う (ja); 'say' cannot take the addressee. Resolves escalation (reviewer: not wrong_sense; author: gloss overlap).", False),
    ("en_silver_28", 0): ("shared_translation", "'engine' and 'motor' share the zh L1 gloss 发动机 (and 马达 overlap); 'engine' has no electric-servo sense, so not wrong_sense. Resolves escalation.", False),
    ("en_silver_31", 0): ("wrong_word", "'thing' for 'gripper': vague different word.", False),
    ("en_silver_32", 0): ("wrong_word", "'stuff' for 'commands': vague different word.", False),
    ("en_silver_35", 0): ("wrong_word", "'expensive' for 'important': different word; a 贵重-style L1 path is conceivable but the two share no gloss.", False),
}


def load_csv() -> dict[tuple[str, str], dict]:
    with open(HERE / "v5_to_merged.csv", encoding="utf-8") as f:
        return {(r["lang"], r["v5_subtype"]): r for r in csv.DictReader(f)}


def load_items(lang: str, set_name: str) -> list[dict]:
    with open(SETS[set_name](lang), encoding="utf-8") as f:
        return json.load(f)


def build_overlay():
    csvmap = load_csv()
    overlay, used_over, used_wc = [], set(), set()
    items_by_key = {}
    for lang in LANGS:
        for set_name in SETS:
            for it in load_items(lang, set_name):
                items_by_key[(it["id"])] = (lang, set_name, it)
                for i, e in enumerate(it["expected_errors"]):
                    key = (it["id"], i)
                    v5, sev = e["subtype_v5_target"], e["severity_v2"]
                    entry = {
                        "item_id": it["id"], "set": set_name, "lang": lang, "error_index": i,
                        "learner_form": e["learner_form"], "corrected_form": e["corrected_form"],
                        "v5_subtype": v5, "v5_severity": sev,
                    }
                    if key in OVERRIDES:
                        t, s, basis, note = OVERRIDES[key]
                        used_over.add(key)
                    else:
                        row = csvmap[(lang, v5)]
                        if row["mapping_kind"] not in ("1:1", "merge"):
                            raise SystemExit(f"{key}: CSV mapping {row['mapping_kind']} for {v5} needs an override")
                        t, s, basis, note = row["merged_type(s)"], sev, "csv_deterministic", None
                    entry.update(v6_type=t, v6_severity=s, basis=basis)
                    judged = []
                    if t == "word_choice":
                        if key not in WC_VARIANT:
                            raise SystemExit(f"{key}: word_choice without explanation_variant")
                        var, vnote, unsure = WC_VARIANT[key]
                        used_wc.add(key)
                        entry["explanation_variant"] = var
                        if unsure:
                            entry["variant_uncertain"] = True
                        judged.append("explanation_variant")
                        note = f"{note} | variant: {vnote}" if note else f"variant: {vnote}"
                    entry["judgement_fields"] = judged
                    entry["note"] = note
                    overlay.append(entry)
    stale = (set(OVERRIDES) - used_over) | (set(WC_VARIANT) - used_wc)
    if stale:
        raise SystemExit(f"unused decisions (key typo?): {sorted(stale)}")
    return overlay, items_by_key


def apply_resolutions(overlay) -> None:
    """Mark every entry final and attach a `resolution` to each entry that went through the
    blind-review exchange (overlay_reconciled.json). Deterministic CSV entries were never
    reviewed and carry no resolution.

      agreed            blind agreement, final unchanged
      reviewer_conceded reviewer conceded in the one-exchange round
      author_conceded   author conceded (none in this round, kept for the enum)
      user_decision     escalated to the user, or re-classified under Decision A (3-way variant)
    """
    with open(HERE / "overlay_reconciled.json", encoding="utf-8") as f:
        rec = {(e["item_id"], e["error_index"]): e for e in json.load(f)["entries"]}
    fields = ("v6_type", "v6_severity", "explanation_variant")
    for e in overlay:
        e["final"] = True
        r = rec.get((e["item_id"], e["error_index"]))
        if r is None:
            continue
        mine = {k: e.get(k) for k in fields}
        if r["final"] == "ESCALATE":
            e["resolution"] = "user_decision"
            continue
        theirs = {k: r["final"].get(k) for k in fields}
        res_text = str(r.get("resolution", ""))
        if mine != theirs:
            # only Decision A (variant) may move an agreed final
            if {k: mine[k] for k in fields[:2]} != {k: theirs[k] for k in fields[:2]}:
                raise SystemExit(f"{e['item_id']}#{e['error_index']}: overlay {mine} != reconciled final {theirs}")
            e["resolution"] = "user_decision"
            e["note"] = f"{e['note']} | reconciled final was {theirs['explanation_variant']}; re-classified under Decision A"
        elif res_text.startswith("Reviewer concedes"):
            e["resolution"] = "reviewer_conceded"
        elif res_text.startswith("Author concedes"):
            e["resolution"] = "author_conceded"
        else:
            e["resolution"] = "agreed"
    missing = set(rec) - {(e["item_id"], e["error_index"]) for e in overlay}
    if missing:
        raise SystemExit(f"reconciled entries not in overlay: {sorted(missing)}")


def v6_dimension_maps() -> dict[str, dict[str, str]]:
    with open(HERE / "merged_taxonomy.json", encoding="utf-8") as f:
        tax = json.load(f)
    return {lang: {t["id"]: t["dimension"] for t in tax[lang]} for lang in LANGS}


def band_changes(overlay, items_by_key):
    """Shim: derive_bands looks dimensions up in helper.V5_DIMENSION[subtype_v5_target].
    We swap that module-level dict per language for the v6 map (the helper file is untouched)
    and feed v6 types through the same key."""
    import scripts.dt_gold_seed_helper as helper

    original = dict(helper.V5_DIMENSION)
    dims = v6_dimension_maps()
    by_item: dict[str, list] = {}
    for e in overlay:
        by_item.setdefault(e["item_id"], []).append(e)
    changes, baseline_mismatch = [], []
    try:
        for item_id, (lang, set_name, it) in items_by_key.items():
            exp = it["expected_bands"]
            judged = {"range": exp["range"], "naturalness": exp["naturalness"]}
            helper.V5_DIMENSION.clear(); helper.V5_DIMENSION.update(original)
            v5b = helper.derive_bands(it["expected_errors"], judged, offline=True)
            if v5b != exp:
                baseline_mismatch.append(item_id)
            errs = [{"subtype_v5_target": e["v6_type"], "severity_v2": e["v6_severity"]}
                    for e in sorted(by_item.get(item_id, []), key=lambda x: x["error_index"])]
            helper.V5_DIMENSION.clear(); helper.V5_DIMENSION.update(dims[lang])
            v6b = helper.derive_bands(errs, judged, offline=True)
            diff = {d: [exp[d], v6b[d]] for d in exp if exp[d] != v6b[d]}
            if diff:
                changes.append({
                    "item_id": item_id, "set": set_name, "lang": lang,
                    "expected_bands": exp, "v6_bands": v6b, "changed": diff,
                    "v6_errors": [[e["subtype_v5_target"], e["severity_v2"]] for e in errs],
                })
    finally:
        helper.V5_DIMENSION.clear(); helper.V5_DIMENSION.update(original)
    return changes, baseline_mismatch


def main():
    overlay, items_by_key = build_overlay()
    apply_resolutions(overlay)
    changes, baseline_mismatch = band_changes(overlay, items_by_key)

    blind = []
    for e in overlay:
        if e["basis"] == "csv_deterministic" and not e["judgement_fields"]:
            continue
        _, _, it = items_by_key[e["item_id"]]
        blind.append({
            "item_id": e["item_id"], "set": e["set"], "lang": e["lang"], "error_index": e["error_index"],
            "reference": it["reference"], "reproduction": it["reproduction"],
            "learner_form": e["learner_form"], "corrected_form": e["corrected_form"],
            "v5_subtype": e["v5_subtype"], "v5_severity": e["v5_severity"],
        })

    def dump(name, obj):
        with open(HERE / name, "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")

    dump("v6_label_overlay.json", {
        "taxonomy": "v6 (ADR-031, proposed)", "built_by": "build_overlay.py", "date": "2026-09-27",
        "final": True,
        "finalised": "2026-09-27: blind review (overlay_reconciled.json) + user Decision A (word_choice "
                     "explanation_variant is 3-way: wrong_word | wrong_sense (narrow, same lemma) | "
                     "shared_translation) + Decision B (reviewer's call on zh_silver_18, zh_silver_37, "
                     "ja_silver_19, en_silver_17).",
        "resolution_scope": "`resolution` is set only on the 61 entries that went through blind review; "
                            "csv_deterministic entries outside that set were never contested and carry none.",
        "entries": overlay,
    })
    dump("overlay_band_changes.json", {
        "method": "scripts/dt_gold_seed_helper.derive_bands(offline=True) with V5_DIMENSION swapped "
                  "per language for merged_taxonomy.json dimensions; range/naturalness taken from expected_bands",
        "v5_baseline_mismatches": baseline_mismatch,
        "v5_baseline_note": "en_silver_24 already fails derive_bands under v5: its note says MEANING INVERSION "
                            "(agent swap, 'The Arduino writes instructions for you') but expected_errors is empty, "
                            "so the derived understandability is 4 vs expected 2. Not an overlay entry (no labelled "
                            "error); needs a meaning_inversion/critical error record added upstream.",
        "count": len(changes), "changes": changes,
    })
    # The blind file is the historical record handed to the reviewer (2-way variant era); never
    # overwrite it once it exists.
    if not (HERE / "overlay_blind_for_reviewer.json").exists():
        dump("overlay_blind_for_reviewer.json", {
            "instructions": "Assign a v6 type/severity (and explanation_variant wrong_word|wrong_sense for word_choice) blind.",
            "count": len(blind), "entries": blind,
        })

    from collections import Counter
    print("entries", len(overlay))
    print("basis", dict(Counter(e["basis"] for e in overlay)))
    print("inversions", [f"{e['item_id']}#{e['error_index']}" for e in overlay if e["v6_type"] == INV])
    print("wc variants", dict(Counter(e.get("explanation_variant") for e in overlay if e["v6_type"] == "word_choice")))
    print("resolution", dict(Counter(e.get("resolution") for e in overlay)))
    print("variant uncertain", [f"{e['item_id']}#{e['error_index']}" for e in overlay if e.get("variant_uncertain")])
    print("band changes", len(changes), "| v5 baseline mismatches", baseline_mismatch)
    for c in changes:
        print(" ", c["item_id"], c["changed"])
    print("blind", len(blind))


if __name__ == "__main__":
    main()
