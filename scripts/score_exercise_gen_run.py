"""Quality scoring protocol for exercise-generation cost changes (TASK-807).

Scores a candidate exercise-generation run against a reference (either the frozen
ja benchmark in `data/eval/exercise_gen_reference_set_2026-09.json`, or -- for
zh/en, which that file only carries `top_up_candidates` for -- a baseline run
directory produced by `scripts/run_exercise_gen_eval.py` on the *current*,
unmodified pipeline) and decides whether the candidate is non-inferior.

    python scripts/score_exercise_gen_run.py \
        --candidate data/eval/runs/qwen-bundle-v1 \
        --reference data/eval/exercise_gen_reference_set_2026-09.json \
        --lang ja

    python scripts/score_exercise_gen_run.py \
        --candidate data/eval/runs/qwen-zh-v1 \
        --reference data/eval/runs/baseline-zh \
        --lang zh

Writes `<candidate>/score.json`, `<candidate>/score_report.md`, and (unless
`--skip-pairwise-packs`) `<candidate>/pairwise_packs/pack_NN.md` plus the
unblinding key `<candidate>/pairwise_key.json`. Pairwise packs are judged out of
band (fresh-context Claude subagents, or a human) and folded back in with
`scripts/merge_pairwise_verdicts.py`; pass the resulting file via
`--pairwise-results` (or drop it at `<candidate>/pairwise_results.json`, which is
auto-detected) to make the pairwise non-inferiority criterion count toward the
PASS/FAIL decision. Without it, that criterion is reported as SKIPPED, not FAIL.

== Adapter contract (read this before wiring a new run producer) ==

`scripts/run_exercise_gen_eval.py` is being built concurrently by another agent
and its exact on-disk shape was not available while this script was written.
Every place this script reads a candidate/baseline-run sense file goes through
`normalize_run_entry()`, a single function that tries several plausible key
names for each field and raises a clear `RunShapeError` naming the sense file
and the field it could not find, rather than silently defaulting.

Assumed per-sense JSON shape at `<run_dir>/<sense_id>.json` (fields marked
"or equivalent" are looked up under several aliases -- see
`_first_present()` calls in `normalize_run_entry`):

    {
      "sense_id": <int or str>,
      "language": "en" | "zh" | "ja",
      "difficulty": <int, optional>,
      "generation_batch_id": "<uuid, optional>",
      "assets" | "word_assets": [
        {"asset_type": str, "is_valid": bool,
         "validation_errors" | "errors": [str, ...] (optional), ...}
      ],
      "exercises" | "rendered_exercises": [
        {"type" | "exercise_type": str, "level": int,
         "variant": "A" | "B" (optional), "complexity_tier": str (optional),
         "payload": {...}}
      ],
      "judge_verdicts" | "render_judges" | "judges": [
        {"judge" | "judge_name" | "name": str,
         "verdict" | "result": "pass" | "reject" | "accept" | ... ,
         "level": int (optional), "exercise_type" | "type": str (optional)}
      ],
      "stage_timings" | "timings" | "durations": {"<stage>": <seconds>}
                                                    or [{"stage": str, "seconds": float}],
      "llm_calls": [  # optional inline cost rows, same columns as the DB table
        {"cost_usd": float, "call_role": str, "task_name": str,
         "prompt_tokens": int, "completion_tokens": int, ...}
      ]
    }

`summary.json` at the run root is read opportunistically for a `generation_batch_id`
/ `generation_batch_ids` list to key an external `llm_calls` cost export, and for
overall wall-clock if per-sense timings are absent. It is never required.

If the real script's shape differs, only `normalize_run_entry()` (and, for cost,
`load_cost_rows()`) should need editing.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


# run_exercise_gen_eval.py's real per-sense JSON carries `language_id` (an
# int FK into dim_languages), not a `language` string -- see LANG_CODE_TO_ID
# in that script. Mirrored here (rather than imported) to keep this scorer
# importable/runnable standalone with no DB/pipeline dependency.
_LANG_ID_TO_CODE: dict[int, str] = {1: "zh", 2: "en", 3: "ja"}


class RunShapeError(ValueError):
    """Raised when a sense record does not match any known shape for a field."""


# --------------------------------------------------------------------------
# Small generic helpers
# --------------------------------------------------------------------------


def _first_present(d: dict, keys: Iterable[str], default: Any = "__MISSING__") -> Any:
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] is not None:
            return d[k]
    if default == "__MISSING__":
        raise RunShapeError(f"none of {list(keys)} present in {list(d.keys()) if isinstance(d, dict) else d!r}")
    return default


def _percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile, no interpolation. pct in [0, 100]."""
    if not values:
        return None
    s = sorted(values)
    k = max(0, min(len(s) - 1, math.ceil(pct / 100.0 * len(s)) - 1))
    return s[k]


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _pct(n: int, d: int) -> float | None:
    if d == 0:
        return None
    return 100.0 * n / d


# --------------------------------------------------------------------------
# Normalized sense record
# --------------------------------------------------------------------------


@dataclass
class NormalizedAsset:
    asset_type: str
    is_valid: bool | None
    validation_errors: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


@dataclass
class NormalizedExercise:
    exercise_type: str
    level: int | None
    variant: str | None
    complexity_tier: str | None
    payload: dict = field(default_factory=dict)


@dataclass
class NormalizedJudgeVerdict:
    judge: str
    rejected: bool
    level: int | None = None
    exercise_type: str | None = None


