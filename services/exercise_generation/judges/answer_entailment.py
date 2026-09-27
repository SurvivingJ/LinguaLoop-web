"""
Answer entailment judge.

Verifies that the passage actually supports the proposed correct answer.
Catches the "answer hallucination" failure mode that Pydantic schema
validation cannot catch — the model invents a correct answer that the
passage does not actually state or imply.

Usage::

    from services.exercise_generation.judges.answer_entailment import (
        judge_answer_entailment,
    )
    outcome = judge_answer_entailment(
        db=db,
        passage="...",
        question_text="What did the author say about X?",
        answer="Y",
        language_id=2,
    )
    # outcome.verdict in ('accept', 'flag', 'reject')
    # outcome.confidence  — the 1-5 Likert rating, as a float
    # outcome.reason      — explanation in the target language

Scale (v2, TASK-723)
--------------------
This judge used to return a raw 0.0-1.0 confidence classified by
``base.classify``. It now returns the same 5-point Likert rating the distractor
judge uses, mapped by ``schemas.likert_to_verdict``:

    5  stated explicitly in the passage          → accept
    4  not stated, but uniquely inferable        → accept
    3  partially supported; another answer fits  → flag  (persist + enqueue)
    2  unsupported; merely on the same topic     → reject
    1  contradicted by the passage, or unrelated → reject

Why: ``llm_calls.judge_confidence`` is one column holding two scales that
*invert* — a stored ``1.0`` meant "maximum confidence, accept" here and "worst
rating, reject" on the Likert judges. Nothing could tell them apart, which is
why ``migrations/null_legacy_judge_confidence.sql`` had to erase 888 rows.
Entailment is the easy conversion because "does the passage support this
answer" is naturally a single axis, so its bands can be mutually exclusive
without the two-axis redesign TASK-719 owes the distractor judge.

``cloze_distractor_judge`` is still on the float scale and still calls
``base.classify``; until it converts, judge_confidence is consistent per
task_name but not globally.

Backends (ENTAILMENT_JUDGE_BACKEND)
-----------------------------------
``llm``     the Likert judge above, unchanged. The rollback:
            ``ENTAILMENT_JUDGE_BACKEND=llm``.
``jev``     (default since 2026-09-27, TASK-835) ``typesafe/jev-1.13`` answers one yes/no question and returns
            P(yes), mapped to the same accept/flag/reject verdict by per-language
            cutoffs (``answer_entailment_jev``). If jev cannot answer, the LLM
            judge runs instead; only if that also fails does the usual
            ``safe_accept`` contract apply (raises ``JudgeUnavailable`` in
            ``batch_mode()``, fails open when serving).
``shadow``  the LLM verdict is returned; jev also runs and its verdict is logged
            under ``judge_answer_entailment_shadow`` for offline comparison. jev
            can never change the outcome or raise in this mode.

The variable is read on every call, so it can be flipped without a restart. jev
outcomes carry ``confidence=None`` and ``probability=P(yes)``: the probability
must not share the 1-5 ``judge_confidence`` column with Likert ratings.

Cutover safety
--------------
This code only works against a v3+ ``prompt_templates`` row. ``_is_pre_likert``
checks that before the LLM call and refuses to judge on an older row, because
the mismatch is *not* self-announcing: a legacy row's most common answer is
``1.0``, which is a structurally valid Likert ``1`` and would invert into a
hard reject. Deploy this code first, then activate the v3 rows, then restart —
``_cfg_cache`` is process-lifetime, so flipping ``is_active`` does not reach a
process that has already judged in that language.
"""

from __future__ import annotations

import json
import logging
import os

from services.llm_service import call_llm
from services.prompt_service import get_template_config

from services.test_generation.schemas import (
    AnswerEntailmentVerdict,
    likert_to_verdict,
)
from . import answer_entailment_jev
from .base import JudgeOutcome, accept_item, safe_accept, log_judge_verdict

logger = logging.getLogger(__name__)

_TASK_NAME = 'judge_answer_entailment'   # label in llm_calls (judge_ prefix)
_SHADOW_TASK_NAME = 'judge_answer_entailment_shadow'  # kept apart so the live
                                         # accept/flag/reject distribution stays clean
_PT_NAME   = 'test_answer_entailment'    # task_name in prompt_templates
_PIPELINE  = 'test_gen'

# language_id → llm_calls.language_code. Same hardcoded map used by
# services/corpus/ingestion.py and services/exercise_generation/difficulty.py
# — a DB-cached lookup (DimensionService) needs an app-startup init this
# judge cannot rely on, and the id space is small and stable.
_LANG_ID_TO_CODE: dict[int, str] = {1: 'zh', 2: 'en', 3: 'ja'}

