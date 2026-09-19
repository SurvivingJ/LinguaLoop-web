"""
Zero-LLM measurement run (tasks 2/4/5). Writes a JSON summary to
sandbox/exercise-lab/reports/zero_llm_measurement.json and prints it.
Run from repo root:
    PYTHONIOENCODING=utf-8 venv/Scripts/python sandbox/exercise-lab/prototypes/zero_llm/measure.py
"""
from __future__ import annotations

import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SANDBOX = Path(__file__).resolve().parents[2]
REPO_ROOT = SANDBOX.parent.parent
sys.path.insert(0, str(SANDBOX))
sys.path.insert(0, str(REPO_ROOT))

from lab import db as labdb  # noqa: E402
from prototypes.zero_llm import shim  # noqa: E402
from prototypes.zero_llm.sentence_source import build_sentence_index, measure_coverage  # noqa: E402
from lab.embeddings import unpack_embedding, cosine_similarity  # noqa: E402
from prototypes.zero_llm.semantic_class import classify  # noqa: E402

LANGS = {1: "zh", 2: "en", 3: "ja"}
SAMPLE_SIZE = 1200
RNG_SEED = 20260917


def _p(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def fetch_standard_senses(conn, language_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT ws.id sense_id, ws.vocab_id, v.language_id, v.lemma, v.part_of_speech,
                  v.frequency_rank, ws.definition, ws.definition_level, ws.pronunciation,
                  ws.example_sentence, ws.sense_rank
           FROM dim_word_senses ws JOIN dim_vocabulary v ON v.id = ws.vocab_id
           WHERE v.language_id = ? AND ws.definition_level = 'standard'""",
        (language_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def sample(rows: list[dict], n: int, rng: random.Random) -> list[dict]:
    if len(rows) <= n:
        return rows
    return rng.sample(rows, n)


def main() -> None:
    conn = labdb.connect()
    det = shim.install()
    rng = random.Random(RNG_SEED)

    # --- Task 2: sentence sourcing coverage (full population, not sampled) ---
    _p("building sentence indices...")
    t0 = time.time()
    indices = {lid: build_sentence_index(conn, lid) for lid in LANGS}
    sentence_build_s = round(time.time() - t0, 2)
    _p(f"sentence indices built in {sentence_build_s}s")
    coverage = {LANGS[lid]: measure_coverage(conn, lid, indices[lid]) for lid in LANGS}
    _p(f"coverage computed: {coverage}")

    factory = shim.SenseFactory(conn=conn, sentence_indices=indices)

    # --- sample senses per language ---
    populations = {lid: fetch_standard_senses(conn, lid) for lid in LANGS}
    samples = {lid: sample(populations[lid], SAMPLE_SIZE, rng) for lid in LANGS}
    _p(f"sampled: { {LANGS[k]: len(v) for k,v in samples.items()} }")

    # --- semantic_class heuristic distribution (so the capability-matrix
    # numbers below can be read against how often each class fires) ---
    class_dist: dict[str, dict] = {}
    for lid, rows in samples.items():
        counts: dict[str, int] = {}
        for r in rows:
            c = classify(lid, r["part_of_speech"], r["definition"]) or "NULL"
            counts[c] = counts.get(c, 0) + 1
        class_dist[LANGS[lid]] = counts

    # --- Task 4: true capability matrix + exercises-per-sense distribution ---
    type_counts: dict[str, dict[str, int]] = {}  # lang -> type_code -> #senses producing it
    skip_reasons: dict[str, dict[str, dict[str, int]]] = {}  # lang -> type_code -> reason -> count
    per_sense_totals: dict[str, list[int]] = {LANGS[lid]: [] for lid in LANGS}
    sample_examples: dict[str, list[dict]] = {LANGS[lid]: [] for lid in LANGS}

    for lid, rows in samples.items():
        lang = LANGS[lid]
        type_counts[lang] = {}
        skip_reasons[lang] = {}
        _p(f"generating exercises for {lang} ({len(rows)} senses x2 variants)...")
        t_lang0 = time.time()
        for idx, row in enumerate(rows):
            if idx and idx % 200 == 0:
                _p(f"  {lang}: {idx}/{len(rows)} senses done ({round(time.time()-t_lang0,1)}s elapsed)")
            total_items = 0
            seen_types: set[str] = set()  # across BOTH variants, so a sense reachable
            # via variant A and/or B for a type is counted once, not twice (pct would
            # otherwise exceed 100% for any type both variants can produce).
            for variant in ("A", "B"):
                ctx = factory.context_for(row, variant=variant)
                items, skips = det.generate(ctx)
                total_items += len(items)
                for item in items:
                    if item.type_code not in seen_types:
                        type_counts[lang][item.type_code] = type_counts[lang].get(item.type_code, 0) + 1
                        seen_types.add(item.type_code)
                    if len(sample_examples[lang]) < 60:
                        sample_examples[lang].append({
                            "lemma": row["lemma"], "type_code": item.type_code,
                            "variant": variant, "content": item.content,
                        })
                for skip in skips:
                    bucket = skip_reasons[lang].setdefault(skip.type_code, {})
                    bucket[skip.reason[:80]] = bucket.get(skip.reason[:80], 0) + 1
            per_sense_totals[lang].append(total_items)
        _p(f"  {lang}: done in {round(time.time()-t_lang0,1)}s")

    def bucket_distribution(totals: list[int]) -> dict:
        n = len(totals)
        if n == 0:
            return {}
        b0 = sum(1 for t in totals if t == 0)
        b1 = sum(1 for t in totals if 1 <= t <= 2)
        b2 = sum(1 for t in totals if 3 <= t <= 4)
        b3 = sum(1 for t in totals if t >= 5)
        return {
            "n": n,
            "0_exercises_pct": round(100 * b0 / n, 1),
            "1_2_exercises_pct": round(100 * b1 / n, 1),
            "3_4_exercises_pct": round(100 * b2 / n, 1),
            "5plus_exercises_pct": round(100 * b3 / n, 1),
            "mean_exercises_per_sense": round(sum(totals) / n, 2),
        }

    headline = {lang: bucket_distribution(totals) for lang, totals in per_sense_totals.items()}

    capability_pct = {}
    for lid, rows in samples.items():
        lang = LANGS[lid]
        n = len(rows)
        capability_pct[lang] = {
            t: {"senses": c, "pct_of_sample": round(100 * c / n, 2)}
            for t, c in sorted(type_counts[lang].items(), key=lambda kv: -kv[1])
        }

    # --- latency/throughput on a fixed sub-sample per language ---
    _p("latency/throughput benchmark...")
    latency = {}
    for lid, rows in samples.items():
        lang = LANGS[lid]
        bench_rows = rows[: min(400, len(rows))]

        def run_one(row):
            ctx = factory.context_for(row, variant="A")
            return det.generate(ctx)

        t0 = time.perf_counter()
        for row in bench_rows:
            run_one(row)
        serial_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=8) as ex:
            list(ex.map(run_one, bench_rows))
        conc8_s = time.perf_counter() - t0

        n = len(bench_rows)
        latency[lang] = {
            "n": n,
            "concurrency_1_ms_per_sense": round(1000 * serial_s / n, 3),
            "concurrency_1_senses_per_sec": round(n / serial_s, 1),
            "concurrency_8_ms_per_sense_wallclock": round(1000 * conc8_s / n, 3),
            "concurrency_8_senses_per_sec": round(n / conc8_s, 1),
            "speedup_8_over_1": round(serial_s / conc8_s, 2),
        }

    # --- Task 5: distractor strategy comparison for definition_match ---
    # Reuse the real embeddings build_db.py already computed (top-8000/lang,
    # HashedCharNgramTfidf char-ngram proxy - orthographic, NOT semantic; see
    # README fidelity gap #1). Strategy EMBED = nearest-neighbour by cosine
    # similarity. Strategy NONEMBED = same Zipf-decile tier AND same heuristic
    # semantic_class bucket (frequency-tier + semantic-field, task 5's own
    # spec), matching the shape of production's real (tier-only) approach but
    # extended with the class filter.
    _p("distractor strategy comparison...")
    distractor_compare = {}
    for lid in LANGS:
        lang = LANGS[lid]
        embedded_rows = conn.execute(
            """SELECT ws.id sense_id, v.lemma, ws.definition, embedding, v.frequency_rank,
                      v.part_of_speech
               FROM dim_word_senses ws JOIN dim_vocabulary v ON v.id = ws.vocab_id
               WHERE v.language_id = ? AND ws.definition_level='standard'
               AND ws.embedding IS NOT NULL AND ws.definition IS NOT NULL""",
            (lid,),
        ).fetchall()
        if len(embedded_rows) < 20:
            distractor_compare[lang] = {"note": "fewer than 20 embedded senses — skipped"}
            continue
        pool = [dict(r) for r in embedded_rows]
        import bisect
        freqs_sorted = sorted(p["frequency_rank"] for p in pool if p["frequency_rank"] is not None)
        for p in pool:
            p["vec"] = unpack_embedding(p["embedding"])
            f = p["frequency_rank"]
            if f is None or not freqs_sorted:
                p["tier"] = None
            else:
                pos = bisect.bisect_left(freqs_sorted, f) / max(len(freqs_sorted), 1)
                p["tier"] = min(9, int(pos * 10))
            p["class"] = classify(lid, p["part_of_speech"], p["definition"])

        bench = rng.sample(pool, min(80, len(pool)))
        overlap_counts = []
        high_sim_flags = 0
        examples = []
        for target in bench:
            embed_ranked = sorted(
                (p for p in pool if p["sense_id"] != target["sense_id"]),
                key=lambda p: -cosine_similarity(target["vec"], p["vec"]),
            )[:3]
            embed_defs = {p["definition"].strip() for p in embed_ranked}
            top_sim = cosine_similarity(target["vec"], embed_ranked[0]["vec"]) if embed_ranked else 0.0
            if top_sim > 0.92:
                high_sim_flags += 1

            same_bucket = [
                p for p in pool
                if p["sense_id"] != target["sense_id"]
                and p["tier"] == target["tier"] and p["class"] == target["class"]
            ]
            rng.shuffle(same_bucket)
            nonembed_defs = {p["definition"].strip() for p in same_bucket[:3]}

            overlap = len(embed_defs & nonembed_defs)
            overlap_counts.append(overlap)
            if len(examples) < 5:
                examples.append({
                    "lemma": target["lemma"], "definition": target["definition"],
                    "embed_distractors": list(embed_defs), "embed_top_sim": round(top_sim, 3),
                    "nonembed_distractors": list(nonembed_defs),
                })

        distractor_compare[lang] = {
            "n_compared": len(bench),
            "n_pool_embedded": len(pool),
            "mean_overlap_of_3": round(sum(overlap_counts) / len(overlap_counts), 2),
            "pct_high_similarity_gt_0.92_embed_top1": round(100 * high_sim_flags / len(bench), 1),
            "examples": examples,
        }

    summary = {
        "sentence_index_build_seconds": sentence_build_s,
        "sentence_coverage": coverage,
        "semantic_class_heuristic_distribution": class_dist,
        "sample_size_per_language": {LANGS[lid]: len(rows) for lid, rows in samples.items()},
        "capability_matrix_pct_of_sample": capability_pct,
        "skip_reasons_top": {
            lang: {
                t: dict(sorted(reasons.items(), key=lambda kv: -kv[1])[:3])
                for t, reasons in types.items()
            }
            for lang, types in skip_reasons.items()
        },
        "exercises_per_sense_headline": headline,
        "latency_throughput": latency,
        "distractor_strategy_comparison": distractor_compare,
    }

    out_path = SANDBOX / "reports" / "zero_llm_measurement.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    examples_path = SANDBOX / "reports" / "zero_llm_sample_exercises.json"
    examples_path.write_text(json.dumps(sample_examples, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