@dataclass
class NormalizedSense:
    sense_id: str
    language: str
    lemma: str | None
    difficulty: int | None
    assets: list[NormalizedAsset]
    exercises: list[NormalizedExercise]
    judge_verdicts: list[NormalizedJudgeVerdict]
    stage_timings: dict[str, float]
    generation_batch_id: str | None
    llm_calls: list[dict]
    # Authoritative started_at->finished_at total, when the run records one
    # (see `wall_clock_total_s` alias handling in `normalize_run_entry`).
    # `run_exercise_gen_eval.py`'s real `stage_seconds` dict only covers a
    # subset of pipeline stages (fetch_corpus/p1_generate/p1_repair/tier_gate/
    # p1_judge/fan_out as of the 2026-09-26 baseline) and undercounts total
    # wall clock by roughly half; `compute_wall_clock` prefers this field.
    wall_clock_total_s: float | None = None


_REJECT_VERDICTS = {"reject", "rejected", "fail", "failed", "flag", "flagged", "no"}
_ACCEPT_VERDICTS = {"accept", "accepted", "pass", "passed", "ok", "yes"}


def _verdict_is_reject(v: Any) -> bool:
    if isinstance(v, bool):
        return not v
    s = str(v).strip().lower()
    if s in _REJECT_VERDICTS:
        return True
    if s in _ACCEPT_VERDICTS:
        return False
    # Unknown string verdict (e.g. a Likert band) -- treat anything that isn't
    # an explicit accept as a soft reject signal, but this is a shape gap the
    # caller should tighten once the real judge output format is known.
    return False


def normalize_reference_entry(raw: dict) -> NormalizedSense:
    """Adapts an item from `exercise_gen_reference_set_2026-09.json`'s
    `reference_set` list (frozen ja benchmark shape: `word_assets` use
    `asset_type`, exercises use `type`, no judge_verdicts/timings/cost)."""
    assets = [
        NormalizedAsset(
            asset_type=a.get("asset_type", "unknown"),
            is_valid=a.get("is_valid"),
            validation_errors=list(a.get("validation_errors") or a.get("errors") or []),
            raw=a,
        )
        for a in raw.get("word_assets", []) or []
    ]
    exercises = [
        NormalizedExercise(
            exercise_type=e.get("type") or e.get("exercise_type") or "unknown",
            level=e.get("level"),
            variant=e.get("variant"),
            complexity_tier=e.get("complexity_tier"),
            payload=e.get("payload", {}) or {},
        )
        for e in raw.get("exercises", []) or []
    ]
    return NormalizedSense(
        sense_id=str(raw["sense_id"]),
        language=raw.get("language", "unknown"),
        lemma=raw.get("lemma"),
        difficulty=raw.get("difficulty"),
        assets=assets,
        exercises=exercises,
        judge_verdicts=[],
        stage_timings={},
        generation_batch_id=None,
        llm_calls=[],
    )


