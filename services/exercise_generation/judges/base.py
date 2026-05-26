"""
Judge infrastructure — base types, thresholds, and verdict classifier.

All LLM judges in services.exercise_generation.judges import from here so
threshold changes propagate with a single edit and no redeploy of judge logic.

Verdict flow
------------
                       confidence
                           │
              ┌────────────┼────────────┐
              │            │            │
           < 0.6        0.6–0.8       ≥ 0.8
              │            │            │
           reject         flag        accept
       (sync block)  (persist,      (pass
                      enqueue)      through)

Failure-safe contract
---------------------
On any judge error (template missing, LLM call failure, malformed response)
the judge returns safe_accept() — the same "act as if the judge wasn't there"
contract used by cloze_judge.py.  The caller logs the error before delegating
to safe_accept.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


# ---------------------------------------------------------------------------
# Verdict thresholds — edit here to re-tune without touching judge logic.
# ---------------------------------------------------------------------------

THRESHOLD_ACCEPT: float = 0.8   # confidence >= THRESHOLD_ACCEPT → accept
THRESHOLD_REJECT: float = 0.6   # confidence <  THRESHOLD_REJECT → reject
                                 # in between → flag


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------

Verdict = Literal['accept', 'flag', 'reject']


@dataclass
class JudgeOutcome:
    """Result of a single judge evaluation.

    Attributes
    ----------
    verdict:    'accept' | 'flag' | 'reject'  (derived from confidence)
    confidence: raw 0.0–1.0 score reported by the LLM judge
    reason:     free-text explanation in the target language
    """
    verdict: Verdict
    confidence: float
    reason: str


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def classify(confidence: float) -> Verdict:
    """Map a raw 0.0–1.0 confidence score to a verdict string.

    Examples
    --------
    >>> classify(0.9)
    'accept'
    >>> classify(0.7)
    'flag'
    >>> classify(0.5)
    'reject'
    """
    if confidence >= THRESHOLD_ACCEPT:
        return 'accept'
    if confidence >= THRESHOLD_REJECT:
        return 'flag'
    return 'reject'


# ---------------------------------------------------------------------------
# Safe-default helper (mirrors cloze_judge.py pattern)
# ---------------------------------------------------------------------------

def safe_accept(reason: str = 'judge error – safe-default accept') -> JudgeOutcome:
    """Return an accept outcome for use when a judge fails unexpectedly.

    Failure mode is "act as if the judge wasn't there", not "drop all output".
    Callers must log the underlying error *before* calling this.
    """
    return JudgeOutcome(
        verdict='accept',
        confidence=THRESHOLD_ACCEPT,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Verdict observability helper
# ---------------------------------------------------------------------------

def log_judge_verdict(
    task_name: str,
    model: str,
    verdict: str,
    confidence: float,
    pipeline: str = 'test_gen',
) -> None:
    """Best-effort: write a compact verdict row to llm_calls.

    ``call_llm`` auto-logs the raw LLM round-trip with judge_verdict=NULL.
    This function writes a *second* row that carries the classified verdict
    and confidence, enabling the smoke-test query::

        SELECT task_name, COUNT(*) FILTER (WHERE judge_verdict='accept') ...
        FROM llm_calls
        WHERE task_name LIKE 'judge_%' AND judge_verdict IS NOT NULL

    to compute accept / flag / reject distributions without changing
    call_llm's internals.

    Never raises — verdict logging must never break the generation pipeline.
    """
    try:
        from services.supabase_factory import get_supabase_admin, get_supabase
        client = get_supabase_admin() or get_supabase()
        if client is None:
            return
        client.table('llm_calls').insert({
            'pipeline': pipeline,
            'task_name': task_name,
            'model': model,
            'judge_verdict': verdict,
            'judge_confidence': confidence,
        }).execute()
    except Exception:
        pass
