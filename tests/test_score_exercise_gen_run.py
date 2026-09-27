"""Tests for scripts/score_exercise_gen_run.py and scripts/merge_pairwise_verdicts.py
(TASK-807). Uses small synthetic fixtures -- no DB, no network, no LLM calls.

Run: PYTHONPATH=. python -m pytest tests/test_score_exercise_gen_run.py -q
"""

from __future__ import annotations

import importlib
import json
import sys

import pytest

sys.path.insert(0, ".")

score_mod = importlib.import_module("scripts.score_exercise_gen_run")
merge_mod = importlib.import_module("scripts.merge_pairwise_verdicts")


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


def make_reference_entry(sense_id, levels_types, invalid_assets=0, valid_assets=2):
    """`reference_set`-shaped item (asset_type/word_assets/type-keyed exercises)."""
    word_assets = [
        {"asset_type": "prompt1_core", "is_valid": True, "content": {}} for _ in range(valid_assets)
    ] + [{"asset_type": "prompt1_core", "is_valid": False, "content": {}} for _ in range(invalid_assets)]
    exercises = []
    for level, etype, options in levels_types:
        exercises.append(
            {
                "type": etype,
                "level": level,
                "variant": "A",
                "complexity_tier": "T5",
                "payload": {"options": options, "correct_answer": options[-1]} if options else {},
            }
        )
    return {
        "sense_id": sense_id,
        "language": "ja",
        "lemma": f"lemma{sense_id}",
        "difficulty": 5,
        "word_assets": word_assets,
        "exercises": exercises,
    }


def make_run_entry(
    sense_id,
    levels_types,
    language="ja",
    invalid_assets=0,
    valid_assets=2,
    judge_verdicts=None,
    cost_rows=None,
    timings=None,
):
    """`<run_dir>/<sense_id>.json`-shaped item (assets/exercise_type-keyed)."""
    assets = [{"asset_type": "prompt1_core", "is_valid": True} for _ in range(valid_assets)] + [
        {"asset_type": "prompt1_core", "is_valid": False, "validation_errors": ["bad schema"]}
        for _ in range(invalid_assets)
    ]
    exercises = []
    for level, etype, options in levels_types:
        exercises.append(
            {
                "exercise_type": etype,
                "level": level,
                "variant": "A",
                "complexity_tier": "T5",
                "payload": {"options": options, "correct_answer": options[-1]} if options else {},
            }
        )
    return {
        "sense_id": sense_id,
        "language": language,
        "difficulty": 5,
        "assets": assets,
        "exercises": exercises,
        "judge_verdicts": judge_verdicts or [],
        "llm_calls": cost_rows or [],
        "stage_timings": timings or {},
    }


# --------------------------------------------------------------------------
# normalize_* adapters
# --------------------------------------------------------------------------


def test_normalize_reference_entry_maps_type_and_asset_type():
    raw = make_reference_entry(1, [(1, "phonetic_recognition", ["a", "b", "c", "d"])])
    ns = score_mod.normalize_reference_entry(raw)
    assert ns.sense_id == "1"
    assert ns.assets[0].asset_type == "prompt1_core"
    assert ns.exercises[0].exercise_type == "phonetic_recognition"
    assert ns.exercises[0].level == 1


def test_normalize_run_entry_accepts_aliased_keys():
    raw = {
        "sense_id": 42,
        "lang": "zh",  # alias for "language"
        "word_assets": [{"type": "prompt2", "valid": False}],  # aliases: type, valid
        "rendered_exercises": [{"type": "cloze", "level": 2, "payload": {"options": ["x", "y"]}}],
        "render_judges": [{"name": "entailment", "result": "reject", "level": 2}],
        "durations": [{"stage": "p1", "seconds": 1.5}, {"stage": "p1", "seconds": 0.5}],
        "batch_id": "batch-123",
    }
    ns = score_mod.normalize_run_entry(raw, source="test")
    assert ns.language == "zh"
    assert ns.assets[0].asset_type == "prompt2"
    assert ns.assets[0].is_valid is False
    assert ns.exercises[0].exercise_type == "cloze"
    assert ns.judge_verdicts[0].judge == "entailment"
    assert ns.judge_verdicts[0].rejected is True
    assert ns.stage_timings["p1"] == 2.0
    assert ns.generation_batch_id == "batch-123"