def normalize_run_entry(raw: dict, *, source: str = "<unknown file>") -> NormalizedSense:
    """Defensive adapter for one `<run_dir>/<sense_id>.json` produced by
    `scripts/run_exercise_gen_eval.py` (candidate run OR a zh/en baseline run
    used as the reference). See the module docstring's "Adapter contract" for
    the assumed shape and the field aliases tried below.

    Raises `RunShapeError` naming `source` and the missing field, rather than
    guessing, for the one field with no reasonable default (`sense_id`).
    """
    try:
        sense_id = _first_present(raw, ["sense_id", "id"])
    except RunShapeError as e:
        raise RunShapeError(f"{source}: {e}") from e

    language = (
        raw.get("language")
        or raw.get("lang")
        or _LANG_ID_TO_CODE.get(raw.get("language_id"))
        or "unknown"
    )
    difficulty = raw.get("difficulty")

    raw_assets = _first_present(raw, ["assets", "word_assets", "generated_assets"], default=[])
    assets = []
    for a in raw_assets or []:
        assets.append(
            NormalizedAsset(
                asset_type=a.get("asset_type") or a.get("type") or "unknown",
                is_valid=a.get("is_valid") if "is_valid" in a else a.get("valid"),
                validation_errors=list(
                    a.get("validation_errors") or a.get("errors") or a.get("validation_error") or []
                    if not isinstance(a.get("validation_errors") or a.get("errors"), str)
                    else [a.get("validation_errors") or a.get("errors")]
                ),
                raw=a,
            )
        )

    raw_exercises = _first_present(
        raw, ["exercises", "rendered_exercises", "exercise_rows"], default=[]
    )
    exercises = []
    for e in raw_exercises or []:
        e_tags = e.get("tags") if isinstance(e.get("tags"), dict) else {}
        exercises.append(
            NormalizedExercise(
                exercise_type=e.get("exercise_type") or e.get("type") or "unknown",
                # `run_exercise_gen_eval.py`'s real `exercise_rows` shape (the DB row
                # shape, confirmed against data/eval/runs/baseline_{ja,en}/*.json)
                # carries the level as a top-level `ladder_level` column, not
                # `level`, and puts `variant` inside the `tags` jsonb blob rather
                # than at the row's top level. The rendered content lives under
                # `content`, not `payload`. The frozen reference JSON (built by
                # hand, see normalize_reference_entry) uses `level`/`variant`/
                # `payload` directly -- both shapes are tried here so coverage,
                # l1-drop-rate, and pairwise-pack rendering all see real data
                # instead of silently defaulting every candidate exercise to
                # level=None (which zeroed out coverage against the reference).
                level=e.get("level") if e.get("level") is not None else (e.get("ladder_level") or e_tags.get("ladder_level")),
                variant=e.get("variant") or e_tags.get("variant"),
                complexity_tier=e.get("complexity_tier") or e.get("tier") or e_tags.get("complexity_tier"),
                payload=e.get("payload") or e.get("content") or {},
            )
        )

    raw_judges = _first_present(
        raw, ["judge_verdicts", "render_judges", "judges", "judge_results"], default=[]
    )
    judge_verdicts = []
    if isinstance(raw_judges, dict):
        # `run_exercise_gen_eval.py`'s real shape (`_summarize_judges()`):
        # {"<judge_name>": {"ran": N, "rejected": R, "kept": K}, ...} -- an
        # aggregate per judge, not one row per verdict. Expand into R
        # synthetic rejected verdicts + K synthetic kept verdicts so
        # `compute_judge_reject_rates()` (which just counts
        # `NormalizedJudgeVerdict` rows) sees the same totals without needing
        # its own code path for this shape.
        for judge_name, counts in raw_judges.items():
            if not isinstance(counts, dict):
                continue
            rejected_n = int(counts.get("rejected") or 0)
            kept_n = int(counts.get("kept") or 0)
            for _ in range(rejected_n):
                judge_verdicts.append(NormalizedJudgeVerdict(judge=judge_name, rejected=True))
            for _ in range(kept_n):
                judge_verdicts.append(NormalizedJudgeVerdict(judge=judge_name, rejected=False))
    else:
        for j in raw_judges or []:
            judge_name = j.get("judge") or j.get("judge_name") or j.get("name") or "unknown_judge"
            verdict = j.get("verdict") if "verdict" in j else j.get("result")
            judge_verdicts.append(
                NormalizedJudgeVerdict(
                    judge=judge_name,
                    rejected=_verdict_is_reject(verdict),
                    level=j.get("level"),
                    exercise_type=j.get("exercise_type") or j.get("type"),
                )
            )

    raw_timings = _first_present(
        raw, ["stage_timings", "timings", "durations", "stage_seconds"], default={}
    )
    stage_timings: dict[str, float] = {}
    if isinstance(raw_timings, dict):
        for k, v in raw_timings.items():
            try:
                stage_timings[k] = float(v)
            except (TypeError, ValueError):
                continue
    elif isinstance(raw_timings, list):
        for item in raw_timings:
            stage = item.get("stage") or item.get("name")
            secs = item.get("seconds") or item.get("duration_s") or item.get("ms")
            if stage is None or secs is None:
                continue
            try:
                stage_timings[stage] = stage_timings.get(stage, 0.0) + float(secs)
            except (TypeError, ValueError):
                continue

    generation_batch_id = raw.get("generation_batch_id") or raw.get("batch_id")
    llm_calls = list(raw.get("llm_calls") or [])

    wall_clock_total = raw.get("wall_clock_s")
    if wall_clock_total is None:
        wall_clock_total = raw.get("wall_clock_seconds") or raw.get("total_wall_clock_s")
    try:
        wall_clock_total = float(wall_clock_total) if wall_clock_total is not None else None
    except (TypeError, ValueError):
        wall_clock_total = None

    return NormalizedSense(
        sense_id=str(sense_id),
        language=language,
        lemma=raw.get("lemma"),
        difficulty=difficulty,
        assets=assets,
        exercises=exercises,
        judge_verdicts=judge_verdicts,
        stage_timings=stage_timings,
        generation_batch_id=generation_batch_id,
        llm_calls=llm_calls,
        wall_clock_total_s=wall_clock_total,
    )


# --------------------------------------------------------------------------
# Loaders
# --------------------------------------------------------------------------


def load_reference(path: str, lang: str) -> tuple[list[NormalizedSense], dict]:
    """Loads the reference side. `path` is either:
      - the frozen reference JSON (has a top-level `reference_set` key) -- used
        as-is for `lang` if that language has entries there; if it only has
        `top_up_candidates` for `lang` (true for zh/en as of 2026-09-24, since
        those senses have no rendered exercises yet), this returns an empty
        list and the caller should be pointed at a baseline run instead; or
      - a run directory (baseline run of the current, unmodified pipeline),
        loaded exactly like a candidate run.
    Returns (senses, meta) where meta notes which path was taken.
    """
    if os.path.isdir(path):
        senses, summary = load_candidate_run(path, lang=lang)
        return senses, {"kind": "run_dir", "path": path, "summary": summary}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "reference_set" in data:
        senses = [
            normalize_reference_entry(item)
            for item in data.get("reference_set", [])
            if item.get("language") == lang
        ]
        top_up = [item for item in data.get("top_up_candidates", []) if item.get("language") == lang]
        meta = {
            "kind": "frozen_reference_json",
            "path": path,
            "reference_set_count": len(senses),
            "top_up_candidates_count": len(top_up),
        }
        if not senses and top_up:
            meta["warning"] = (
                f"lang={lang!r} has 0 benchmark senses in reference_set (only "
                f"{len(top_up)} unauthored top_up_candidates). Per ADR-028/TASK-806, "
                f"use a baseline run directory as --reference for this language instead."
            )
        return senses, meta

    # Fallback: treat the file as a single combined run export (list of
    # per-sense dicts, or {"senses": [...]}) using the run-shape adapter.
    items = data.get("senses") if isinstance(data, dict) else data
    senses = [
        normalize_run_entry(item, source=f"{path}#{i}")
        for i, item in enumerate(items or [])
        if item.get("language", lang) == lang
    ]
    return senses, {"kind": "run_export_json", "path": path}


