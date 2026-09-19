"""One-shot measurement run: pulls real senses from db/lab.sqlite, runs all
three variants at concurrency 1/4/12 through lab/harness.py, runs Phase B for
the fat-seed variants, and prints a compact summary. Not a pytest file --
requested as an explicit measurement pass."""
from __future__ import annotations

import sys
import time
from pathlib import Path

_LAB_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_LAB_ROOT))

from lab import db as labdb  # noqa: E402
from lab.harness import run_harness  # noqa: E402
from lab.models import SenseRow  # noqa: E402

from prototypes.fat_seed.variants import (  # noqa: E402
    FatSeedOneCallGenerator, FatSeedTwoCallGenerator, LegacyFanoutGenerator,
)

NOMINAL_LATENCY_MS = 15.0  # small, for fast structural/throughput measurement;
                            # real seconds-per-call applied analytically after.


def load_senses(n_per_lang: int = 8) -> list[SenseRow]:
    conn = labdb.connect()
    out: list[SenseRow] = []
    for lang in (1, 2, 3):
        rows = conn.execute(
            """
            SELECT ws.id, ws.vocab_id, v.language_id, v.lemma, v.part_of_speech,
                   v.frequency_rank, ws.definition, ws.definition_level,
                   ws.pronunciation, ws.example_sentence, ws.sense_rank
            FROM dim_word_senses ws JOIN dim_vocabulary v ON v.id = ws.vocab_id
            WHERE v.language_id = ? AND ws.definition_level = 'standard'
              AND ws.definition IS NOT NULL AND length(ws.definition) > 0
            ORDER BY v.frequency_rank DESC LIMIT ?
            """,
            (lang, n_per_lang),
        ).fetchall()
        for r in rows:
            out.append(SenseRow(
                sense_id=r[0], vocab_id=r[1], language_id=r[2], lemma=r[3],
                part_of_speech=r[4], frequency_rank=r[5], definition=r[6],
                definition_level=r[7], pronunciation=r[8], example_sentence=r[9],
                sense_rank=r[10],
            ))
    conn.close()
    return out


def summarize(label: str, report, generator) -> dict:
    generator.run_phase_b_for_all()
    pa_lat = [pa.latency_ms for pa in generator.phase_a_results.values()]
    pb_lat = [pb.latency_ms for pb in generator.phase_b_results.values()]
    validator_pass = sum(1 for pa in generator.phase_a_results.values() if pa.seed_valid)
    total = len(generator.phase_a_results)
    skip_counts: dict[str, int] = {}
    for pa in generator.phase_a_results.values():
        for sk in pa.skips:
            skip_counts[sk.type_code] = skip_counts.get(sk.type_code, 0) + 1
    return {
        "label": label,
        "n_senses": report.n_senses,
        "concurrency": report.concurrency,
        "throughput_senses_per_min": report.throughput_senses_per_min,
        "total_llm_calls": report.total_llm_calls,
        "total_tokens_in": report.total_tokens_in,
        "total_tokens_out": report.total_tokens_out,
        "total_cost_usd": report.total_cost_usd,
        "total_exercises_produced": report.total_exercises_produced,
        "validation_pass_rate_seed": validator_pass / total if total else 0.0,
        "phase_a_latency_ms_mean": sum(pa_lat) / len(pa_lat) if pa_lat else 0.0,
        "phase_b_latency_ms_mean": sum(pb_lat) / len(pb_lat) if pb_lat else 0.0,
        "calls_per_sense": report.total_llm_calls / max(report.n_senses, 1),
        "skip_counts": skip_counts,
    }


def main() -> None:
    senses = load_senses(8)
    print(f"Loaded {len(senses)} senses across zh/en/ja")

    variant_classes = [
        ("fat_seed_one_call", FatSeedOneCallGenerator),
        ("fat_seed_two_call", FatSeedTwoCallGenerator),
        ("legacy_fanout_control", LegacyFanoutGenerator),
    ]
    results = []
    for concurrency in (1, 4, 12):
        for label, cls in variant_classes:
            gen = cls(synthetic_latency_ms=NOMINAL_LATENCY_MS)
            t0 = time.perf_counter()
            report = run_harness(gen, senses, concurrency=concurrency)
            wall = time.perf_counter() - t0
            summary = summarize(label, report, gen)
            summary["wall_s"] = wall
            results.append(summary)
            print(f"[{label} c={concurrency}] senses={summary['n_senses']} "
                  f"calls/sense={summary['calls_per_sense']:.2f} "
                  f"tokens_in={summary['total_tokens_in']} tokens_out={summary['total_tokens_out']} "
                  f"cost=${summary['total_cost_usd']:.5f} "
                  f"exercises={summary['total_exercises_produced']} "
                  f"seed_valid_rate={summary['validation_pass_rate_seed']:.2f} "
                  f"throughput/min={summary['throughput_senses_per_min']:.1f} "
                  f"phaseA_ms={summary['phase_a_latency_ms_mean']:.2f} "
                  f"phaseB_ms={summary['phase_b_latency_ms_mean']:.2f} "
                  f"errors={report.errors}")
            if summary["skip_counts"]:
                print(f"    skips: {summary['skip_counts']}")

    import json
    out_path = Path(__file__).resolve().parents[2] / "reports" / "fat_seed_measurement.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
