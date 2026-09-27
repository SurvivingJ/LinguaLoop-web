# -*- coding: utf-8 -*-
"""Real-gold entailment experiment. Ground truth is STRUCTURAL (per repo
memory 'entailment gold labels are structural and free'): the stated correct
answer = positive class (label=1), each of its distractors = negative class
(label=0). This is a lower-bound-only signal (a distractor is a proxy for a
hallucinated/wrong answer, not necessarily the hardest real negative), but it
is real production content, not synthetic corruption.

Source content: WebApp/data/eval/entailment_sample_150.json (50 qids/lang x3
langs, passage+question+answer+3 distractors each).
Existing-judge verdicts for comparison: WebApp/data/eval/entailment_v3_2026-08-19.json
(one model per lang: zh=deepseek-chat, en=gemini-3.5-flash-lite, qwen=ja) and
entailment_v3_ja_models_2026-08-19.json (ja, both gemini-3.5-flash-lite and
deepseek-chat) -- covers item_id suffixes :pos/:neg0/:neg1 only (not :neg2).
"""
import env_setup  # noqa: F401
import json
import sys
from rubric import RUBRIC_ENTAILMENT
from jev_client import call_jev_batch, get_running_totals

REPO = r"c:\Users\James\Documents\Coding\LinguaLoop\WebApp"
LANG_NAME = {1: "zh", 2: "en", 3: "ja"}
OUT = "entailment_results.json"

def load_content():
    with open(REPO + r"\data\eval\entailment_sample_150.json", encoding="utf-8") as f:
        return json.load(f)

def build_requests(content):
    reqs = []
    for row in content:
        lang = LANG_NAME[row["lang"]]
        base_meta = dict(lang=lang, qid=row["qid"], passage=row["passage"],
                          question=row["question"], type_code=row.get("type_code"))
        # positive
        reqs.append({
            "state": {"passage": row["passage"], "question": row["question"], "candidate": row["answer"]},
            "questions": RUBRIC_ENTAILMENT[lang],
            "_meta": dict(base_meta, item_id=f"{row['qid']}:pos", candidate=row["answer"], gold_label=1),
        })
        for i, d in enumerate(row["distractors"]):
            reqs.append({
                "state": {"passage": row["passage"], "question": row["question"], "candidate": d},
                "questions": RUBRIC_ENTAILMENT[lang],
                "_meta": dict(base_meta, item_id=f"{row['qid']}:neg{i}", candidate=d, gold_label=0),
            })
    return reqs

def main():
    content = load_content()
    reqs = build_requests(content)
    print(f"Total requests: {len(reqs)}", file=sys.stderr)
    results = call_jev_batch(reqs, max_workers=8)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    cost, n = get_running_totals()
    n_err = sum(1 for r in results if r.get("_error"))
    print(f"Done. {n} calls, ${cost:.6f} total cost, {n_err} errors. Wrote {OUT}", file=sys.stderr)

if __name__ == "__main__":
    main()