def load_candidate_run(run_dir: str, lang: str | None = None) -> tuple[list[NormalizedSense], dict]:
    """Loads every `<run_dir>/<sense_id>.json` plus `summary.json` (if present)."""
    summary = {}
    summary_path = os.path.join(run_dir, "summary.json")
    if os.path.isfile(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)

    # Filenames this script itself writes into a run/candidate directory
    # (`--out-dir` defaults to `--candidate`). Without excluding them, scoring
    # the same directory twice -- or using a scored run as a `--reference` for
    # a later candidate, per the zh/en self-reference use case -- picks up the
    # scorer's own prior output as if it were a per-sense record and fails
    # with a confusing RunShapeError on `pairwise_key.json` (no `sense_id`).
    _OWN_OUTPUT_FILES = {"summary.json", "score.json", "pairwise_key.json", "pairwise_results.json"}

    senses: list[NormalizedSense] = []
    for name in sorted(os.listdir(run_dir)):
        if not name.endswith(".json") or name in _OWN_OUTPUT_FILES:
            continue
        full = os.path.join(run_dir, name)
        with open(full, "r", encoding="utf-8") as f:
            raw = json.load(f)
        ns = normalize_run_entry(raw, source=full)
        if lang is not None and ns.language not in (lang, "unknown"):
            continue
        senses.append(ns)
    return senses, summary


def load_cost_rows(
    *,
    senses: list[NormalizedSense] | None = None,
    llm_calls_export: str | None = None,
) -> list[dict]:
    """Cost rows are `llm_calls`-shaped dicts (cost_usd, prompt_tokens,
    completion_tokens, cached_tokens, reasoning_tokens, call_role, task_name,
    model, sense_id). Preference order, all offline/no-DB-required:

      1. Rows inlined per-sense at `NormalizedSense.llm_calls` (what
         `run_exercise_gen_eval.py` is expected to capture directly).
      2. An external JSON export at `--llm-calls-export` (a list of the same
         row shape, e.g. a one-off dump of `llm_calls WHERE generation_batch_id
         = ANY(...)` for when the run script does not inline cost rows).

    This function makes no network or DB calls itself -- TASK-807 must not make
    paid API calls, and a live DB credential is not assumed to be available
    wherever this script runs. If a live pull is wanted, dump `llm_calls` rows
    to JSON first and pass `--llm-calls-export`.
    """
    rows: list[dict] = []
    if senses:
        for s in senses:
            for r in s.llm_calls:
                row = dict(r)
                row.setdefault("sense_id", s.sense_id)
                rows.append(row)
    if llm_calls_export and os.path.isfile(llm_calls_export):
        with open(llm_calls_export, "r", encoding="utf-8") as f:
            exported = json.load(f)
        if isinstance(exported, dict):
            exported = exported.get("rows") or exported.get("llm_calls") or []
        rows.extend(exported)
    return rows


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------


def compute_coverage(candidate: list[NormalizedSense], reference: list[NormalizedSense]) -> dict:
    """Exercise rows per sense by (level, type) vs reference; missing-levels count.

    "Coverage" is measured per language over the (level, exercise_type) pairs
    that appear anywhere in the reference set: for each such pair, what fraction
    of reference senses that have it does the candidate also have it for
    (matched by sense_id)? Senses present only in one side are ignored for the
    per-pair rate but counted in `senses_missing_from_candidate`.
    """
    ref_by_id = {s.sense_id: s for s in reference}
    cand_by_id = {s.sense_id: s for s in candidate}
    common_ids = sorted(set(ref_by_id) & set(cand_by_id))

    ref_pairs_by_sense: dict[str, set[tuple]] = {}
    for sid in common_ids:
        ref_pairs_by_sense[sid] = {(e.level, e.exercise_type) for e in ref_by_id[sid].exercises}

    all_pairs: set[tuple] = set()
    for pairs in ref_pairs_by_sense.values():
        all_pairs |= pairs

    total_expected = 0
    total_present = 0
    missing_levels: set[int] = set()
    per_sense_missing: dict[str, list] = {}
    for sid in common_ids:
        expected = ref_pairs_by_sense[sid]
        got = {(e.level, e.exercise_type) for e in cand_by_id[sid].exercises}
        missing = expected - got
        total_expected += len(expected)
        total_present += len(expected & got)
        if missing:
            per_sense_missing[sid] = sorted(missing)
            for level, _etype in missing:
                if level is not None:
                    missing_levels.add(level)

    coverage_pct = _pct(total_present, total_expected)
    return {
        "senses_compared": len(common_ids),
        "senses_missing_from_candidate": sorted(set(ref_by_id) - set(cand_by_id)),
        "reference_level_type_pairs": len(all_pairs),
        "expected_pairs_total": total_expected,
        "present_pairs_total": total_present,
        "coverage_pct": coverage_pct,
        "missing_levels_count": len(missing_levels),
        "missing_levels": sorted(missing_levels),
        "per_sense_missing": per_sense_missing,
    }


def compute_invalid_asset_rate(senses: list[NormalizedSense]) -> dict:
    total = 0
    invalid = 0
    by_type: dict[str, dict] = defaultdict(lambda: {"total": 0, "invalid": 0})
    for s in senses:
        for a in s.assets:
            if a.is_valid is None:
                continue  # unknown validity is excluded from the rate, not counted invalid
            total += 1
            by_type[a.asset_type]["total"] += 1
            if not a.is_valid:
                invalid += 1
                by_type[a.asset_type]["invalid"] += 1
    return {
        "total_assets": total,
        "invalid_assets": invalid,
        "invalid_rate_pct": _pct(invalid, total),
        "by_asset_type": {
            k: {**v, "invalid_rate_pct": _pct(v["invalid"], v["total"])} for k, v in by_type.items()
        },
    }