# First prompt_templates version that asks for a 1-5 Likert rating. Every
# earlier row asks for a 0.0-1.0 confidence and is incompatible with this code
# — see _is_pre_likert.
_MIN_LIKERT_VERSION = 3

# Measurement hook (TASK-833): when set, called as
# ``observer(passage, question_text, answer, language_id, live_outcome, jev_verdict)``
# after every successful shadow evaluation, so a shadow-window script can keep the
# text of each comparison (llm_calls stores verdicts only). An observer that raises
# is logged and ignored -- like the rest of shadow mode it cannot affect a batch.
shadow_observer = None

_BACKEND_ENV = 'ENTAILMENT_JUDGE_BACKEND'
_BACKENDS = ('llm', 'jev', 'shadow')
DEFAULT_BACKEND = 'jev'     # TASK-835: flipped from 'llm' on 2026-09-27 at the operator's
                            # explicit instruction. Rollback: ENTAILMENT_JUDGE_BACKEND=llm

_cfg_cache: dict[int, dict] = {}         # language_id → cfg dict


def _backend() -> str:
    """Active backend, read per call.

    Unset or blank means ``DEFAULT_BACKEND``. An unrecognised value falls to
    ``llm`` (loudly) rather than the default: a typo should land on the
    long-proven judge, not on the newer one.
    """
    raw = os.environ.get(_BACKEND_ENV, '').strip().lower() or DEFAULT_BACKEND
    if raw not in _BACKENDS:
        logger.warning(
            "answer_entailment: %s=%r is not one of %s; using 'llm'",
            _BACKEND_ENV, raw, _BACKENDS,
        )
        return 'llm'
    return raw


def _is_pre_likert(version) -> bool:
    """True when the active prompt row is known to predate the Likert scale.

    This is the *primary* guard against running v3 code against a pre-v3 row,
    and it keys off the version because the returned **value cannot tell you**.
    The two scales overlap at 1, where they mean opposite things, and a legacy
    row's best-case answer is exactly ``1.0``: measured over 391 historical
    responses in ``llm_calls.raw_response``, 77% were ``1.0``. Those parse to a
    valid Likert ``1``, so ``schemas._reject_legacy_float_scale`` waves them
    through and ``likert_to_verdict`` turns "maximum confidence, accept" into a
    hard reject. Only the remaining 23% (fractional floats such as 0.85) are
    detectable from the value.

    Unknown / non-numeric versions return False rather than blocking: in
    production ``get_template_config`` always returns the integer from the row,
    so an unusable value means a test double, and the schema-level check still
    backstops the fractional case.
    """
    try:
        return int(version) < _MIN_LIKERT_VERSION
    except (TypeError, ValueError):
        return False


def judge_answer_entailment(
    db,
    passage: str,
    question_text: str,
    answer: str,
    language_id: int,
) -> JudgeOutcome:
    """Run the answer-entailment judge and return a single JudgeOutcome.

    Dispatches on ``ENTAILMENT_JUDGE_BACKEND`` (see the module docstring). On
    any error the result is ``safe_accept()`` -- failure mode is "let it
    through", not "block the whole pipeline" -- except inside ``batch_mode()``,
    where ``safe_accept`` raises ``JudgeUnavailable`` instead.
    """
    backend = _backend()
    if backend == 'jev':
        try:
            return _judge_jev(passage, question_text, answer, language_id)
        except Exception as exc:  # noqa: BLE001 -- any jev failure -> LLM judge
            logger.warning(
                "answer_entailment: jev backend failed for lang=%d, "
                "falling back to the LLM judge: %s", language_id, exc,
            )
    outcome = _judge_llm(db, passage, question_text, answer, language_id)
    if backend == 'shadow':
        _shadow_jev(passage, question_text, answer, language_id, outcome)
    return outcome


def _judge_jev(
    passage: str, question_text: str, answer: str, language_id: int,
) -> JudgeOutcome:
    """The jev backend. Raises on any failure so the caller can fall back."""
    jv = answer_entailment_jev.evaluate(
        passage, question_text, answer, language_id,
        task_name=_TASK_NAME, pipeline=_PIPELINE,
    )
    outcome = JudgeOutcome(
        verdict=jv.verdict,
        confidence=None,                 # never a probability in the 1-5 column
        reason=jv.reason,
        probability=jv.probability,
        backend='jev',
    )
    log_judge_verdict(
        task_name=_TASK_NAME, model=jv.model, verdict=outcome.verdict,
        confidence=None, pipeline=_PIPELINE,
    )
    return outcome