def test_normalize_run_entry_missing_sense_id_raises():
    with pytest.raises(score_mod.RunShapeError):
        score_mod.normalize_run_entry({"language": "en"}, source="broken.json")


def test_normalize_run_entry_accepts_real_pilot_shape():
    """`scripts/run_exercise_gen_eval.py`'s ACTUAL on-disk shape (captured from
    a live TASK-808-prep pilot run, data/eval/runs/pilot_ja/35341.json,
    2026-09-26) differs from the module docstring's assumed shape in three
    ways this adapter must handle:

      1. `language_id` (int FK), not `language`/`lang` (string).
      2. `stage_seconds`, not `stage_timings`/`timings`/`durations`.
      3. `judges` is a dict keyed by judge name -> {ran, rejected, kept}
         (from `_summarize_judges()`), not a list of per-verdict dicts.

    Fixture is `tests/fixtures/exercise_gen_pilot_sense_ja.json` -- the real
    file with `exercise_rows` truncated to 3 and long text fields trimmed.
    """
    with open("tests/fixtures/exercise_gen_pilot_sense_ja.json", encoding="utf-8") as f:
        raw = json.load(f)

    ns = score_mod.normalize_run_entry(raw, source="pilot_ja/35341.json")

    assert ns.sense_id == "35341"
    assert ns.language == "ja"  # mapped from language_id=3, not a "language" key
    assert ns.generation_batch_id  # present in the real shape
    assert len(ns.assets) == len(raw["assets"])
    assert len(ns.exercises) == 3
    assert ns.exercises[0].exercise_type  # aliased from exercise_type in exercise_rows

    # stage_seconds -> stage_timings alias.
    assert ns.stage_timings, "stage_seconds should have populated stage_timings"
    assert ns.stage_timings.get("p1_generate") == pytest.approx(raw["stage_seconds"]["p1_generate"])

    # judges dict -> expanded per-verdict NormalizedJudgeVerdict rows, counts preserved.
    real_judges = raw["judges"]
    assert real_judges, "fixture should carry at least one judge summary"
    for judge_name, counts in real_judges.items():
        rows = [v for v in ns.judge_verdicts if v.judge == judge_name]
        assert len(rows) == counts["rejected"] + counts["kept"]
        assert sum(1 for v in rows if v.rejected) == counts["rejected"]
        assert sum(1 for v in rows if not v.rejected) == counts["kept"]

    # Round-trips cleanly through the reject-rate metric too.
    rates = score_mod.compute_judge_reject_rates([ns])
    for judge_name, counts in real_judges.items():
        assert rates[judge_name]["total"] == counts["rejected"] + counts["kept"]
        assert rates[judge_name]["rejected"] == counts["rejected"]


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------


def test_compute_coverage_counts_missing_levels():
    ref = [
        score_mod.normalize_reference_entry(
            make_reference_entry(
                1,
                [
                    (1, "phonetic_recognition", ["a", "b", "c", "d"]),
                    (2, "cloze", ["a", "b"]),
                    (3, "cloze", ["a", "b"]),
                ],
            )
        )
    ]
    cand = [
        score_mod.normalize_run_entry(
            make_run_entry(1, [(1, "phonetic_recognition", ["a", "b", "c", "d"]), (2, "cloze", ["a", "b"])]),
            source="t",
        )
    ]
    cov = score_mod.compute_coverage(cand, ref)
    assert cov["senses_compared"] == 1
    assert cov["expected_pairs_total"] == 3
    assert cov["present_pairs_total"] == 2
    assert cov["missing_levels_count"] == 1
    assert cov["missing_levels"] == [3]
    assert round(cov["coverage_pct"], 2) == round(100 * 2 / 3, 2)


def test_compute_coverage_empty_common_senses():
    ref = [score_mod.normalize_reference_entry(make_reference_entry(1, [(1, "cloze", ["a", "b"])]))]
    cand = [score_mod.normalize_run_entry(make_run_entry(2, [(1, "cloze", ["a", "b"])]), source="t")]
    cov = score_mod.compute_coverage(cand, ref)
    assert cov["senses_compared"] == 0
    assert cov["coverage_pct"] is None