def compute_judge_reject_rates(senses: list[NormalizedSense]) -> dict:
    by_judge: dict[str, dict] = defaultdict(lambda: {"total": 0, "rejected": 0})
    for s in senses:
        for v in s.judge_verdicts:
            by_judge[v.judge]["total"] += 1
            if v.rejected:
                by_judge[v.judge]["rejected"] += 1
    return {
        judge: {**d, "reject_rate_pct": _pct(d["rejected"], d["total"])} for judge, d in by_judge.items()
    }


def compute_l1_drop_rate(senses: list[NormalizedSense], *, min_surviving_distractors: int = 3) -> dict:
    """L1 (`phonetic_recognition`) is all-or-nothing: a variant is dropped if
    fewer than `min_surviving_distractors` distractors survive. Post-judge
    survivor counts are not reliably present in every run shape, so this
    counts distractors as they appear in the rendered `payload.options` (i.e.
    after whatever filtering already happened upstream) -- `len(options) - 1`
    for the correct answer. This under-counts drops if the run shape instead
    reports a pre-filter option list; callers should sanity-check this metric
    against `run_exercise_gen_eval.py`'s actual survivor semantics once known.
    """
    total_variants = 0
    dropped = 0
    for s in senses:
        for e in s.exercises:
            if e.exercise_type != "phonetic_recognition":
                continue
            options = e.payload.get("options") if isinstance(e.payload, dict) else None
            if not isinstance(options, list):
                continue
            total_variants += 1
            distractor_count = max(0, len(options) - 1)
            if distractor_count < min_surviving_distractors:
                dropped += 1
    return {
        "l1_variants": total_variants,
        "dropped": dropped,
        "drop_rate_pct": _pct(dropped, total_variants),
        "min_surviving_distractors": min_surviving_distractors,
    }


def compute_cost_metrics(rows: list[dict]) -> dict:
    """Cost/sense (mean, p50, p90), per-stage cost share, retries/sense."""
    per_sense_cost: dict[str, float] = defaultdict(float)
    per_sense_calls: dict[str, int] = defaultdict(int)
    per_sense_retries: dict[str, int] = defaultdict(int)
    stage_cost: dict[str, float] = defaultdict(float)
    total_cost = 0.0
    priced_rows = 0

    for r in rows:
        sid = str(r.get("sense_id", "unknown"))
        cost = r.get("cost_usd")
        role = r.get("call_role") or "primary"
        stage = r.get("task_name") or r.get("pipeline") or "unknown"
        per_sense_calls[sid] += 1
        if role != "primary":
            per_sense_retries[sid] += 1
        if cost is not None:
            try:
                cost = float(cost)
            except (TypeError, ValueError):
                cost = None
        if cost is not None:
            per_sense_cost[sid] += cost
            stage_cost[stage] += cost
            total_cost += cost
            priced_rows += 1

    sense_ids = set(per_sense_calls) | set(per_sense_cost)
    costs = [per_sense_cost.get(sid, 0.0) for sid in sense_ids] if sense_ids else []
    retries = [per_sense_retries.get(sid, 0) for sid in sense_ids] if sense_ids else []

    return {
        "senses_with_calls": len(sense_ids),
        "total_calls": len(rows),
        "priced_calls": priced_rows,
        "total_cost_usd": round(total_cost, 6) if rows else None,
        "cost_per_sense_mean": round(_mean(costs), 6) if costs else None,
        "cost_per_sense_p50": round(_percentile(costs, 50), 6) if costs else None,
        "cost_per_sense_p90": round(_percentile(costs, 90), 6) if costs else None,
        "retries_per_sense_mean": round(_mean([float(x) for x in retries]), 4) if retries else None,
        "per_stage_cost_share_pct": (
            {k: round(_pct(v, total_cost) or 0.0, 2) for k, v in stage_cost.items()} if total_cost else {}
        ),
    }


def compute_wall_clock(senses: list[NormalizedSense]) -> dict:
    per_sense_seconds = [
        s.wall_clock_total_s if s.wall_clock_total_s is not None else sum(s.stage_timings.values())
        for s in senses
        if s.wall_clock_total_s is not None or s.stage_timings
    ]
    return {
        "senses_with_timings": len(per_sense_seconds),
        "wall_clock_per_sense_mean_s": round(_mean(per_sense_seconds), 2) if per_sense_seconds else None,
        "wall_clock_per_sense_p50_s": round(_percentile(per_sense_seconds, 50), 2)
        if per_sense_seconds
        else None,
        "wall_clock_per_sense_p90_s": round(_percentile(per_sense_seconds, 90), 2)
        if per_sense_seconds
        else None,
    }


def compute_all_metrics(senses: list[NormalizedSense], *, cost_rows: list[dict] | None = None) -> dict:
    return {
        "invalid_asset_rate": compute_invalid_asset_rate(senses),
        "judge_reject_rates": compute_judge_reject_rates(senses),
        "l1_drop_rate": compute_l1_drop_rate(senses),
        "cost": compute_cost_metrics(cost_rows or []),
        "wall_clock": compute_wall_clock(senses),
    }


# --------------------------------------------------------------------------
# Blind pairwise packs
# --------------------------------------------------------------------------

