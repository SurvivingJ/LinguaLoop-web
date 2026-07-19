"""Dual Translation — nightly error synthesis (TASK-610).

Pure clustering + promotion logic for the error-profile pipeline. It reads
already-graded ``dt_error_instance`` rows (produced by Feature 1's grading
cascade) and turns them into ``dt_error_profile_entry`` upserts.

No embeddings and no LLM calls: the grader already emits a structured taxonomy
``subtype`` for every error, so clustering is a *deterministic group-by* on
``(user_id, l1↔l2 pair, subtype)``. All LLM spend stays in grading (see
[[features/dual-translation-remediation.tech]] §Key Architectural Decision 2).

Everything here is a pure function over plain dicts, so the whole pipeline is
testable with no DB. The DB + CLI wiring lives in
``scripts/dt_nightly_synthesis.py``.

Pipeline ([[features/dual-translation-remediation.tech]] §Pipeline):
  1. mistake gate — drop ``is_mistake=True`` (self-corrected / one-off slips;
     Corder's error-vs-mistake distinction). A *mistake* NEVER promotes.
  2. cluster       — group-by ``(user_id, l1_language_id, l2_language_id,
     subtype)``. Deterministic; no embedding/LLM re-read.
  3. promote       — a subtype crosses into ``queued`` only on recurrence >= N
     inside window W (or a proceduralization gap). N / W are tunable config.
  4. profile       — emit the ``dt_error_profile_entry`` upsert row: ``count``,
     ``severity_rank`` (frequency × severity), ``trend``, ``remediation_status``.
"""

from collections import defaultdict
from datetime import datetime, timedelta

# Severity weights for the MQM triad (dt_severity_triad.sql / TASK-625). The
# legacy pre-triad global/local vocabulary is mapped defensively so a row that
# predates the backfill still ranks sanely rather than defaulting to 1.0.
DEFAULT_SEVERITY_WEIGHTS: dict[str, float] = {
    "minor": 1.0,
    "major": 2.0,
    "critical": 3.0,
    # legacy (pre-TASK-625) — local ≈ minor, global ≈ major
    "local": 1.0,
    "global": 2.0,
}

# The DB CHECK on dt_error_profile_entry.remediation_status.
STATUS_WATCHING = "watching"
STATUS_QUEUED = "queued"
STATUS_DRILLING = "drilling"
STATUS_RESOLVED = "resolved"

# An error "record" is a plain dict with these keys (dt_error_instance joined to
# its dt_submission / dt_passage):
#   user_id: str (uuid)      l1_language_id: int   l2_language_id: int
#   subtype: str             severity: str         is_mistake: bool
#   created_at: datetime (timezone-aware)
ClusterKey = tuple[str, int, int, str]


def cluster_key(error: dict) -> ClusterKey:
    """The deterministic cluster identity for one error record."""
    return (
        error["user_id"],
        error["l1_language_id"],
        error["l2_language_id"],
        error["subtype"],
    )


def gate_mistakes(errors: list[dict]) -> list[dict]:
    """Drop ``is_mistake=True`` rows.

    Corder: a *mistake* is a one-off performance slip the learner can
    self-correct; only systematic *errors* are worth drilling. A gated mistake
    can never contribute to a cluster's ``count`` and therefore can never
    promote — this is the acceptance-criterion guarantee.
    """
    return [e for e in errors if not e.get("is_mistake", False)]


def cluster_errors(errors: list[dict]) -> dict[ClusterKey, list[dict]]:
    """Group errors by ``(user, l1, l2, subtype)`` — a plain deterministic
    group-by. No embedding, no LLM, no similarity threshold."""
    clusters: dict[ClusterKey, list[dict]] = defaultdict(list)
    for e in errors:
        clusters[cluster_key(e)].append(e)
    return dict(clusters)


def severity_rank(errors: list[dict], weights: dict[str, float] | None = None) -> float:
    """Frequency × severity, as the sum of per-error severity weights.

    The sum equals ``count × mean(severity_weight)``, so it grows with BOTH how
    often the subtype recurs and how bad each instance is: a cluster containing
    a ``critical`` outranks an equally frequent all-``minor`` cluster (global
    errors rank first — [[business-rules/translation-error-taxonomy]]).
    """
    weights = weights or DEFAULT_SEVERITY_WEIGHTS
    return float(sum(weights.get(e["severity"], 1.0) for e in errors))


def meets_promotion_threshold(
    count: int, *, threshold: int, proceduralization_gap: bool = False
) -> bool:
    """A subtype promotes on recurrence >= N in window W, OR on a
    proceduralization gap (correct when attention is drawn, wrong under load).

    The gap signal needs delayed re-test data that only exists once remediation
    cards ship (TASK-613/614); until then it is always ``False`` and promotion
    is recurrence-only. ``is_mistake`` rows are already gone before this is
    called, so a mistake can never make ``count`` reach the threshold.
    """
    return count >= threshold or proceduralization_gap