def test_compute_invalid_asset_rate():
    senses = [
        score_mod.normalize_run_entry(
            make_run_entry(1, [], valid_assets=3, invalid_assets=1), source="t"
        ),
        score_mod.normalize_run_entry(
            make_run_entry(2, [], valid_assets=1, invalid_assets=1), source="t"
        ),
    ]
    rate = score_mod.compute_invalid_asset_rate(senses)
    assert rate["total_assets"] == 6
    assert rate["invalid_assets"] == 2
    assert round(rate["invalid_rate_pct"], 2) == round(100 * 2 / 6, 2)


def test_compute_judge_reject_rates():
    senses = [
        score_mod.normalize_run_entry(
            make_run_entry(
                1,
                [],
                judge_verdicts=[
                    {"judge": "entailment", "verdict": "reject"},
                    {"judge": "entailment", "verdict": "accept"},
                    {"judge": "distractor", "verdict": "reject"},
                ],
            ),
            source="t",
        )
    ]
    rates = score_mod.compute_judge_reject_rates(senses)
    assert rates["entailment"]["total"] == 2
    assert rates["entailment"]["rejected"] == 1
    assert rates["entailment"]["reject_rate_pct"] == 50.0
    assert rates["distractor"]["reject_rate_pct"] == 100.0


def test_compute_l1_drop_rate_flags_under_three_distractors():
    senses = [
        score_mod.normalize_run_entry(
            make_run_entry(
                1,
                [
                    (1, "phonetic_recognition", ["ok", "d1", "d2", "d3"]),  # 3 distractors: kept
                    (1, "phonetic_recognition", ["ok", "d1"]),  # 1 distractor: dropped
                    (1, "cloze", ["irrelevant"]),  # not L1, ignored
                ],
            ),
            source="t",
        )
    ]
    result = score_mod.compute_l1_drop_rate(senses)
    assert result["l1_variants"] == 2
    assert result["dropped"] == 1
    assert result["drop_rate_pct"] == 50.0


def test_compute_cost_metrics_mean_p50_p90_and_retries():
    rows = [
        {"sense_id": "1", "cost_usd": 0.01, "call_role": "primary", "task_name": "p1"},
        {"sense_id": "1", "cost_usd": 0.005, "call_role": "retry", "task_name": "p1"},
        {"sense_id": "2", "cost_usd": 0.02, "call_role": "primary", "task_name": "p2"},
    ]
    metrics = score_mod.compute_cost_metrics(rows)
    assert metrics["senses_with_calls"] == 2
    assert metrics["total_calls"] == 3
    assert round(metrics["total_cost_usd"], 4) == 0.035
    assert metrics["retries_per_sense_mean"] == pytest.approx(0.5)
    assert round(metrics["cost_per_sense_mean"], 4) == round(0.035 / 2, 4)
    assert metrics["per_stage_cost_share_pct"]["p2"] == round(100 * 0.02 / 0.035, 2)


def test_compute_cost_metrics_handles_no_rows():
    metrics = score_mod.compute_cost_metrics([])
    assert metrics["cost_per_sense_mean"] is None
    assert metrics["total_cost_usd"] is None


def test_compute_wall_clock():
    senses = [
        score_mod.normalize_run_entry(make_run_entry(1, [], timings={"p1": 2.0, "p2": 1.0}), source="t"),
        score_mod.normalize_run_entry(make_run_entry(2, [], timings={"p1": 4.0}), source="t"),
    ]
    wc = score_mod.compute_wall_clock(senses)
    assert wc["senses_with_timings"] == 2
    assert wc["wall_clock_per_sense_mean_s"] == 3.5


# --------------------------------------------------------------------------
# Pairwise packs: blind/unblind round trip
# --------------------------------------------------------------------------