RUBRIC_MD = """\
## Rubric

For each level shown, compare Pack A and Pack B for the SAME sense and level and
judge which set of exercises is better, or call it a tie. Score on:

1. **Correctness** -- is the correct answer actually correct for the sentence/prompt shown?
2. **Single defensible answer** -- is exactly one option defensible as correct, with no
   distractor that a reasonable native speaker could also accept?
3. **Distractor plausibility** -- are distractors plausible confusions (not random noise),
   and none of them *also correct* ("also-correct" is a major defect, not a style nit)?
4. **Naturalness** -- does the sentence/prompt read as something a native speaker would
   actually write or say?
5. **Target-word anchoring** -- does the exercise actually test the target word/sense, not
   some other word in the sentence? **Known defect class: the target word appears only
   inside a compound word**, so the exercise is really testing the compound, not the
   target sense. Flag this explicitly as a major defect when you see it.
6. **L1 (`phonetic_recognition`) validity, if shown** -- L1 is an audio-confusable-only,
   listening exercise: pitch-accent-only distractor pairs are NOT valid, because TTS only
   renders one form. A pitch-accent-only distractor is a major defect, not a style nit.

Return one JSON line per (sense_id, level) you evaluated:
`{"sense_id": ..., "level": ..., "preferred": "A" | "B" | "tie", "major_defects_A": [...], "major_defects_B": [...], "notes": "..."}`
`major_defects_A` / `major_defects_B` are short strings from the checklist above (e.g.
"also-correct distractor", "compound-word anchoring", "pitch-accent-only L1 pair"), empty
list if none found. Do not guess which side is the candidate or reference -- you are not
told, and should not try to infer it from formatting.
"""


def _render_sense_level_md(sense: NormalizedSense, level: int) -> str:
    lines = [f"### Level {level} (sense {sense.sense_id}, difficulty {sense.difficulty})"]
    exs = [e for e in sense.exercises if e.level == level]
    if not exs:
        lines.append("_(no exercises at this level)_")
        return "\n".join(lines)
    for e in sorted(exs, key=lambda x: (x.variant or "", x.exercise_type)):
        lines.append(f"**{e.exercise_type}** variant `{e.variant or '-'}`, tier `{e.complexity_tier or '-'}`")
        lines.append("```json")
        lines.append(json.dumps(e.payload, ensure_ascii=False, indent=2))
        lines.append("```")
    return "\n".join(lines)


def build_pairwise_packs(
    candidate: list[NormalizedSense],
    reference: list[NormalizedSense],
    out_dir: str,
    *,
    pack_size: int = 10,
    seed: int = 0,
) -> dict:
    """Emits `<out_dir>/pairwise_packs/pack_NN.md` (blind, randomized A/B order
    per sense+level) and `<out_dir>/pairwise_key.json` (the unblinding key).

    Returns the key dict `{entries: [{key_id, sense_id, level, language,
    candidate_side: "A"|"B"}]}` (also what gets written to pairwise_key.json).
    """
    ref_by_id = {s.sense_id: s for s in reference}
    cand_by_id = {s.sense_id: s for s in candidate}
    common_ids = sorted(set(ref_by_id) & set(cand_by_id))

    rng = random.Random(seed)
    entries = []
    for sid in common_ids:
        ref_levels = {e.level for e in ref_by_id[sid].exercises if e.level is not None}
        cand_levels = {e.level for e in cand_by_id[sid].exercises if e.level is not None}
        for level in sorted(ref_levels & cand_levels):
            candidate_side = rng.choice(["A", "B"])
            entries.append(
                {
                    "key_id": f"{sid}::{level}",
                    "sense_id": sid,
                    "level": level,
                    "language": cand_by_id[sid].language,
                    "candidate_side": candidate_side,
                }
            )

    key_path = os.path.join(out_dir, "pairwise_key.json")
    os.makedirs(out_dir, exist_ok=True)
    key_doc = {"seed": seed, "pack_size": pack_size, "entries": entries}
    with open(key_path, "w", encoding="utf-8") as f:
        json.dump(key_doc, f, ensure_ascii=False, indent=2)

    packs_dir = os.path.join(out_dir, "pairwise_packs")
    os.makedirs(packs_dir, exist_ok=True)
    for i in range(0, len(entries), pack_size) if entries else []:
        chunk = entries[i : i + pack_size]
        pack_num = i // pack_size + 1
        md = [f"# Pairwise review pack {pack_num:02d}", "", RUBRIC_MD, ""]
        for entry in chunk:
            sid, level = entry["sense_id"], entry["level"]
            a_sense = cand_by_id[sid] if entry["candidate_side"] == "A" else ref_by_id[sid]
            b_sense = ref_by_id[sid] if entry["candidate_side"] == "A" else cand_by_id[sid]
            md.append(f"## sense {sid}, level {level}")
            md.append("")
            md.append("#### Pack A")
            md.append(_render_sense_level_md(a_sense, level))
            md.append("")
            md.append("#### Pack B")
            md.append(_render_sense_level_md(b_sense, level))
            md.append("")
            md.append("---")
            md.append("")
        pack_path = os.path.join(packs_dir, f"pack_{pack_num:02d}.md")
        with open(pack_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md))

    return key_doc


# --------------------------------------------------------------------------
# Non-inferiority decision
# --------------------------------------------------------------------------


@dataclass
class Thresholds:
    major_defect_margin_pp: float = 2.0
    pairwise_loss_margin_pp: float = 10.0
    coverage_min_pct: float = 95.0
    invalid_asset_margin_pp: float = 3.0


def _major_defect_rate_from_judges(metrics: dict) -> float | None:
    """Stand-in for "major-defect rate" using the aggregate render-judge reject
    rate across all judges, since no single "major defect" judge field exists
    in every run shape. If pairwise verdicts with `major_defects_*` are
    available, `decide_non_inferiority` prefers those (see below) -- this is
    the automatic-metrics fallback for criterion (a) when pairwise data is
    absent.
    """
    rates = [
        d["reject_rate_pct"]
        for d in metrics.get("judge_reject_rates", {}).values()
        if d.get("reject_rate_pct") is not None
    ]
    if not rates:
        return None
    return _mean(rates)


