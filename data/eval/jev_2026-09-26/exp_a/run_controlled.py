# -*- coding: utf-8 -*-
import env_setup  # noqa: F401
import json
import sys
from controlled_set import CONTROLLED
from rubric import RUBRIC_NATIVE, RUBRIC_ENGLISH_CONTROL
from jev_client import call_jev_batch, get_running_totals

OUT = "controlled_results.json"

def build_requests():
    reqs = []
    for item in CONTROLLED:
        lang = item["lang"]
        for label, text_key in (("correct", "correct"), ("corrupted", "corrupted")):
            sentence = item[text_key]
            reqs.append({
                "state": {"sentence": sentence},
                "questions": RUBRIC_NATIVE[lang],
                "_meta": {
                    "lang": lang, "sense_id": item["sense_id"], "defect_type": item["defect_type"],
                    "subtlety": item["subtlety"], "label": label, "sentence": sentence,
                    "arm": "native", "note": item["note"],
                },
            })
    # English-prompt control: subset of zh/ja items, subtlety in {obvious, subtle}
    for item in CONTROLLED:
        if item["lang"] not in ("zh", "ja"):
            continue
        if item["subtlety"] not in ("obvious", "subtle"):
            continue
        for label, text_key in (("correct", "correct"), ("corrupted", "corrupted")):
            sentence = item[text_key]
            reqs.append({
                "state": {"sentence": sentence},
                "questions": RUBRIC_ENGLISH_CONTROL[item["lang"]],
                "_meta": {
                    "lang": item["lang"], "sense_id": item["sense_id"], "defect_type": item["defect_type"],
                    "subtlety": item["subtlety"], "label": label, "sentence": sentence,
                    "arm": "english_control", "note": item["note"],
                },
            })
    return reqs

def main():
    reqs = build_requests()
    print(f"Total requests: {len(reqs)}", file=sys.stderr)
    results = call_jev_batch(reqs, max_workers=8)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    cost, n = get_running_totals()
    n_err = sum(1 for r in results if r.get("_error"))
    print(f"Done. {n} calls, ${cost:.6f} total cost, {n_err} errors. Wrote {OUT}", file=sys.stderr)

if __name__ == "__main__":
    main()