def test_build_pairwise_packs_and_merge_round_trip(tmp_path):
    ref = [
        score_mod.normalize_reference_entry(
            make_reference_entry(str(i), [(1, "cloze", ["a", "b"]), (2, "cloze", ["c", "d"])])
        )
        for i in range(1, 4)
    ]
    cand = [
        score_mod.normalize_run_entry(
            make_run_entry(str(i), [(1, "cloze", ["a", "b"]), (2, "cloze", ["c", "d"])]), source="t"
        )
        for i in range(1, 4)
    ]

    out_dir = str(tmp_path / "run")
    key_doc = score_mod.build_pairwise_packs(cand, ref, out_dir, pack_size=10, seed=7)

    assert len(key_doc["entries"]) == 6  # 3 senses x 2 levels
    pack_files = sorted((tmp_path / "run" / "pairwise_packs").glob("pack_*.md"))
    assert len(pack_files) == 1
    assert "Pack A" in pack_files[0].read_text(encoding="utf-8")

    # Build verdicts that always prefer the *candidate* side, using the key to
    # know which of A/B that is for each pair -- this is what a reviewer's
    # blind judgment collapses to when the candidate is genuinely better.
    verdicts = []
    for entry in key_doc["entries"]:
        verdicts.append(
            {
                "sense_id": entry["sense_id"],
                "level": entry["level"],
                "preferred": entry["candidate_side"],
                "major_defects_A": [],
                "major_defects_B": ["also-correct distractor"] if entry["candidate_side"] == "A" else [],
                "notes": "",
            }
        )
    verdicts_path = tmp_path / "verdicts.jsonl"
    verdicts_path.write_text("\n".join(json.dumps(v) for v in verdicts), encoding="utf-8")

    result = merge_mod.unblind_and_aggregate(key_doc, verdicts)
    assert result["candidate_wins"] == 6
    assert result["reference_wins"] == 0
    assert result["win_rate_pct"] == 100.0
    assert result["loss_rate_pct"] == 0.0
    assert not result["unmatched_verdicts"]
    assert not result["missing_verdicts"]

    # And via the file-based loader/CLI path too.
    key_path = tmp_path / "run" / "pairwise_key.json"
    loaded_key = merge_mod.load_key(str(key_path))
    loaded_verdicts = merge_mod.load_verdict_lines([str(verdicts_path)])
    result2 = merge_mod.unblind_and_aggregate(loaded_key, loaded_verdicts)
    assert result2 == result


def test_merge_pairwise_verdicts_flags_unmatched_and_missing():
    key = {
        "entries": [
            {"sense_id": "1", "level": 1, "candidate_side": "A"},
            {"sense_id": "1", "level": 2, "candidate_side": "B"},
        ]
    }
    verdicts = [
        {"sense_id": "1", "level": 1, "preferred": "A"},
        {"sense_id": "999", "level": 1, "preferred": "tie"},  # unmatched
    ]
    result = merge_mod.unblind_and_aggregate(key, verdicts)
    assert result["candidate_wins"] == 1
    assert len(result["unmatched_verdicts"]) == 1
    assert result["missing_verdicts"] == [{"sense_id": "1", "level": 2}]


def test_merge_pairwise_verdicts_rejects_bad_preferred_value():
    key = {"entries": [{"sense_id": "1", "level": 1, "candidate_side": "A"}]}
    verdicts = [{"sense_id": "1", "level": 1, "preferred": "C"}]
    with pytest.raises(merge_mod.VerdictShapeError):
        merge_mod.unblind_and_aggregate(key, verdicts)


# --------------------------------------------------------------------------
# Non-inferiority decision
# --------------------------------------------------------------------------


def _metrics(invalid_pct, judge_reject_pct=None):
    m = {"invalid_asset_rate": {"invalid_rate_pct": invalid_pct}, "judge_reject_rates": {}}
    if judge_reject_pct is not None:
        m["judge_reject_rates"] = {"j": {"reject_rate_pct": judge_reject_pct}}
    return m