def decide_non_inferiority(
    candidate_metrics: dict,
    reference_metrics: dict,
    *,
    pairwise_summary: dict | None,
    thresholds: Thresholds,
    coverage: dict,
) -> dict:
    """PASS if all four criteria hold; otherwise FAIL, naming every criterion
    that failed (not just the first). A criterion with insufficient data to
    evaluate is reported as SKIPPED and does not cause a FAIL on its own.
    """
    criteria = {}

    # (a) major-defect rate <= reference + margin
    if pairwise_summary and "major_defect_rate_candidate" in pairwise_summary:
        cand_defect = pairwise_summary["major_defect_rate_candidate"]
        ref_defect = pairwise_summary.get("major_defect_rate_reference")
        source = "pairwise"
    else:
        cand_defect = _major_defect_rate_from_judges(candidate_metrics)
        ref_defect = _major_defect_rate_from_judges(reference_metrics)
        source = "judge_reject_rate_fallback"

    if cand_defect is None or ref_defect is None:
        criteria["a_major_defect_rate"] = {
            "status": "SKIPPED",
            "reason": "insufficient data (no judge verdicts and no pairwise results)",
            "source": source,
        }
    else:
        ok = cand_defect <= ref_defect + thresholds.major_defect_margin_pp
        criteria["a_major_defect_rate"] = {
            "status": "PASS" if ok else "FAIL",
            "candidate_pct": round(cand_defect, 2),
            "reference_pct": round(ref_defect, 2),
            "margin_pp": thresholds.major_defect_margin_pp,
            "source": source,
        }

    # (b) pairwise loss rate - win rate <= margin
    if pairwise_summary and "win_rate_pct" in pairwise_summary and "loss_rate_pct" in pairwise_summary:
        diff = pairwise_summary["loss_rate_pct"] - pairwise_summary["win_rate_pct"]
        ok = diff <= thresholds.pairwise_loss_margin_pp
        criteria["b_pairwise_loss_minus_win"] = {
            "status": "PASS" if ok else "FAIL",
            "loss_minus_win_pp": round(diff, 2),
            "margin_pp": thresholds.pairwise_loss_margin_pp,
        }
    else:
        criteria["b_pairwise_loss_minus_win"] = {
            "status": "SKIPPED",
            "reason": "no --pairwise-results provided; run scripts/merge_pairwise_verdicts.py first",
        }

    # (c) coverage >= threshold
    cov_pct = coverage.get("coverage_pct")
    if cov_pct is None:
        criteria["c_coverage"] = {"status": "SKIPPED", "reason": "no common senses to compare coverage on"}
    else:
        ok = cov_pct >= thresholds.coverage_min_pct
        criteria["c_coverage"] = {
            "status": "PASS" if ok else "FAIL",
            "coverage_pct": round(cov_pct, 2),
            "min_pct": thresholds.coverage_min_pct,
        }

    # (d) invalid-asset rate <= reference + margin
    cand_inv = candidate_metrics.get("invalid_asset_rate", {}).get("invalid_rate_pct")
    ref_inv = reference_metrics.get("invalid_asset_rate", {}).get("invalid_rate_pct")
    if cand_inv is None or ref_inv is None:
        criteria["d_invalid_asset_rate"] = {
            "status": "SKIPPED",
            "reason": "no assets with a known is_valid on one or both sides",
        }
    else:
        ok = cand_inv <= ref_inv + thresholds.invalid_asset_margin_pp
        criteria["d_invalid_asset_rate"] = {
            "status": "PASS" if ok else "FAIL",
            "candidate_pct": round(cand_inv, 2),
            "reference_pct": round(ref_inv, 2),
            "margin_pp": thresholds.invalid_asset_margin_pp,
        }

    failed = [k for k, v in criteria.items() if v["status"] == "FAIL"]
    skipped = [k for k, v in criteria.items() if v["status"] == "SKIPPED"]
    overall = "FAIL" if failed else "PASS"

    return {
        "overall": overall,
        "failed_criteria": failed,
        "skipped_criteria": skipped,
        "criteria": criteria,
    }


# --------------------------------------------------------------------------
# Report rendering
# --------------------------------------------------------------------------


