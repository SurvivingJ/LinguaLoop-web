#!/usr/bin/env python3
"""Dual-translation grading eval harness — runner (TASK-622).

Grades every item in a frozen gold set (`tests/fixtures/dt_gold/{l2}.json`, TASK-621)
through `services.dual_translation.grader_cascade.grade_submission` (real OpenRouter calls),
then computes the full §10 metric set via the pure functions in
`services.dual_translation.eval_metrics` and writes a per-L2 markdown report.

Framework selection is EXPLICIT (TASK-632): the default grades the v1 tier1/tier2 cascade;
`--framework-v2` grades the TASK-628 Detector/Verifier flow. The chosen framework is passed
as `grade_submission(..., framework_v2=...)` — never inherited from the ambient
`DT_FRAMEWORK_V2` env var — so a run's report is self-documenting and reproducible
regardless of process environment.

This is the regression gate every later Evidence-First task (623..632) re-runs. It measures
the grader; it never modifies grading code.

Cost/paid discipline:
  * Live model calls are gated behind `--live`. Without it the runner loads fixtures, resolves
    ids, prints the plan, and exits WITHOUT spending anything.
  * One pass per L2 per invocation (grade each item exactly once). Tier-0-resolved items cost
    zero tokens (tier0's own result cache + full-marks short-circuit).
  * Per-call (model, tokens) are recorded by wrapping grader_cascade.call_model_with_usage;
    USD cost is computed from the OpenRouter pricing map (services.model_arena.pricing).

Usage:
    python scripts/run_dt_grading_eval.py --l2 ja --out report.md --live
    python scripts/run_dt_grading_eval.py --l2 en --out report.md            # dry plan, no calls
    python scripts/run_dt_grading_eval.py --l2 zh --out report.md --live --limit 2   # cheap smoke

Taxonomy candidate (TASK-849, evaluate-before-activate, mirrors --rubric-file):
    python scripts/run_dt_grading_eval.py --l2 en --out r.md --framework-v2 \\
        --taxonomy-file migrations/dt_taxonomy_v6_seed.sql --fixture-set v6      # dry plan
  `--taxonomy-file` parses the seed's $taxonomy$ literal OFFLINE and pre-seeds
  grader_cascade._cfg_cache (taxonomy + taxonomy_version), so grading uses it without
  the version existing in the DB. `--fixture-set {v5,v6,v6_silver}` picks
  tests/fixtures/{dt_gold,dt_gold_v6,dt_silver_v6} (default v5 = unchanged behaviour).
"""

import argparse
import datetime as _dt
import json
import logging
import math
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

try:  # httpx is the OpenRouter client's transport; optional so the retry helper imports without it
    import httpx as _httpx
    _TRANSIENT_EXC: tuple = (
        _httpx.ConnectError, _httpx.ConnectTimeout, _httpx.ReadTimeout,
        _httpx.WriteTimeout, _httpx.PoolTimeout, _httpx.RemoteProtocolError,
    )
except Exception:  # pragma: no cover - httpx present in this project, guard is defensive
    _httpx = None
    _TRANSIENT_EXC = ()

from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.dimension_service import DimensionService
from services.dual_translation import eval_metrics as em
from services.dual_translation import grader_cascade as gc
from services.model_arena import pricing as arena_pricing

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("run_dt_grading_eval")

_FIXTURES_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "fixtures")
FIXTURE_DIR = os.path.join(_FIXTURES_ROOT, "dt_gold")
# TASK-849: --fixture-set -> fixture dir. v5 (default) is the frozen v5 gold set.
FIXTURE_DIRS = {
    "v5": FIXTURE_DIR,
    "v6": os.path.join(_FIXTURES_ROOT, "dt_gold_v6"),
    "v6_silver": os.path.join(_FIXTURES_ROOT, "dt_silver_v6"),
}
# Log lines counted per run (TASK-849/850 gate: both must be 0 for en/zh under v6).
_EXEMPLAR_DROP_LOGGER = "services.dual_translation.prompts"
_NO_TEMPLATE_LOGGER = "services.dual_translation.grader_cascade"

# Fallback age tier per L2 if a passage row can't be read (README: en/ja tier 3, zh tier 6).
_DEFAULT_AGE_TIER = {"en": 3, "zh": 6, "ja": 3}
# Default L1 (explanation language only — does not affect the measured metrics). Kept != L2.
_DEFAULT_L1 = {"en": "zh", "zh": "en", "ja": "en"}

