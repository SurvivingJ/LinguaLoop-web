"""Unblind and aggregate pairwise review verdicts for TASK-807 (see
`scripts/score_exercise_gen_run.py`).

`score_exercise_gen_run.py --candidate <dir> ...` writes `<dir>/pairwise_key.json`
(the unblinding key: which of Pack A / Pack B was the candidate, per sense+level)
and `<dir>/pairwise_packs/pack_NN.md` (the blind packs, for a fresh-context
reviewer -- a Claude subagent or a human -- to judge without knowing which side
is which).

Each reviewer returns JSON lines shaped:
    {"sense_id": ..., "level": ..., "preferred": "A" | "B" | "tie",
     "major_defects_A": [...], "major_defects_B": [...], "notes": "..."}

This script reads those verdict files, joins them back to `pairwise_key.json` by
`(sense_id, level)`, flips `preferred`/`major_defects_*` from "A"/"B" into
"candidate"/"reference", and aggregates win/loss/tie rates and major-defect
rates for both sides. Write the result to `<candidate>/pairwise_results.json`
(the default output path) and pass it to `score_exercise_gen_run.py
--pairwise-results` to fold it into the non-inferiority decision.

    python scripts/merge_pairwise_verdicts.py \
        --candidate data/eval/runs/qwen-bundle-v1 \
        --verdicts data/eval/runs/qwen-bundle-v1/pairwise_verdicts/*.jsonl
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter


class VerdictShapeError(ValueError):
    pass


def load_key(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_verdict_lines(paths: list[str]) -> list[dict]:
    """Reads one or more files, each either JSON Lines (one verdict object per
    line) or a single JSON array of verdict objects. Blank lines are skipped.
    """
    verdicts: list[dict] = []
    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            continue
        if content.lstrip().startswith("["):
            items = json.loads(content)
        else:
            items = []
            for i, line in enumerate(content.splitlines()):
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise VerdictShapeError(f"{path}:{i + 1}: invalid JSON line: {e}") from e
        verdicts.extend(items)
    return verdicts


def unblind_and_aggregate(key: dict, verdicts: list[dict]) -> dict:
    """Maps each verdict's A/B fields to candidate/reference using `key`
    (as produced by `build_pairwise_packs`/`score_exercise_gen_run.py`), then
    aggregates. Verdicts whose (sense_id, level) is not in the key are
    reported under `unmatched` rather than silently dropped or guessed at.
    """
    by_key = {(str(e["sense_id"]), e["level"]): e for e in key.get("entries", [])}

    wins = losses = ties = 0
    major_defects_candidate = 0
    major_defects_reference = 0
    per_sense: list[dict] = []
    unmatched: list[dict] = []
    seen_keys: set[tuple] = set()

    for v in verdicts:
        try:
            sid = str(v["sense_id"])
            level = v["level"]
            preferred = v["preferred"]
        except KeyError as e:
            raise VerdictShapeError(f"verdict missing required field {e}: {v}") from e

        entry = by_key.get((sid, level))
        if entry is None:
            unmatched.append(v)
            continue
        seen_keys.add((sid, level))

        candidate_side = entry["candidate_side"]  # "A" or "B"
        reference_side = "B" if candidate_side == "A" else "A"

        if preferred == "tie":
            outcome = "tie"
            ties += 1
        elif preferred == candidate_side:
            outcome = "candidate_win"
            wins += 1
        elif preferred == reference_side:
            outcome = "reference_win"
            losses += 1
        else:
            raise VerdictShapeError(f"unrecognised preferred={preferred!r} for {sid}/{level}")

        defects_candidate = v.get(f"major_defects_{candidate_side}") or []
        defects_reference = v.get(f"major_defects_{reference_side}") or []
        if defects_candidate:
            major_defects_candidate += 1
        if defects_reference:
            major_defects_reference += 1

        per_sense.append(
            {
                "sense_id": sid,
                "level": level,
                "outcome": outcome,
                "major_defects_candidate": defects_candidate,
                "major_defects_reference": defects_reference,
                "notes": v.get("notes", ""),
            }
        )

    total_judged = wins + losses + ties
    missing_keys = [
        {"sense_id": e["sense_id"], "level": e["level"]}
        for k, e in by_key.items()
        if k not in seen_keys
    ]

    def pct(n: int, d: int) -> float | None:
        return round(100.0 * n / d, 2) if d else None

    return {
        "total_pairs_in_key": len(by_key),
        "total_judged": total_judged,
        "unmatched_verdicts": unmatched,
        "missing_verdicts": missing_keys,
        "candidate_wins": wins,
        "reference_wins": losses,
        "ties": ties,
        "win_rate_pct": pct(wins, total_judged),
        "loss_rate_pct": pct(losses, total_judged),
        "tie_rate_pct": pct(ties, total_judged),
        "major_defect_rate_candidate": pct(major_defects_candidate, total_judged),
        "major_defect_rate_reference": pct(major_defects_reference, total_judged),
        "per_sense": per_sense,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--candidate", required=True, help="Candidate run dir holding pairwise_key.json")
    p.add_argument(
        "--verdicts",
        required=True,
        nargs="+",
        help="Verdict file path(s) or glob(s) (JSONL or JSON array of verdict objects)",
    )
    p.add_argument("--out", default=None, help="Defaults to <candidate>/pairwise_results.json")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    key_path = os.path.join(args.candidate, "pairwise_key.json")
    key = load_key(key_path)

    paths: list[str] = []
    for pattern in args.verdicts:
        matched = glob.glob(pattern)
        paths.extend(matched if matched else [pattern])

    verdicts = load_verdict_lines(paths)
    result = unblind_and_aggregate(key, verdicts)

    out_path = args.out or os.path.join(args.candidate, "pairwise_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(
        f"Judged {result['total_judged']}/{result['total_pairs_in_key']} pairs: "
        f"candidate wins {result['win_rate_pct']}%, reference wins {result['loss_rate_pct']}%, "
        f"ties {result['tie_rate_pct']}%"
    )
    if result["unmatched_verdicts"]:
        print(f"WARNING: {len(result['unmatched_verdicts'])} verdicts did not match any key entry")
    if result["missing_verdicts"]:
        print(f"WARNING: {len(result['missing_verdicts'])} key entries have no verdict yet")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
