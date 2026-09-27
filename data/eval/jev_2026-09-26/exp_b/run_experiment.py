"""
Orchestrates the full jev tier-classification experiment.
Writes raw results (JSON) to exp_b/raw/*.json. All read-only against Supabase
(data pulled by pull_tests.py already); no DB writes anywhere in this file.
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from jev_prompts import build_request, VALID_TIERS  # noqa: E402
from jev_client import run_batch, get_spend  # noqa: E402

OUT_DIR = os.path.dirname(__file__)
RAW_DIR = os.path.join(OUT_DIR, "raw")
os.makedirs(RAW_DIR, exist_ok=True)

random.seed(20260926)


def load_samples():
    samples = {}
    for lang in ("zh", "en", "ja"):
        with open(os.path.join(OUT_DIR, f"sample_{lang}.json"), encoding="utf-8") as f:
            samples[lang] = json.load(f)
    return samples


def save(name, obj):
    path = os.path.join(RAW_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"wrote {path} ({len(obj) if isinstance(obj, list) else 'obj'})")


def main():
    samples = load_samples()
    all_results = {}

    # ---- Task A: main run, native-language prompts, both modes in one call ----
    print("=== Task A: main run (native prompts, choice+score combined) ===")
    payloads = []
    index = []
    for lang, items in samples.items():
        for it in items:
            req = build_request(lang, it["transcript"])
            label = f"main|{lang}|{it['id']}"
            payloads.append((label, req))
            index.append((lang, it))
    results = run_batch(payloads, concurrency=8)
    main_out = []
    for (lang, it), res in zip(index, results):
        main_out.append({"lang": lang, "item": it, "result": res})
    save("task_a_main.json", main_out)
    print("spend after Task A:", get_spend())

    # ---- Task B: test-retest stability (20 items, 3 repeats each) ----
    print("=== Task B: test-retest (20 items x 3 repeats) ===")
    all_items_flat = [(lang, it) for lang, items in samples.items() for it in items]
    random.shuffle(all_items_flat)
    retest_items = all_items_flat[:20]
    payloads = []
    index = []
    for rep in range(3):
        for lang, it in retest_items:
            req = build_request(lang, it["transcript"])
            label = f"retest|rep{rep}|{lang}|{it['id']}"
            payloads.append((label, req))
            index.append((rep, lang, it))
    results = run_batch(payloads, concurrency=8)
    retest_out = []
    for (rep, lang, it), res in zip(index, results):
        retest_out.append({"rep": rep, "lang": lang, "item": it, "result": res})
    save("task_b_retest.json", retest_out)
    print("spend after Task B:", get_spend())

    # ---- Task C: shuffle sensitivity (same 20 items, choice-mode only, ----
    # ---- criteria key order reversed vs the canonical T1..T6 order) ----
    print("=== Task C: shuffle sensitivity (choice mode, reversed tier order) ===")
    reversed_order = list(reversed(VALID_TIERS))
    payloads = []
    index = []
    for lang, it in retest_items:
        req = build_request(lang, it["transcript"], tier_order=reversed_order,
                             include_choice=True, include_score=False)
        label = f"shuffle|{lang}|{it['id']}"
        payloads.append((label, req))
        index.append((lang, it))
    results = run_batch(payloads, concurrency=8)
    shuffle_out = []
    for (lang, it), res in zip(index, results):
        shuffle_out.append({"lang": lang, "item": it, "result": res})
    save("task_c_shuffle.json", shuffle_out)
    print("spend after Task C:", get_spend())

    # ---- Task D: English-prompt control on zh/ja samples ----
    print("=== Task D: English-prompt control (zh, ja) ===")
    payloads = []
    index = []
    for lang in ("zh", "ja"):
        for it in samples[lang]:
            req = build_request(lang, it["transcript"], english_control=True)
            label = f"encontrol|{lang}|{it['id']}"
            payloads.append((label, req))
            index.append((lang, it))
    results = run_batch(payloads, concurrency=8)
    encontrol_out = []
    for (lang, it), res in zip(index, results):
        encontrol_out.append({"lang": lang, "item": it, "result": res})
    save("task_d_english_control.json", encontrol_out)
    print("spend after Task D:", get_spend())

    # ---- Task E: sanity-check texts (deliberately-levelled) ----
    print("=== Task E: sanity-check texts ===")
    with open(os.path.join(OUT_DIR, "sanity_texts.json"), encoding="utf-8") as f:
        sanity = json.load(f)
    payloads = []
    index = []
    for lang, tiers in sanity.items():
        for tier, texts in tiers.items():
            for i, text in enumerate(texts):
                req = build_request(lang, text)
                label = f"sanity|{lang}|{tier}|{i}"
                payloads.append((label, req))
                index.append((lang, tier, i, text))
    results = run_batch(payloads, concurrency=8)
    sanity_out = []
    for (lang, tier, i, text), res in zip(index, results):
        sanity_out.append({"lang": lang, "true_tier": tier, "idx": i, "text": text, "result": res})
    save("task_e_sanity.json", sanity_out)
    print("spend after Task E:", get_spend())

    print("FINAL SPEND:", get_spend())


if __name__ == "__main__":
    main()