# Substrings that mark an error as transient (retryable) even when it isn't one of
# the typed httpx exceptions — DNS blips (getaddrinfo, the failure that orphaned JA
# twice in TASK-625), resets, and upstream 5xx/overload/rate-limit responses.
_TRANSIENT_MARKERS = (
    "getaddrinfo", "temporarily unavailable", "connection reset", "connection aborted",
    "timed out", "timeout", "502", "503", "504", "overloaded", "rate limit",
    "too many requests", "remotedisconnected", "server disconnected",
)


# ---------------------------------------------------------------------------
# Retry + resume (TASK-626 hardening)
# ---------------------------------------------------------------------------

def _is_transient(exc: BaseException) -> bool:
    """True if `exc` is a network/transient failure worth retrying (vs. a
    deterministic bug we shouldn't hammer). Typed httpx transport errors count;
    otherwise fall back to message markers (covers the wrapped getaddrinfo DNS
    failure and upstream 5xx/overload without importing every client's error type)."""
    if _TRANSIENT_EXC and isinstance(exc, _TRANSIENT_EXC):
        return True
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(m in text for m in _TRANSIENT_MARKERS)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_is_transient),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _grade_once(grade_fn):
    """The single graded model call, wrapped in tenacity's bounded exponential-backoff
    retry (the project convention — see services/ai_service.py, base_generator.py).

    Only transient network/upstream errors are retried (`retry_if_exception(_is_transient)`);
    a non-transient error is re-raised on the first attempt without retrying. `reraise=True`
    surfaces the ORIGINAL exception (not tenacity's RetryError) so `_grade_with_retry`'s
    classifier/bookkeeping sees the real cause.
    """
    return grade_fn()


def _grade_with_retry(grade_fn, item_id: str):
    """Call `grade_fn()` through `_grade_once` (bounded retry on transient errors).

    Returns (result, error): (contract, None) on success, or (None, last_exc) when
    the item is given up on — a transient error that outlived the retry envelope, OR
    any non-transient error (re-raised on the first attempt, not retried). Either way
    it RETURNS rather than raises, so one bad item can't abort the whole L2 run (the
    failure mode that orphaned JA in TASK-625). Behaviour-neutral when the network is
    fine: the first call succeeds and no sleep happens.
    """
    try:
        return _grade_once(grade_fn), None
    except Exception as exc:  # noqa: BLE001 - deliberately broad: classify, don't crash
        logger.error("grade_submission gave up on %s (transient=%s): %s",
                     item_id, _is_transient(exc), exc)
        return None, exc


def _load_checkpoint(path: str | None) -> dict:
    """Load a resume log into {"records":[...], "skipped":[...]} — the normalized
    eval dicts aggregate_metrics consumes, so a resumed run re-pays for nothing
    already graded. Missing/unreadable/empty → empty (fresh run).

    Format (TASK-644): append-only JSONL, one envelope per completed item —
    {"type": "record"|"skipped", "data": {...}}. A partial trailing line (crash
    mid-append) is skipped, not fatal. A legacy pre-TASK-644 sidecar (the whole
    file is one indented {"records":[...],"skipped":[...]} object) is read once
    and migrated to JSONL in place, so the rest of the run appends consistently."""
    if not path or not os.path.exists(path):
        return {"records": [], "skipped": []}
    try:
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
    except Exception as exc:  # pragma: no cover - unreadable checkpoint shouldn't be silent
        logger.warning("could not read resume checkpoint %s (%s); starting fresh", path, exc)
        return {"records": [], "skipped": []}

    stripped = content.strip()
    if not stripped:
        return {"records": [], "skipped": []}

    # Legacy format (pre-TASK-644): the whole file parses as one JSON object with
    # records/skipped arrays. A JSONL log won't (multiple top-level objects), so
    # this only fires for old sidecars. Migrate to JSONL in place after reading.
    try:
        legacy = json.loads(stripped)
    except json.JSONDecodeError:
        legacy = None
    if isinstance(legacy, dict) and ("records" in legacy or "skipped" in legacy):
        data = {
            "records": list(legacy.get("records") or []),
            "skipped": list(legacy.get("skipped") or []),
        }
        _migrate_checkpoint_to_jsonl(path, data)
        return data

    # Current format: JSONL, one envelope per line. Stream to rebuild the arrays.
    records: list[dict] = []
    skipped: list[dict] = []
    for line in stripped.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            env = json.loads(line)
        except json.JSONDecodeError:
            # A crash mid-append can leave a half-written final line; skip it.
            logger.warning("skipping unparseable line in resume checkpoint %s", path)
            continue
        etype = env.get("type")
        if etype == "record":
            records.append(env.get("data", {}))
        elif etype == "skipped":
            skipped.append(env.get("data", {}))
    return {"records": records, "skipped": skipped}