def decide_status(existing_status: str | None, *, meets_threshold: bool) -> str:
    """State machine for ``remediation_status`` — monotonic toward remediation.

    - Never regress an in-flight (``drilling``) or finished (``resolved``) row:
      those are owned by the card/review pipeline (TASK-613+), not by nightly
      re-counting.
    - ``watching`` → ``queued`` when the threshold is met.
    - Once ``queued``, stay ``queued`` (awaiting card generation) even if this
      particular window happens to be quiet — don't demote a pending promotion.
    - Otherwise ``watching``.
    """
    if existing_status in (STATUS_DRILLING, STATUS_RESOLVED):
        return existing_status
    if meets_threshold:
        return STATUS_QUEUED
    if existing_status == STATUS_QUEUED:
        return STATUS_QUEUED
    return STATUS_WATCHING


def build_trend(
    *, current_count: int, prev_count: int, window_days: int, now: datetime
) -> dict:
    """Minimal trend payload for the self-regulation dashboard (TASK-611).

    Records this window's count against the previous window's so the dashboard
    can render "article errors down 40% this month" without re-querying history.
    ``delta_pct`` is signed (negative = improving); ``None`` when there is no
    prior-window baseline to compare against.
    """
    delta_pct = None
    if prev_count > 0:
        delta_pct = round((current_count - prev_count) / prev_count * 100.0, 1)
    return {
        "window_days": window_days,
        "as_of": now.isoformat(),
        "current_count": current_count,
        "previous_count": prev_count,
        "delta_pct": delta_pct,
    }


def synthesize(
    errors: list[dict],
    existing_status: dict[ClusterKey, str] | None = None,
    *,
    now: datetime,
    window_days: int,
    threshold: int,
    severity_weights: dict[str, float] | None = None,
    proceduralization_gaps: dict[ClusterKey, bool] | None = None,
) -> list[dict]:
    """Turn a flat list of error records into ``dt_error_profile_entry`` upserts.

    Args:
        errors: ``dt_error_instance`` records joined to their submission/passage.
            Should span the last TWO windows (``2 × window_days``) so the
            previous-window trend baseline can be computed; anything older is
            ignored.
        existing_status: ``{ClusterKey: remediation_status}`` for rows already in
            ``dt_error_profile_entry``, so an in-flight/resolved status is never
            regressed by a re-count.
        now: the run timestamp (timezone-aware); defines the window boundaries.
        window_days: W — the rolling window length in days.
        threshold: N — recurrences within W required to promote to ``queued``.
        severity_weights: override for the MQM severity → weight map.
        proceduralization_gaps: ``{ClusterKey: True}`` override for the
            proceduralization-gap promotion path (future TASK-614 signal).

    Returns:
        One upsert-ready dict per cluster *observed in the current window*, in a
        deterministic (sorted-key) order. Each dict is keyed by
        ``(user_id, l1_language_id, l2_language_id, subtype)`` — the
        ``dt_error_profile_entry`` UNIQUE constraint.

    Note:
        Clusters with no errors in the current window are not emitted, so a
        subtype that has gone quiet keeps its last-written row (no decay). Decay
        of stale ``watching`` rows is a deliberate future refinement.
    """
    existing_status = existing_status or {}
    proceduralization_gaps = proceduralization_gaps or {}
    weights = severity_weights or DEFAULT_SEVERITY_WEIGHTS

    survivors = gate_mistakes(errors)
    current_cutoff = now - timedelta(days=window_days)
    previous_cutoff = now - timedelta(days=2 * window_days)

    current = [e for e in survivors if e["created_at"] > current_cutoff]
    previous = [
        e for e in survivors if previous_cutoff < e["created_at"] <= current_cutoff
    ]

    current_clusters = cluster_errors(current)
    previous_counts = {k: len(v) for k, v in cluster_errors(previous).items()}

    rows: list[dict] = []
    for key in sorted(current_clusters):  # deterministic emission order
        user_id, l1_language_id, l2_language_id, subtype = key
        members = current_clusters[key]
        count = len(members)
        promoted = meets_promotion_threshold(
            count,
            threshold=threshold,
            proceduralization_gap=proceduralization_gaps.get(key, False),
        )
        rows.append(
            {
                "user_id": user_id,
                "l1_language_id": l1_language_id,
                "l2_language_id": l2_language_id,
                "subtype": subtype,
                "count": count,
                "severity_rank": severity_rank(members, weights),
                "trend": build_trend(
                    current_count=count,
                    prev_count=previous_counts.get(key, 0),
                    window_days=window_days,
                    now=now,
                ),
                "remediation_status": decide_status(
                    existing_status.get(key), meets_threshold=promoted
                ),
                "updated_at": now.isoformat(),
            }
        )
    return rows