def _shadow_jev(
    passage: str, question_text: str, answer: str, language_id: int,
    live: JudgeOutcome,
) -> None:
    """Run jev alongside the authoritative LLM verdict and log both.

    Never raises and never touches ``live``: a shadow that could fail a batch
    would defeat the point of shadowing. The row's raw_response holds both
    verdicts so the comparison is one query, no join.
    """
    try:
        jv = answer_entailment_jev.evaluate(
            passage, question_text, answer, language_id,
            task_name=_SHADOW_TASK_NAME, pipeline=_PIPELINE,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "answer_entailment shadow: jev failed for lang=%d: %s", language_id, exc,
        )
        return
    if shadow_observer is not None:
        try:
            shadow_observer(passage, question_text, answer, language_id, live, jv)
        except Exception as exc:  # noqa: BLE001
            logger.warning("answer_entailment shadow: observer failed: %s", exc)
    try:
        from services.llm_service import _log_llm_call
        _log_llm_call(
            pipeline=_PIPELINE, task_name=_SHADOW_TASK_NAME, template_version=None,
            model=jv.model, temperature=None, seed=None, prompt_hash=None,
            raw_response=json.dumps({
                'p_yes': jv.probability,
                'jev_verdict': jv.verdict,
                'live_verdict': live.verdict,
                'live_rating': live.confidence,
            }),
            parsed_ok=True, schema_ok=True,
            judge_verdict=jv.verdict, judge_confidence=None,
            latency_ms=None, artifact_id=None, cost_usd=None,
            language_code=_LANG_ID_TO_CODE.get(language_id), provider='TypeSafe',
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("answer_entailment shadow: verdict logging failed: %s", exc)


def _judge_llm(
    db,
    passage: str,
    question_text: str,
    answer: str,
    language_id: int,
) -> JudgeOutcome:
    """The LLM (Likert) backend.

    On any error (missing template, LLM failure, schema validation error)
    returns ``safe_accept()`` and logs a warning — failure mode is "let it
    through", not "block the whole pipeline".
    """
    try:
        cfg = _load_cfg(db, language_id)
    except Exception as exc:
        logger.warning(
            "answer_entailment: failed to load template for lang=%d, safe-accept: %s",
            language_id, exc,
        )
        return safe_accept(f'template load error: {exc}')

    # Prompt and code are coupled and must cut over together. Refuse *before*
    # spending the LLM call: a pre-v3 row answers on the inverted scale, and
    # judging on it would reject the answers it is most confident about.
    if _is_pre_likert(cfg.get('version')):
        reason = (
            f'prompt_templates row for {_PT_NAME}/lang={language_id} is '
            f'v{cfg.get("version")}, which asks for a 0.0-1.0 confidence, but '
            f'this code reads a 1-5 Likert rating (v{_MIN_LIKERT_VERSION}+). '
            f'Activate the v{_MIN_LIKERT_VERSION} rows from '
            f'migrations/entailment_likert_v2.sql and restart '
            f'(the cfg cache is process-lifetime).'
        )
        logger.error('answer_entailment: %s Refusing to judge.', reason)
        return safe_accept(reason)

    prompt = cfg['template'].format(passage, question_text, answer)

    try:
        verdict_obj: AnswerEntailmentVerdict = call_llm(
            prompt,
            model=cfg['model'],
            temperature=0.0,
            response_format='json_object',
            schema=AnswerEntailmentVerdict,
            provider='openrouter',
            pipeline=_PIPELINE,
            task_name=_TASK_NAME,
            template_version=cfg['version'],
            language_code=_LANG_ID_TO_CODE.get(language_id),
        )
    except Exception as exc:
        logger.warning(
            "answer_entailment: LLM call failed for lang=%d, safe-accept: %s",
            language_id, exc,
        )
        return safe_accept(f'llm call error: {exc}')

    # A judge that answered but gave no usable rating must not manufacture a
    # rejection — same contract as the distractor judge's per-item gaps. This is
    # `accept_item`, not `safe_accept`: the judge itself is healthy, so a
    # generation batch must NOT abort over one unparseable rating.
    if verdict_obj.rating is None:
        return accept_item(
            f'entailment judge returned no rating: {verdict_obj.reason}'
        )

    outcome = JudgeOutcome(
        verdict=likert_to_verdict(verdict_obj.rating),
        confidence=float(verdict_obj.rating),  # carries the 1-5 Likert rating
        reason=verdict_obj.reason,
    )

    # Write a compact verdict row so the smoke-test can count
    # accept/flag/reject distributions by task_name LIKE 'judge_%'.
    log_judge_verdict(
        task_name=_TASK_NAME,
        model=cfg['model'],
        verdict=outcome.verdict,
        confidence=outcome.confidence,
        pipeline=_PIPELINE,
    )

    return outcome


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _load_cfg(db, language_id: int) -> dict:
    if language_id not in _cfg_cache:
        _cfg_cache[language_id] = get_template_config(db, _PT_NAME, language_id)
    return _cfg_cache[language_id]
