# -*- coding: utf-8 -*-
"""Distractor-plausibility comparison against the LIVE gemini-3.5-flash-lite
v7 two-axis judge (data/eval/distractor_ablation_2026-08-20.json, 358 records,
all langs, already-judged, no human gold exists for this axis -- per memory
'gold frame built, unlabelled'). Passage/question/answer text is joined in
from the (unlabelled) gold-frame CSVs by qid, since the ablation file itself
only stores distractor text + scores, not the passage.

jev is asked the SAME two axes (fit, confusability) the live judge uses, in
native language, as `score` questions (0-4 internally; +1 to compare on the
judge's 1-5 scale). A jev verdict is derived with the identical rule
services/test_generation/schemas.py:axes_to_verdict implements, for a
same-content 3-way Cohen's kappa against the live judge's stored verdict.

Also asks a standalone noul "is this distractor definitely wrong / not also
a correct answer" question (the literal thing the task brief asked for) --
reported descriptively only, since there is no gold and no existing judge
column that answers exactly this (the live judge's axes are fit+confusability,
not an also-correct call).
"""
import env_setup  # noqa: F401
import csv
import json
import sys
from collections import defaultdict
from rubric import RUBRIC_DISTRACTOR
from jev_client import call_jev_batch, get_running_totals

REPO = r"c:\Users\James\Documents\Coding\LinguaLoop\WebApp"
LANG_NAME = {1: "zh", 2: "en", 3: "ja"}
OUT = "distractor_results.json"

CSV_FILES = [
    r"\data\eval\distractor_gold_frame_2026-08_zh_primary.csv",
    r"\data\eval\distractor_gold_frame_2026-08_zh_overlap.csv",
    r"\data\eval\distractor_gold_frame_2026-08_en_primary.csv",
    r"\data\eval\distractor_gold_frame_2026-08_en_overlap.csv",
    r"\data\eval\distractor_gold_frame_2026-08_ja_primary.csv",
    r"\data\eval\distractor_gold_frame_2026-08_ja_overlap.csv",
]

def load_passage_index():
    idx = {}
    for rel in CSV_FILES:
        path = REPO + rel
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                qid = row["item_id"].split("#")[0]
                if qid not in idx:
                    idx[qid] = {"passage": row["passage"], "question": row["question"], "answer": row["answer"]}
    return idx

# state->score noul question for the "definitely wrong" descriptive probe
NOUL_WRONG = {
    "zh": {"instructions": "distractor字段里的选项，在这道题的语境下，是否明确是错误答案（而不是另一种也说得通的正确答案）？",
           "criteria": {"true": "该选项明确是错的，不是问题的正确答案。", "false": "该选项也可能是正确答案，或读者难以排除它。"}},
    "en": {"instructions": "Given the context, is the option in `distractor` definitely a wrong answer (as opposed to another defensible correct answer)?",
           "criteria": {"true": "The option is clearly wrong, not a correct answer to the question.", "false": "The option might also be correct, or a reader could not confidently rule it out."}},
    "ja": {"instructions": "この文脈において、distractorフィールドの選択肢は明確に誤った答えですか（もう一つの正解ではなく）？",
           "criteria": {"true": "その選択肢は明らかに誤りであり、質問の正解ではない。", "false": "その選択肢も正解である可能性があるか、読者が確実に除外できない。"}},
}

def build_requests(ablation, passage_idx):
    reqs = []
    skipped = 0
    for rec in ablation:
        lang = LANG_NAME[rec["lang"]]
        qid = rec["qid"]
        pinfo = passage_idx.get(qid)
        if not pinfo:
            skipped += 1
            continue
        for i, dtext in enumerate(rec["distractors"]):
            gemini_fit = rec["ratings"][i] if i < len(rec.get("ratings", [])) else None
            gemini_conf = rec["confusability"][i] if i < len(rec.get("confusability", [])) else None
            gemini_verdict = rec["verdicts"][i] if i < len(rec.get("verdicts", [])) else None
            state = {"passage": pinfo["passage"], "question": pinfo["question"], "answer": pinfo["answer"], "distractor": dtext}
            questions = dict(RUBRIC_DISTRACTOR[lang])
            questions = {"fit": RUBRIC_DISTRACTOR[lang]["fit"], "confusability": RUBRIC_DISTRACTOR[lang]["confusability"],
                         "definitely_wrong": dict(type="noul", **NOUL_WRONG[lang])}
            reqs.append({
                "state": state,
                "questions": questions,
                "_meta": {
                    "lang": lang, "qid": qid, "idx": i, "distractor": dtext, "type_code": rec.get("type_code"),
                    "gemini_fit": gemini_fit, "gemini_confusability": gemini_conf, "gemini_verdict": gemini_verdict,
                },
            })
    print(f"skipped {skipped} records with no passage match", file=sys.stderr)
    return reqs

def main():
    with open(REPO + r"\data\eval\distractor_ablation_2026-08-20.json", encoding="utf-8") as f:
        ablation = json.load(f)
    passage_idx = load_passage_index()
    reqs = build_requests(ablation, passage_idx)
    print(f"Total requests: {len(reqs)}", file=sys.stderr)
    results = call_jev_batch(reqs, max_workers=8)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    cost, n = get_running_totals()
    n_err = sum(1 for r in results if r.get("_error"))
    print(f"Done. {n} calls, ${cost:.6f} total cost, {n_err} errors. Wrote {OUT}", file=sys.stderr)

if __name__ == "__main__":
    main()