def _save_checkpoint(path: str | None, *, record: dict | None = None,
                     skipped: dict | None = None) -> None:
    """Append the one freshly-completed item to the JSONL resume log — O(1) per
    item, vs the pre-TASK-644 full-file rewrite that was O(n²) over a run. Pass
    exactly one of `record` (graded ok) / `skipped` (gave up). flush()+fsync()
    after the write so a mid-run teardown resumes from the last completed item
    rather than restarting. A write failure is logged, never fatal."""
    if not path:
        return
    if record is not None:
        entry = {"type": "record", "data": record}
    elif skipped is not None:
        entry = {"type": "skipped", "data": skipped}
    else:
        return
    try:
        # If a prior crash left a torn (newline-less) final line, lead with a
        # newline so this complete entry lands on its own parseable line instead
        # of being concatenated onto the garbage (which would lose it too).
        prefix = "\n" if _needs_leading_newline(path) else ""
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(prefix + json.dumps(entry, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    except Exception as exc:  # pragma: no cover - a checkpoint write failure shouldn't abort the run
        logger.warning("could not append to resume checkpoint %s (%s)", path, exc)


def _needs_leading_newline(path: str) -> bool:
    """True iff `path` exists, is non-empty, and its last byte isn't a newline —
    i.e. a crash left a torn final line the next append must not glue onto."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            if fh.tell() == 0:
                return False
            fh.seek(-1, os.SEEK_END)
            return fh.read(1) != b"\n"
    except OSError:  # pragma: no cover - missing file → fresh append, no prefix needed
        return False


def _migrate_checkpoint_to_jsonl(path: str, data: dict) -> None:
    """Rewrite a legacy whole-file checkpoint as append-only JSONL (write-to-temp
    then replace so a crash can't corrupt it), so the rest of the run appends one
    line per item instead of falling back to the old rewrite path."""
    tmp = f"{path}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            for rec in data.get("records", []):
                fh.write(json.dumps({"type": "record", "data": rec}, ensure_ascii=False) + "\n")
            for sk in data.get("skipped", []):
                fh.write(json.dumps({"type": "skipped", "data": sk}, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception as exc:  # pragma: no cover - migration failure shouldn't abort the run
        logger.warning("could not migrate legacy checkpoint %s to JSONL (%s)", path, exc)


# ---------------------------------------------------------------------------
# Fixture -> eval record normalization
# ---------------------------------------------------------------------------

def _load_fixture(l2: str, fixture_set: str = "v5") -> list[dict]:
    path = os.path.join(FIXTURE_DIRS[fixture_set], f"{l2}.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _pred_errors(contract: dict) -> list[dict]:
    """Normalize the v1 grading contract's errors[] into the eval record shape.
    `explanation_variant` is None until the grader emits it (TASK-845)."""
    out = []
    for e in contract.get("errors", []):
        out.append({
            "span": e["span_reproduction"],
            "subtype": e.get("subtype"),
            "severity": e.get("severity"),
            "explanation_variant": e.get("explanation_variant"),
        })
    return out


def _exp_errors(item: dict) -> list[dict]:
    """Normalize a gold item's expected_errors into the eval record shape.

    TASK-625: reads the triad `severity_v2` (minor/major/critical) — the live
    grader now emits the triad, so severity agreement is measured against it (the
    fixtures carry both `severity_v1` and `severity_v2`). The runner passes
    `em.SEVERITY_TRIAD_ORDER` to aggregate_metrics so within-one is meaningful.
    """
    out = []
    for e in item.get("expected_errors", []):
        out.append({
            "span": e["span_repro"],
            "subtype": e.get("subtype"),
            "severity": e.get("severity_v2"),
            # v6 fixtures only (TASK-847); absent on the v5 set -> None.
            "explanation_variant": e.get("explanation_variant"),
        })
    return out


def _build_record(it: dict, contract: dict, rubric_cfg: dict, l2: str) -> dict:
    """One graded item -> the neutral eval record (eval_metrics module docstring)."""
    exp_bands = it["expected_bands"]
    return {
        "id": it["id"],
        "kind": it["kind"],
        "pred_errors": _pred_errors(contract),
        "exp_errors": _exp_errors(it),
        "pred_bands": contract["scores"],
        "exp_bands": exp_bands,
        "pred_overall": contract["overall_band"],
        "exp_overall": gc.compute_overall_band(exp_bands, rubric_cfg, l2),
        # TASK-845 grader_trace.variant_basis ({basis: n}); {} until it ships.
        "pred_variant_basis": (contract.get("grader_trace") or {}).get("variant_basis") or {},
    }


# ---------------------------------------------------------------------------
# Cost recording (wrap the model boundary grade_submission calls through)
# ---------------------------------------------------------------------------

class _CallRecorder:
    """Wraps grader_cascade.call_model_with_usage to log (model, tokens) per LLM call."""

    def __init__(self):
        self.calls: list[dict] = []
        self._orig = None
        # TASK-643: the cascade now issues Tier 1 and Tier 2 concurrently in the
        # forced-recheck branch, so _recording runs on two threads at once. Guard
        # the append with a lock (list.append is atomic under CPython's GIL, but
        # the explicit lock makes the contract hold regardless of interpreter).
        self._lock = threading.Lock()

    def __enter__(self):
        self._orig = gc.call_model_with_usage

        def _recording(model, prompt, **kwargs):
            content, tin, tout, latency = self._orig(model, prompt, **kwargs)
            with self._lock:
                self.calls.append({"model": model, "in": int(tin or 0), "out": int(tout or 0)})
            return content, tin, tout, latency

        gc.call_model_with_usage = _recording
        return self

    def __exit__(self, *exc):
        gc.call_model_with_usage = self._orig
        return False

    def total_cost(self, pricing_map: dict) -> float:
        total = 0.0
        for c in self.calls:
            total += arena_pricing.compute_cost(c["in"], c["out"], pricing_map.get(c["model"], {}))
        return total

    @property
    def slugs(self) -> list[str]:
        return sorted({c["model"] for c in self.calls})

    @property
    def tokens_in(self) -> int:
        return sum(c["in"] for c in self.calls)

    @property
    def tokens_out(self) -> int:
        return sum(c["out"] for c in self.calls)


def _load_candidate_rubric(path: str) -> tuple[int, dict]:
    """Parse a dt_rubric_v*_seed.sql migration into (version, config) using the
    same extraction the rubric seed tests use: the $rubric$...$rubric$ dollar-
    quoted literal is the config JSON; the version is the first INSERT VALUES
    integer. Lets the harness evaluate a candidate rubric before it is activated
    live (TASK-632)."""
    import re as _re
    text = open(path, encoding="utf-8").read()
    m = _re.search(r"\$rubric\$(.*?)\$rubric\$", text, _re.DOTALL)
    if not m:
        raise SystemExit(f"[error] no $rubric$...$rubric$ config literal in {path}")
    config = json.loads(m.group(1))
    vm = _re.search(r"VALUES\s*\(\s*(\d+)\s*,", text)
    version = int(vm.group(1)) if vm else -1
    return version, config


def _load_candidate_taxonomy(path: str) -> tuple[int, dict]:
    """Parse a dt_taxonomy_v*_seed.sql migration into (version, taxonomy) — the
    $taxonomy$...$taxonomy$ literal is the JSONB, the version the first INSERT VALUES
    integer (same extraction the taxonomy seed tests use). Offline: no DB read, so a
    seed that is written but not applied (v6 before TASK-853) can be evaluated."""
    import re as _re
    text = open(path, encoding="utf-8").read()
    m = _re.search(r"\$taxonomy\$(.*?)\$taxonomy\$", text, _re.DOTALL)
    if not m:
        raise SystemExit(f"[error] no $taxonomy$...$taxonomy$ literal in {path}")
    taxonomy = json.loads(m.group(1))
    vm = _re.search(r"VALUES\s*\(\s*(\d+)\s*,", text)
    if not vm:
        raise SystemExit(f"[error] no INSERT ... VALUES (<version>, ...) in {path}")
    return int(vm.group(1)), taxonomy


def _preseed_candidate_taxonomy(version: int, taxonomy: dict) -> None:
    """Pre-seed grader_cascade's process-wide config cache so get_active_taxonomy()
    and get_active_taxonomy_version() serve the candidate for the whole run. Nothing
    is written to the DB. Seeds both the unpinned keys and the `taxonomy@<v>` key the
    DT_TAXONOMY_VERSION pin reads; a pin naming a DIFFERENT version is a conflicting
    instruction and aborts rather than silently grading under the wrong taxonomy."""
    pin = gc.taxonomy_version_pin()
    if pin is not None and pin != version:
        raise SystemExit(f"[error] DT_TAXONOMY_VERSION={pin} conflicts with --taxonomy-file "
                         f"version {version}; unset the env var or pick the matching file.")
    gc._cfg_cache["taxonomy"] = taxonomy
    gc._cfg_cache[f"taxonomy@{version}"] = taxonomy
    gc._cfg_cache["taxonomy_version"] = version


def _taxonomy_summary(taxonomy: dict) -> str:
    """One-line plan summary: per-L2 baseline subtype counts."""
    pairs = taxonomy.get("pairs") or {}
    counts = [f"{k}={len((v or {}).get('subtypes') or [])}" for k, v in sorted(pairs.items())
              if k in ("en", "zh", "ja") and isinstance(v, dict)]
    return f"{len(pairs)} pair keys; baseline subtypes {' '.join(counts) or '—'}"


class _LogCounter(logging.Filter):
    """Counts grader log lines the v6 gate cares about, for the run's report:
      * exemplar_drop — prompts.py "dropping the ... exemplar" WARNINGs (rubric
        exemplar slug did not resolve against the taxonomy; must be 0 for en/zh);
      * no_explanation_template — grader_cascade's INFO "no explanation template".
    Installed as a logger-level filter: grader_cascade's level is dropped to INFO so
    the INFO line reaches the filter, and sub-WARNING records are then suppressed
    (returns False) so console output is unchanged. Restored on exit."""

    def __init__(self):
        super().__init__()
        self.counts = {"exemplar_drop": 0, "no_explanation_template": 0}
        self._loggers: list[tuple[logging.Logger, int]] = []

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if record.name == _EXEMPLAR_DROP_LOGGER and "exemplar" in msg and "dropping" in msg:
            self.counts["exemplar_drop"] += 1
        elif record.name == _NO_TEMPLATE_LOGGER and "no explanation template" in msg:
            self.counts["no_explanation_template"] += 1
        return record.levelno >= logging.WARNING

    def __enter__(self):
        for name in (_EXEMPLAR_DROP_LOGGER, _NO_TEMPLATE_LOGGER):
            lg = logging.getLogger(name)
            self._loggers.append((lg, lg.level))
            if name == _NO_TEMPLATE_LOGGER:
                lg.setLevel(logging.INFO)
            lg.addFilter(self)
        return self

    def __exit__(self, *exc):
        for lg, level in self._loggers:
            lg.removeFilter(self)
            lg.setLevel(level)
        self._loggers.clear()
        return False


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def _fmt(x, nd=3) -> str:
    if x is None:
        return "—"
    if isinstance(x, float) and math.isnan(x):
        return "n/a"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def _render_v6_section(v6: dict, log_counts: dict) -> list[str]:
    """TASK-849 report block (taxonomy v6 metrics + gate log counts)."""
    lines = ["## Taxonomy v6 metrics", ""]
    mi = v6["meaning_inversion"]
    lines.append("| metric | value |")
    lines.append("|---|---|")
    lines.append(f"| meaning_inversion recall | {_fmt(mi['recall'])} ({mi['tp']}/{mi['n_expected']}) |")
    lines.append(f"| meaning_inversion precision | {_fmt(mi['precision'])} ({mi['tp']}/{mi['n_predicted']}) |")
    ev = v6["explanation_variant"]
    lines.append(f"| explanation_variant accuracy (word_choice TPs) | {_fmt(ev['accuracy'])} "
                 f"({ev['correct']}/{ev['total']}; {ev['pred_missing']} with no predicted variant) |")
    basis = ", ".join(f"{k}={v}" for k, v in ev["variant_basis"].items()) or "— (not emitted)"
    lines.append(f"| variant_basis distribution | {basis} |")
    lines.append(f"| exemplar-drop warnings (must be 0 for en/zh) | {log_counts.get('exemplar_drop', 0)} |")
    lines.append(f"| \"no explanation template\" lines | {log_counts.get('no_explanation_template', 0)} |")
    lines.append("")
    conf = v6["mi_confusion"]
    labels = conf["labels"]
    lines.append("### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)")
    lines.append("")
    lines.append("| expected \\ predicted | " + " | ".join(labels) + " |")
    lines.append("|---|" + "---|" * len(labels))
    for e in labels:
        lines.append(f"| {e} | " + " | ".join(str(conf["matrix"][e][p]) for p in labels) + " |")
    lines.append("")
    return lines


def _render_report(l2: str, metrics: dict, meta: dict) -> str:
    fw_label = ("v2 Detector/Verifier cascade (`grade_submission(framework_v2=True)`)"
                if meta.get("framework_v2")
                else "v1 tier1/tier2 cascade (`grade_submission(framework_v2=False)`)")
    lines: list[str] = []
    lines.append(f"# DT Grading Eval — {'v2' if meta.get('framework_v2') else 'v1'} ({l2.upper()})")
    lines.append("")
    lines.append(f"- **Run date:** {meta['date']}")
    lines.append(f"- **L2 / L1:** {l2} / {meta['l1']}")
    lines.append(f"- **Items graded:** {metrics['n_items']} "
                 f"(clean {metrics['kind_counts']['clean']} / single {metrics['kind_counts']['single']} / multi {metrics['kind_counts']['multi']})")
    if meta.get("resumed") or meta.get("skipped"):
        lines.append(f"- **Resumed / skipped:** {meta.get('resumed', 0)} reused from checkpoint · "
                     f"{len(meta.get('skipped') or [])} skipped ({', '.join(meta.get('skipped') or []) or 'none'})")
    lines.append(f"- **Grader:** {fw_label}, slugs: {', '.join(meta['slugs']) or '—'}")
    if meta.get("rubric_file"):
        lines.append(f"- **Rubric:** CANDIDATE config from `{meta['rubric_file']}` "
                     f"(pre-seeded into the config cache; live DB rubric not modified)")
    lines.append(f"- **Fixture set:** {meta.get('fixture_set', 'v5')}")
    if meta.get("taxonomy_file"):
        lines.append(f"- **Taxonomy:** CANDIDATE v{meta.get('taxonomy_version')} from "
                     f"`{meta['taxonomy_file']}` (pre-seeded into the config cache; live DB "
                     f"taxonomy not modified)")
    else:
        lines.append("- **Taxonomy:** live (active DB row, or the DT_TAXONOMY_VERSION pin)")
    lines.append(f"- **Tokens:** {meta['tokens_in']:,} in / {meta['tokens_out']:,} out — "
                 f"model calls: {meta['n_calls']}")
    lines.append(f"- **Est. cost:** ${meta['cost']:.4f} USD (model-arena pricing)")
    lines.append("")

    span = metrics["span"]
    lines.append("## Span detection (relaxed ≥50% overlap)")
    lines.append("")
    lines.append("| precision | recall | F1 | TP | FP | FN |")
    lines.append("|---|---|---|---|---|---|")
    lines.append(f"| {_fmt(span['precision'])} | {_fmt(span['recall'])} | {_fmt(span['f1'])} | "
                 f"{span['tp']} | {span['fp']} | {span['fn']} |")
    lines.append("")

    sub = metrics["subtype_accuracy"]
    sev = metrics["severity"]
    fp = metrics["clean_fp"]
    lines.append("## Classification + false positives")
    lines.append("")
    lines.append("| metric | value |")
    lines.append("|---|---|")
    lines.append(f"| Subtype accuracy (matched pairs, vs v4) | {_fmt(sub['accuracy'])} ({sub['correct']}/{sub['total']}) |")
    lines.append(f"| Severity exact (triad minor/major/critical) | {_fmt(sev['exact'])} (n={sev['n']}) |")
    lines.append(f"| **Severity within-one (triad)** | {_fmt(sev['within_one'])} |")
    lines.append(f"| **Clean-passage FP rate (items flagged)** | {_fmt(fp['item_fp_rate'])} ({fp['n']} clean items) |")
    lines.append(f"| Clean-passage mean spurious errors/item | {_fmt(fp['mean_errors'])} ({fp['total_errors']} total) |")
    lines.append("")

    lines.append("## Per-dimension band agreement")
    lines.append("")
    lines.append("| dimension | QWK | exact | adjacent | n |")
    lines.append("|---|---|---|---|---|")
    for dim in em.DIMENSIONS:
        b = metrics["bands"][dim]
        lines.append(f"| {dim} | {_fmt(b['qwk'])} | {_fmt(b['exact'])} | {_fmt(b['adjacent'])} | {b['n']} |")
    ov = metrics["overall"]
    lines.append(f"| **overall_band** | {_fmt(ov['qwk'])} | {_fmt(ov['exact'])} | {_fmt(ov['adjacent'])} | {ov['n']} |")
    lines.append("")

    v6 = metrics.get("v6")
    if v6:
        lines.extend(_render_v6_section(v6, meta.get("log_counts") or {}))

    lines.append("## Raw metrics (JSON)")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(metrics, indent=2, default=lambda o: "NaN" if isinstance(o, float) and math.isnan(o) else o))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="DT grading eval harness (TASK-622)")
    ap.add_argument("--l2", required=True, choices=["en", "zh", "ja"], help="L2 gold set to grade")
    ap.add_argument("--l1", default=None, help="L1 (explanation language; default != L2). Metrics-neutral.")
    ap.add_argument("--out", required=True, help="Output markdown report path")
    ap.add_argument("--live", action="store_true", help="Make real (paid) OpenRouter calls. Required to grade.")
    ap.add_argument("--limit", type=int, default=0, help="Cap items graded (0 = all). For a cheap live smoke.")
    ap.add_argument("--resume", default=None,
                    help="Resume checkpoint path (sidecar JSON). Already-graded items are "
                         "reused (not re-paid); progress is saved after every item so a "
                         "mid-run teardown continues instead of restarting.")
    ap.add_argument("--framework-v2", action="store_true",
                    help="Grade through the TASK-628 Detector/Verifier v2 flow instead of the "
                         "v1 tier1/tier2 cascade. Passed explicitly to grade_submission — the "
                         "ambient DT_FRAMEWORK_V2 env var is ignored either way.")
    ap.add_argument("--rubric-file", default=None,
                    help="Evaluate a CANDIDATE rubric config without activating it live: path to "
                         "a dt_rubric_v*_seed.sql; its $rubric$...$rubric$ config literal is "
                         "parsed and pre-seeded into grader_cascade's config cache, so every "
                         "grade in this run uses it while the live DB rubric is untouched. "
                         "Evaluate-before-activate (TASK-632).")
    ap.add_argument("--taxonomy-file", default=None,
                    help="Evaluate a CANDIDATE taxonomy without it being applied/active: path to "
                         "a dt_taxonomy_v*_seed.sql; its $taxonomy$...$taxonomy$ literal is parsed "
                         "offline and pre-seeded (taxonomy + version) into grader_cascade's config "
                         "cache; live DB untouched (TASK-849).")
    ap.add_argument("--fixture-set", default="v5", choices=sorted(FIXTURE_DIRS),
                    help="Gold set: v5 = tests/fixtures/dt_gold (default), v6 = dt_gold_v6, "
                         "v6_silver = dt_silver_v6 (TASK-847).")
    args = ap.parse_args()

    l2 = args.l2
    l1 = args.l1 or _DEFAULT_L1[l2]
    items = _load_fixture(l2, args.fixture_set)
    if args.limit:
        items = items[: args.limit]

    kinds = {"clean": 0, "single": 0, "multi": 0}
    for it in items:
        kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
    print(f"[plan] L2={l2} L1={l1} fixture-set={args.fixture_set} items={len(items)} "
          f"(clean {kinds['clean']} / single {kinds['single']} / multi {kinds['multi']}) "
          f"framework={'v2' if args.framework_v2 else 'v1'}")

    cand_tax = None
    if args.taxonomy_file:
        cand_tax = _load_candidate_taxonomy(args.taxonomy_file)  # offline parse, even on a dry run
        print(f"[taxonomy] candidate v{cand_tax[0]} parsed from {args.taxonomy_file}: "
              f"{_taxonomy_summary(cand_tax[1])}")
        if (cand_tax[0] >= 6) != args.fixture_set.startswith("v6"):
            print(f"[warn] taxonomy v{cand_tax[0]} with fixture-set {args.fixture_set}: "
                  f"gold subtype labels are on the other taxonomy, so subtype metrics will mismatch.")
    elif args.fixture_set != "v5":
        print(f"[warn] fixture-set {args.fixture_set} without --taxonomy-file: grading uses the "
              f"live taxonomy (v5 unless DT_TAXONOMY_VERSION pins another), so v6 subtype "
              f"labels will mismatch.")

    if not args.live:
        print("[dry-run] no --live flag: refusing to make paid OpenRouter calls. "
              "Re-run with --live to execute the graded pass.")
        return 0

    SupabaseFactory.initialize()
    db = get_supabase_admin()
    if db is None:
        print("[error] no service-role Supabase client (SUPABASE_SERVICE_ROLE_KEY missing).", file=sys.stderr)
        return 2

    # Populate DimensionService's id<->code metadata (grade_submission calls
    # get_language_code internally; without this its cache is empty).
    DimensionService.initialize(db)

    l2_language_id = DimensionService.get_language_id(l2, supabase_client=db)
    l1_language_id = DimensionService.get_language_id(l1, supabase_client=db)
    if not l2_language_id or not l1_language_id:
        print(f"[error] could not resolve language ids (l2={l2}->{l2_language_id}, l1={l1}->{l1_language_id})", file=sys.stderr)
        return 2

    # age_tier per source passage (rubric band-descriptor selection only).
    passage_ids = sorted({it["source_passage_id"] for it in items})
    age_by_id: dict[int, int] = {}
    try:
        resp = db.table("dt_passage").select("id, age_tier").in_("id", passage_ids).execute()
        age_by_id = {r["id"]: r["age_tier"] for r in (resp.data or [])}
    except Exception as exc:
        logger.warning("could not read dt_passage age tiers (%s); using default %s", exc, _DEFAULT_AGE_TIER[l2])

    if args.rubric_file:
        cand_version, cand_cfg = _load_candidate_rubric(args.rubric_file)
        # Pre-seed the process-wide config cache: get_active_rubric() (and the
        # grader_trace prompt_version) will serve the candidate for the whole run.
        # Nothing is written to the DB — evaluate-before-activate.
        gc._cfg_cache["rubric"] = cand_cfg
        gc._cfg_cache["rubric_version"] = cand_version
        print(f"[rubric] candidate v{cand_version} loaded from {args.rubric_file} "
              f"(live DB rubric untouched)")

    if cand_tax is not None:
        _preseed_candidate_taxonomy(*cand_tax)
        print(f"[taxonomy] candidate v{cand_tax[0]} pre-seeded into the config cache "
              f"(live DB taxonomy untouched)")

    rubric_cfg = gc.get_active_rubric(db)

    # Resume: reuse already-graded records/skips (never re-paid), then grade the rest.
    ckpt = _load_checkpoint(args.resume)
    records: list[dict] = list(ckpt["records"])
    skipped: list[dict] = list(ckpt["skipped"])
    done_ids = {r["id"] for r in records} | {s["id"] for s in skipped}
    resumed_count = len(records)
    if args.resume:
        print(f"[resume] loaded {resumed_count} graded + {len(skipped)} skipped from {args.resume}")

    with _CallRecorder() as rec, _LogCounter() as log_counter:
        for idx, it in enumerate(items, 1):
            if it["id"] in done_ids:
                print(f"[{idx}/{len(items)}] {it['id']} — reused from checkpoint")
                continue
            age_tier = age_by_id.get(it["source_passage_id"], _DEFAULT_AGE_TIER[l2])
            # Bounded retry on transient errors; skip-and-log (never raise) on give-up,
            # so a single DNS blip or bad item can't orphan the whole L2 run (TASK-625).
            contract, err = _grade_with_retry(
                (lambda _it=it, _age=age_tier: gc.grade_submission(
                    db,
                    passage_id=_it["source_passage_id"],
                    gold_l2=_it["reference"],
                    reproduction=_it["reproduction"],
                    l2_language_id=l2_language_id,
                    l1_language_id=l1_language_id,
                    age_tier=_age,
                    max_tier="tier2",
                    framework_v2=args.framework_v2,
                )),
                it["id"],
            )
            if contract is None:
                skip_entry = {"id": it["id"], "kind": it["kind"], "error": str(err)}
                skipped.append(skip_entry)
                _save_checkpoint(args.resume, skipped=skip_entry)
                print(f"[{idx}/{len(items)}] {it['id']} — SKIPPED (gave up): {err}")
                continue

            record = _build_record(it, contract, rubric_cfg, l2)
            records.append(record)
            _save_checkpoint(args.resume, record=record)
            gt = contract.get("grader_trace", {})
            print(f"[{idx}/{len(items)}] {it['id']} kind={it['kind']} "
                  f"pred_errors={len(contract['errors'])} tier={gt.get('tier')} "
                  f"fell_open={gt.get('fell_open')}")

    if skipped:
        print(f"[warn] {len(skipped)} item(s) skipped after retries: "
              f"{', '.join(s['id'] for s in skipped)}")

    # TASK-625: score severity against the MQM triad (minor/major/critical). Both
    # predicted (live grader) and expected (_exp_errors -> severity_v2) are now on
    # the 3-level scale, so within-one agreement carries real signal (on the old
    # 2-level scale every matched pair was trivially within one).
    metrics = em.aggregate_metrics(records, severity_order=em.SEVERITY_TRIAD_ORDER)
    metrics["v6"] = em.taxonomy_v6_metrics(records)  # TASK-849; additive, QWK untouched

    # Cost from recorded per-call tokens x OpenRouter pricing.
    try:
        pricing_map = arena_pricing.get_pricing_map()
    except Exception as exc:
        logger.warning("could not fetch pricing map (%s); cost will show 0", exc)
        pricing_map = {}
    cost = rec.total_cost(pricing_map)

    meta = {
        "date": _dt.date.today().isoformat(),
        "l1": l1,
        "slugs": rec.slugs,
        "tokens_in": rec.tokens_in,
        "tokens_out": rec.tokens_out,
        "n_calls": len(rec.calls),
        "cost": cost,
        "resumed": resumed_count,
        "skipped": [s["id"] for s in skipped],
        "framework_v2": args.framework_v2,
        "rubric_file": args.rubric_file,
        "fixture_set": args.fixture_set,
        "taxonomy_file": args.taxonomy_file,
        "taxonomy_version": cand_tax[0] if cand_tax else None,
        # Counted over this invocation's grading only (resumed items are not re-graded).
        "log_counts": dict(log_counter.counts),
    }

    report = _render_report(l2, metrics, meta)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)

    print(f"\n[done] wrote {args.out}")
    print(f"  span F1={_fmt(metrics['span']['f1'])}  "
          f"clean FP rate={_fmt(metrics['clean_fp']['item_fp_rate'])}  "
          f"overall QWK={_fmt(metrics['overall']['qwk'])}  cost=${cost:.4f}")
    print(f"  meaning_inversion recall={_fmt(metrics['v6']['meaning_inversion']['recall'])}  "
          f"exemplar drops={log_counter.counts['exemplar_drop']}  "
          f"no-template lines={log_counter.counts['no_explanation_template']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
