# -*- coding: utf-8 -*-
"""Cascade 2 stage 2: jev verifies each error CLAIMED by the cheap LLM's item-level recall pass
(yes/no validity + minor/major/critical severity). Usage: python verify.py <set> [--limit N]"""
from __future__ import annotations
import argparse, concurrent.futures as cf, json, os
import common as C, lib

R = lib.S.R
T = lib.T
OUT = os.path.join(C.HERE, "verify")
os.makedirs(OUT, exist_ok=True)

KEYS = {
    "en": ("reference sentence", "learner sentence", "claimed error"),
    "zh": ("参考译文句子", "学习者译文句子", "被指出的错误"),
    "ja": ("参照文", "学習者文", "指摘された誤り"),
}
CLAIM_FMT = {
    "en": "The learner wrote \"{l}\" where the reference has \"{c}\". Claimed error type: {g}",
    "zh": "学习者写的是“{l}”，而参考译文是“{c}”。被指出的错误类型：{g}",
    "ja": "学習者は「{l}」と書いたが、参照文は「{c}」である。指摘された誤りの種類：{g}",
}
VALID = {
    "en": {"instructions": "A grader claims the `{lk}` contains the error described in `{ck}`, compared with the `{rk}`. Is this claim correct, i.e. is it a real translation or language error rather than an acceptable variation?",
           "true": "The claim is correct: this is a real error a careful native-speaker teacher would mark.",
           "false": "The claim is wrong: the learner's wording is an acceptable variation (synonym, equally natural phrasing) or the described difference does not exist."},
    "zh": {"instructions": "有评分者认为，对照【{rk}】，【{lk}】中存在【{ck}】所描述的错误。这个判断是否正确——即这确实是翻译或语言错误，而不是可以接受的表达差异？",
           "true": "判断正确：这是认真的母语教师会标出的真正错误。",
           "false": "判断错误：学习者的表达是可以接受的差异（同义词、同样自然的说法），或所描述的差异并不存在。"},
    "ja": {"instructions": "ある採点者が、「{rk}」と比べて「{lk}」には「{ck}」に書かれた誤りがあると指摘しています。この指摘は正しいですか。つまり、許容される言い換えではなく、本当に翻訳上または言語上の誤りですか。",
           "true": "指摘は正しい：注意深い母語話者の教師なら誤りとして指摘する本当の誤りである。",
           "false": "指摘は誤り：学習者の表現は許容される言い換え（類義語、同じくらい自然な表現）であるか、指摘された違いは存在しない。"},
}
SEVQ = {
    "en": "How severe is the error described in `{ck}` in the `{lk}`? Pick \"no_error\" if it is not an error.",
    "zh": "【{lk}】中【{ck}】所描述的错误有多严重？如果不是错误，请选择“无错误”。",
    "ja": "「{lk}」にある「{ck}」に書かれた誤りはどの程度深刻ですか。誤りでない場合は「誤りなし」を選んでください。",
}


def build_request(lang, ref_sent, learner_sent, claim):
    rk, lk, ck = KEYS[lang]
    gloss = T.SUBTYPE_GLOSS[lang].get(claim["subtype"], claim["subtype"])
    state = {rk: ref_sent, lk: learner_sent, ck: CLAIM_FMT[lang].format(l=claim["learner"], c=claim["correct"], g=gloss)}
    v = VALID[lang]
    sev = R.SEVERITY_CHOICE_LEVELS[lang]
    questions = {
        "claim_valid": {"type": "noul", "instructions": v["instructions"].format(rk=rk, lk=lk, ck=ck),
                        "criteria": {"true": v["true"], "false": v["false"]}},
        "severity": {"type": "choice", "instructions": SEVQ[lang].format(lk=lk, ck=ck),
                     "criteria": {"minor": sev["minor"], "major": sev["major"], "critical": sev["critical"],
                                  "no_error": T.NO_ERROR_OPTION[lang]}},
    }
    return state, questions


def run(set_name, limit):
    for lang in lib.LANGS:
        items = lib.build(lang, set_name)
        jobs = []
        for it in items.values():
            pmap = {p["idx"]: p for p in it["pairs"]}
            for mk, d in it["item_llm"].items():
                for ci, c in enumerate(d["claims"]):
                    if c["pair_idx"] in pmap:
                        jobs.append((it["id"], mk, ci, pmap[c["pair_idx"]], c))
        if limit:
            jobs = jobs[:limit]

        def do(j):
            iid, mk, ci, p, c = j
            st, q = build_request(lang, p["ref"], p["learner"], c)
            r = C.jev(st, q, tag=f"verify:{set_name}:{lang}")
            a = r["answers"]
            return {"item_id": iid, "model": mk, "claim_idx": ci, "pair_idx": p["idx"],
                    "valid_p": (a.get("claim_valid") or {}).get("noul"),
                    "sev_probs": (a.get("severity") or {}).get("probabilities"),
                    "sev_choice": (a.get("severity") or {}).get("choice"),
                    "usd": r["usd"], "latency_s": r["latency_s"], "cached": r["cached"]}

        with cf.ThreadPoolExecutor(4) as ex:
            recs = list(ex.map(do, jobs))
        if not limit:
            with open(os.path.join(OUT, f"{lang}_{set_name}.jsonl"), "w", encoding="utf-8") as f:
                for r in recs:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        n = max(len(recs), 1)
        print(f"verify {lang} {set_name}: n={len(recs)} usd/call={sum(r['usd'] for r in recs)/n:.6f} "
              f"lat={sum(r['latency_s'] for r in recs)/n:.2f}s new=${sum(r['usd'] for r in recs if not r['cached']):.5f}")
        if limit:
            for r in recs:
                print("  ", r["valid_p"], r["sev_choice"], r["sev_probs"])
    print(f"cumulative ${C.spent():.5f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("set", choices=("silver", "gold"))
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    run(a.set, a.limit)