def render_markdown_report(
    *,
    lang: str,
    candidate_path: str,
    reference_path: str,
    reference_meta: dict,
    coverage: dict,
    candidate_metrics: dict,
    reference_metrics: dict,
    decision: dict,
    thresholds: Thresholds,
    pairwise_summary: dict | None,
) -> str:
    lines = [
        f"# Exercise-gen quality score -- {lang}",
        "",
        f"- Candidate: `{candidate_path}`",
        f"- Reference: `{reference_path}` ({reference_meta.get('kind')})",
    ]
    if reference_meta.get("warning"):
        lines.append(f"- **Warning:** {reference_meta['warning']}")
    lines += [
        "",
        f"## Decision: {decision['overall']}",
        "",
        "| Criterion | Status | Detail |",
        "|---|---|---|",
    ]
    labels = {
        "a_major_defect_rate": "(a) major-defect rate <= reference + margin",
        "b_pairwise_loss_minus_win": "(b) pairwise loss - win <= margin",
        "c_coverage": "(c) coverage >= threshold",
        "d_invalid_asset_rate": "(d) invalid-asset rate <= reference + margin",
    }
    for key, label in labels.items():
        c = decision["criteria"][key]
        detail = ", ".join(f"{k}={v}" for k, v in c.items() if k != "status")
        lines.append(f"| {label} | {c['status']} | {detail} |")

    lines += [
        "",
        "## 1. Automatic metrics",
        "",
        "### Coverage (candidate vs reference)",
        f"```json\n{json.dumps(coverage, ensure_ascii=False, indent=2)}\n```",
        "",
        "### Candidate metrics",
        f"```json\n{json.dumps(candidate_metrics, ensure_ascii=False, indent=2)}\n```",
        "",
        "### Reference metrics",
        f"```json\n{json.dumps(reference_metrics, ensure_ascii=False, indent=2)}\n```",
        "",
        "## 2. Blind pairwise review",
        "",
    ]
    if pairwise_summary:
        lines.append(f"```json\n{json.dumps(pairwise_summary, ensure_ascii=False, indent=2)}\n```")
    else:
        lines.append(
            "No pairwise results yet. Packs are at `<candidate>/pairwise_packs/pack_NN.md`; "
            "have a fresh-context reviewer return `{sense_id, level, preferred, major_defects_A, "
            "major_defects_B, notes}` JSON lines, then run "
            "`python scripts/merge_pairwise_verdicts.py --candidate <candidate dir> --verdicts <file(s)>` "
            "and re-run this script with `--pairwise-results` to fold the result into the decision."
        )

    lines += [
        "",
        "## 3. Non-inferiority thresholds used",
        f"```json\n{json.dumps(thresholds.__dict__, ensure_ascii=False, indent=2)}\n```",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--candidate", required=True, help="Candidate run directory (data/eval/runs/<label>)")
    p.add_argument(
        "--reference",
        required=True,
        help="Reference: the frozen reference JSON, or a baseline run directory (zh/en)",
    )
    p.add_argument("--lang", required=True, choices=["en", "zh", "ja"])
    p.add_argument("--llm-calls-export", default=None, help="JSON export of llm_calls rows (optional)")
    p.add_argument(
        "--pairwise-results",
        default=None,
        help="Aggregate from merge_pairwise_verdicts.py; auto-detects <candidate>/pairwise_results.json",
    )
    p.add_argument("--skip-pairwise-packs", action="store_true")
    p.add_argument("--pack-size", type=int, default=10)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--major-defect-margin-pp", type=float, default=Thresholds.major_defect_margin_pp)
    p.add_argument("--pairwise-loss-margin-pp", type=float, default=Thresholds.pairwise_loss_margin_pp)
    p.add_argument("--coverage-min-pct", type=float, default=Thresholds.coverage_min_pct)
    p.add_argument("--invalid-asset-margin-pp", type=float, default=Thresholds.invalid_asset_margin_pp)
    p.add_argument("--out-dir", default=None, help="Defaults to --candidate")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = args.out_dir or args.candidate

    candidate_senses, _cand_summary = load_candidate_run(args.candidate, lang=args.lang)
    reference_senses, reference_meta = load_reference(args.reference, args.lang)

    cost_rows = load_cost_rows(senses=candidate_senses, llm_calls_export=args.llm_calls_export)
    ref_cost_rows = load_cost_rows(senses=reference_senses, llm_calls_export=None)

    candidate_metrics = compute_all_metrics(candidate_senses, cost_rows=cost_rows)
    reference_metrics = compute_all_metrics(reference_senses, cost_rows=ref_cost_rows)
    coverage = compute_coverage(candidate_senses, reference_senses)

    pairwise_summary = None
    pairwise_path = args.pairwise_results or os.path.join(args.candidate, "pairwise_results.json")
    if os.path.isfile(pairwise_path):
        with open(pairwise_path, "r", encoding="utf-8") as f:
            pairwise_summary = json.load(f)

    if not args.skip_pairwise_packs:
        build_pairwise_packs(
            candidate_senses, reference_senses, out_dir, pack_size=args.pack_size, seed=args.seed
        )

    thresholds = Thresholds(
        major_defect_margin_pp=args.major_defect_margin_pp,
        pairwise_loss_margin_pp=args.pairwise_loss_margin_pp,
        coverage_min_pct=args.coverage_min_pct,
        invalid_asset_margin_pp=args.invalid_asset_margin_pp,
    )
    decision = decide_non_inferiority(
        candidate_metrics,
        reference_metrics,
        pairwise_summary=pairwise_summary,
        thresholds=thresholds,
        coverage=coverage,
    )

    score_doc = {
        "lang": args.lang,
        "candidate": args.candidate,
        "reference": args.reference,
        "reference_meta": reference_meta,
        "coverage": coverage,
        "candidate_metrics": candidate_metrics,
        "reference_metrics": reference_metrics,
        "pairwise_summary": pairwise_summary,
        "thresholds": thresholds.__dict__,
        "decision": decision,
    }

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "score.json"), "w", encoding="utf-8") as f:
        json.dump(score_doc, f, ensure_ascii=False, indent=2)

    report_md = render_markdown_report(
        lang=args.lang,
        candidate_path=args.candidate,
        reference_path=args.reference,
        reference_meta=reference_meta,
        coverage=coverage,
        candidate_metrics=candidate_metrics,
        reference_metrics=reference_metrics,
        decision=decision,
        thresholds=thresholds,
        pairwise_summary=pairwise_summary,
    )
    with open(os.path.join(out_dir, "score_report.md"), "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"Decision: {decision['overall']}")
    if decision["failed_criteria"]:
        print("Failed criteria: " + ", ".join(decision["failed_criteria"]))
    if decision["skipped_criteria"]:
        print("Skipped criteria (insufficient data): " + ", ".join(decision["skipped_criteria"]))
    print(f"Wrote {os.path.join(out_dir, 'score.json')} and {os.path.join(out_dir, 'score_report.md')}")
    return 0 if decision["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