def test_decide_non_inferiority_all_pass():
    thresholds = score_mod.Thresholds()
    coverage = {"coverage_pct": 100.0}
    cand = _metrics(invalid_pct=2.0, judge_reject_pct=5.0)
    ref = _metrics(invalid_pct=1.0, judge_reject_pct=4.0)
    pairwise = {
        "major_defect_rate_candidate": 5.0,
        "major_defect_rate_reference": 4.0,
        "win_rate_pct": 40.0,
        "loss_rate_pct": 30.0,
    }
    decision = score_mod.decide_non_inferiority(
        cand, ref, pairwise_summary=pairwise, thresholds=thresholds, coverage=coverage
    )
    assert decision["overall"] == "PASS"
    assert decision["failed_criteria"] == []


def test_decide_non_inferiority_fails_named_criteria_only():
    thresholds = score_mod.Thresholds()
    coverage = {"coverage_pct": 50.0}  # fails (c)
    cand = _metrics(invalid_pct=10.0, judge_reject_pct=5.0)  # fails (d): 10 > 1+3
    ref = _metrics(invalid_pct=1.0, judge_reject_pct=4.0)
    pairwise = {
        "major_defect_rate_candidate": 4.5,  # passes (a): 4.5 <= 4+2
        "major_defect_rate_reference": 4.0,
        "win_rate_pct": 10.0,
        "loss_rate_pct": 30.0,  # fails (b): 30-10=20 > 10
    }
    decision = score_mod.decide_non_inferiority(
        cand, ref, pairwise_summary=pairwise, thresholds=thresholds, coverage=coverage
    )
    assert decision["overall"] == "FAIL"
    assert set(decision["failed_criteria"]) == {"b_pairwise_loss_minus_win", "c_coverage", "d_invalid_asset_rate"}
    assert decision["criteria"]["a_major_defect_rate"]["status"] == "PASS"


def test_decide_non_inferiority_skips_criteria_without_data():
    thresholds = score_mod.Thresholds()
    coverage = {"coverage_pct": None}
    cand = _metrics(invalid_pct=None)
    ref = _metrics(invalid_pct=None)
    decision = score_mod.decide_non_inferiority(
        cand, ref, pairwise_summary=None, thresholds=thresholds, coverage=coverage
    )
    assert decision["overall"] == "PASS"  # no FAILs, only SKIPs
    assert set(decision["skipped_criteria"]) == {
        "a_major_defect_rate",
        "b_pairwise_loss_minus_win",
        "c_coverage",
        "d_invalid_asset_rate",
    }


def test_thresholds_are_cli_overridable():
    args = score_mod.parse_args(
        [
            "--candidate",
            "c",
            "--reference",
            "r",
            "--lang",
            "ja",
            "--major-defect-margin-pp",
            "5",
            "--coverage-min-pct",
            "80",
        ]
    )
    assert args.major_defect_margin_pp == 5.0
    assert args.coverage_min_pct == 80.0
    assert args.pairwise_loss_margin_pp == score_mod.Thresholds.pairwise_loss_margin_pp


# --------------------------------------------------------------------------
# load_reference: frozen JSON vs run-dir
# --------------------------------------------------------------------------


def test_load_reference_warns_when_language_has_only_top_up_candidates(tmp_path):
    doc = {
        "reference_set": [make_reference_entry(1, [(1, "cloze", ["a", "b"])])],  # ja only
        "top_up_candidates": [{"sense_id": 5, "language": "zh", "lemma": "x"}],
    }
    ref_path = tmp_path / "reference.json"
    ref_path.write_text(json.dumps(doc), encoding="utf-8")

    senses, meta = score_mod.load_reference(str(ref_path), "zh")
    assert senses == []
    assert "warning" in meta

    senses_ja, meta_ja = score_mod.load_reference(str(ref_path), "ja")
    assert len(senses_ja) == 1
    assert "warning" not in meta_ja


def test_load_reference_from_run_dir(tmp_path):
    run_dir = tmp_path / "baseline"
    run_dir.mkdir()
    entry = make_run_entry(1, [(1, "cloze", ["a", "b"])], language="zh")
    (run_dir / "1.json").write_text(json.dumps(entry), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps({"generation_batch_id": "b1"}), encoding="utf-8")

    senses, meta = score_mod.load_reference(str(run_dir), "zh")
    assert len(senses) == 1
    assert meta["kind"] == "run_dir"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
