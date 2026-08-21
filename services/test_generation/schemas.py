"""
Test Generation — Pydantic schemas

Schemas for LLM-structured outputs in the test generation pipeline.
Use these as the `schema=` argument to services.llm_service.call_llm to
get post-validation + one-shot repair retry behaviour.
"""

from __future__ import annotations

from typing import Any, NamedTuple, Optional

from pydantic import BaseModel, field_validator, model_validator


# Fallback used when a judge dumps a bare score (e.g. "0.1") or an empty string
# into a reason field. A real sentence keeps the regen `avoid_context` feedback
# usable instead of poisoning it with "rejected: 0.1".
_REASON_FALLBACK = '(no reason provided by judge)'


def _clean_reason(r: Any) -> str:
    """Coerce a judge reason to a non-empty sentence.

    The judge model intermittently emits a bare number (a duplicated score)
    or an empty string where a reason belongs. Both are useless as regen
    feedback, so they are replaced with a deterministic fallback sentence.
    """
    s = str(r).strip()
    if not s:
        return _REASON_FALLBACK
    try:
        float(s)  # a bare number is a leaked score, not a reason
    except ValueError:
        return s
    return _REASON_FALLBACK


# v3 distractor-plausibility judge: the judge now emits a 5-point Likert RATING
# per distractor instead of a raw 0.0-1.0 float. Code maps the rating to a
# verdict here so the cut points are tunable without re-prompting:
#   5, 4 -> accept    3 -> flag (weak, keep + surface)    2, 1 -> reject
# (2 = off-topic / different subject, 1 = also-correct or absurd). This replaces
# base.classify() for that judge only; answer-entailment keeps its float.
LIKERT_TO_VERDICT: dict[int, str] = {
    5: 'accept', 4: 'accept', 3: 'flag', 2: 'reject', 1: 'reject',
}


def likert_to_verdict(rating: int | None) -> str:
    """Map a 1-5 Likert rating to 'accept' | 'flag' | 'reject'.

    ``None`` means the judge returned NO rating for this item — not a weak one.
    Callers should handle that case before reaching here (see
    ``judges.base.accept_item``); it maps to 'accept' as a backstop so an
    absent rating can never manufacture a rejection or a spurious review-queue
    entry. Out-of-range values keep the historic 'flag' default: this helper is
    shared by seven judges and only the None branch is new.
    """
    if rating is None:
        return 'accept'
    return LIKERT_TO_VERDICT.get(int(rating), 'flag')


# ---------------------------------------------------------------------------
# Distractor plausibility: two axes (TASK-719), and the review band (TASK-720)
# ---------------------------------------------------------------------------
#
# The v4/v6 distractor prompt asks for ONE 1-5 rating that is secretly answering
# two unrelated questions at once — "is this option about the right subject?" and
# "would a learner confuse it with the correct answer?" Those come apart in both
# directions: an off-subject option can still be tempting, and a perfectly
# on-subject one can be so obviously wrong that no learner would ever pick it.
# One integer cannot say which failure it saw, so neither could the review queue.
#
# v7 asks for the two ratings separately and the verdict arithmetic moves here,
# where the cut points are named constants instead of prose in three languages:
#
#   fit            5  clearly the passage's subject
#                  4  plausibly within it
#                  3  NOT CONFIDENT  (review)
#                  2  clearly a different subject
#                  1  not a coherent answer option at all
#
#   confusability  5  also correct, or indistinguishable from the answer (DEFECT)
#                  4  strongly tempting but definitely wrong  (the target)
#                  3  NOT CONFIDENT  (review)
#                  2  mildly tempting
#                  1  no learner would pick it — inert
#
# `confusability` is deliberately NOT monotone in quality: 4 is the goal and 5 is
# a defect, because an option a learner cannot tell apart from the answer breaks
# the question. Encoding that in a single ordinal is exactly what v4 tried and
# failed to do, and it is why the arithmetic belongs in Python.
#
# Band 3 is the review band on BOTH axes and now means "the judge is not
# confident" (TASK-720). It previously named one narrow defect — "essentially a
# paraphrase of the correct answer" — that no model applied as written: all four
# English flags in the 2026-08-16 baseline were something else, while `gemini`
# was already using 3 as a generic "unsure", which is what a review queue
# actually wants. The definition now matches the observed behaviour, and
# `axes_to_verdict` reports WHICH axis was unsure so the queue row can record it.
#
# BACKWARD COMPATIBILITY, and it is load-bearing. `fit`'s bands are deliberately
# identical to the v4 single-axis bands (5/4 accept, 3 flag, 2/1 reject). A v4 or
# v6 row returns one rating per distractor, which lands in `fit` with
# `confusability` None, and a None axis can never manufacture a verdict — so this
# code returns byte-identical verdicts against the rows that are live today.
# Unlike the entailment cutover (TASK-723) the two scales do not invert at any
# point and no version gate is needed: deploy the code first, activate the v7
# rows whenever the measurement says to.

AXIS_FIT = 'fit'
AXIS_CONFUSABILITY = 'confusability'
AXES: tuple[str, str] = (AXIS_FIT, AXIS_CONFUSABILITY)

#: Band reserved on every axis for "the judge is not confident" -> human review.
REVIEW_BAND: int = 3
#: fit <= this is a different subject (2) or not an option at all (1) -> reject.
FIT_REJECT_MAX: int = 2
#: confusability >= this is also-correct / indistinguishable -> reject. This is
#: the failure the single-axis scale put in band 1, which fired 3 times in 1,800
#: ratings; it gets its own axis here precisely because it was undetectable.
CONFUSABILITY_ALSO_CORRECT: int = 5
#: confusability <= this is inert — a real, on-subject option nobody would pick.
#: FLAG, not reject: v4 scored these 4 and accepted them, so rejecting outright
#: would be a scale change rather than a scale split, and the queue volume this
#: adds has to be measured before anyone decides it is worth paying. See
#: wiki/evaluations/distractor-judge-two-axis-2026-08-20.
CONFUSABILITY_INERT_MAX: int = 1

_VERDICT_RANK: dict[str, int] = {'reject': 0, 'flag': 1, 'accept': 2}


class AxisVerdict(NamedTuple):
    """The combined verdict for one distractor, and what drove it.

    ``axes`` names every axis whose own verdict equals the combined one, in
    ``AXES`` order — empty on an accept, because nothing triggered. ``rating``
    is the band on the first such axis (the *binding* axis), or, on an accept,
    ``fit`` when present and ``confusability`` otherwise. It is what lands in
    ``llm_calls.judge_confidence``: still a 1-5 Likert integer, but read it
    together with ``judge_verdict`` on the same row, because a 5 means "clearly
    on-subject, accept" when fit binds and "also correct, reject" when
    confusability does.
    """
    verdict: str
    axes: tuple[str, ...]
    rating: int | None


def fit_to_verdict(fit: int | None) -> str:
    """Verdict contribution of the topical-fit axis alone.

    Identical to ``likert_to_verdict`` by construction — see the backward
    compatibility note above; a v4 row's single rating is read as ``fit``.
    """
    if fit is None:
        return 'accept'
    if fit <= FIT_REJECT_MAX:
        return 'reject'
    if fit == REVIEW_BAND:
        return 'flag'
    return 'accept'


def confusability_to_verdict(confusability: int | None) -> str:
    """Verdict contribution of the confusability axis alone.

    Non-monotone on purpose: both ends are defects. The top (5) is a distractor
    that is also correct — reject. The bottom (1) is a distractor no learner
    would ever pick — flag, not reject, because it is a *weak question*, not a
    broken one, and v4 accepted it outright.
    """
    if confusability is None:
        return 'accept'
    if confusability >= CONFUSABILITY_ALSO_CORRECT:
        return 'reject'
    if confusability == REVIEW_BAND:
        return 'flag'
    if confusability <= CONFUSABILITY_INERT_MAX:
        return 'flag'
    return 'accept'


def axes_to_verdict(
    fit: int | None,
    confusability: int | None,
) -> AxisVerdict:
    """Map the two per-distractor axes to one verdict, naming what drove it.

    The worst per-axis verdict wins. ``None`` on an axis means the judge gave no
    rating on it — not a weak one — and contributes 'accept', so a missing
    rating can never manufacture a rejection or a spurious review-queue entry.
    Both ``None`` therefore accepts; callers detect that case earlier and route
    it through ``judges.base.accept_item`` so the outcome carries no fabricated
    score at all.
    """
    per = (
        (AXIS_FIT, fit, fit_to_verdict(fit)),
        (AXIS_CONFUSABILITY, confusability, confusability_to_verdict(confusability)),
    )
    verdict = min((v for _, _, v in per), key=lambda v: _VERDICT_RANK[v])
    axes = tuple(name for name, _, v in per if v == verdict) if verdict != 'accept' else ()
    if axes:
        rating = next(r for name, r, _ in per if name == axes[0])
    else:
        rating = fit if fit is not None else confusability
    return AxisVerdict(verdict=verdict, axes=axes, rating=rating)


class TopicTranslation(BaseModel):
    """Translated topic + keyword list returned by the topic_translator agent.

    The prompt asks for `{"topic": str, "keywords": list[str]}`. Keywords are
    accepted as either a list of strings or a comma-separated string (model
    sometimes returns the latter); the normaliser coerces both to a list.
    Empty / missing keywords are tolerated — they default to an empty list.
    """
    topic: str
    keywords: list[str] = []

    @model_validator(mode='before')
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        kws = out.get('keywords')
        if isinstance(kws, str):
            out['keywords'] = [k.strip() for k in kws.split(',') if k.strip()]
        elif kws is None:
            out['keywords'] = []
        return out


class TranscriptResponse(BaseModel):
    """Wrapper for the legacy `transcript_generation` prompt output.

    The prompt asks for `{"transcript": "...", "difficulty_level": N}`.
    Using a schema here means call_llm's JSON path handles markdown fences,
    BOM, and stray prose around the JSON — eliminating the brittle
    `if transcript.startswith('{') and transcript.endswith('}')` check.
    """
    transcript: str
    difficulty_level: Optional[int] = None


class MCQuestion(BaseModel):
    """A multiple-choice reading/listening comprehension question.

    The LLM is asked to return one of two shapes — the active DB-templated
    shape (`question_text`/`choices`/`answer`/`explanation`) or the legacy
    numeric-key fallback (`1`/`2`/`3`/`4`/`5`). The validator below normalises
    both to the canonical fields and rejects the call (triggering call_llm's
    one-shot repair retry) when:

      * `choices` is not a length-4 list of distinct non-empty strings, or
      * `answer` (after letter-index promotion: A/B/C/D -> choices[i]) does
        not match any item in `choices`.

    Successful validation populates `correct_answer_index` as the canonical
    pointer to the correct option, eliminating the silent-corruption mode in
    the old parser (which fell back to choices[0] on any mismatch).
    """

    question_text: str
    choices: list[str]
    answer: str
    correct_answer_index: int
    explanation: Optional[str] = None
    distractor_types: Optional[list[Optional[str]]] = None

    @model_validator(mode='before')
    @classmethod
    def _normalize_and_validate(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Accept any of the variant key names the prompts emit.
        aliases = {
            '1': 'question_text', 'Question': 'question_text', 'question': 'question_text',
            '2': 'choices',       'Options': 'choices',        'options': 'choices',
            '3': 'answer',        'Answer': 'answer',          'correct_answer': 'answer',
            'rationale': 'explanation',
            '5': 'distractor_types',
        }
        normalized: dict[str, Any] = {}
        for k, v in data.items():
            normalized[aliases.get(k, k)] = v

        # --- choices ----------------------------------------------------------
        choices = normalized.get('choices')
        if not isinstance(choices, list):
            raise ValueError("choices must be a list")
        if len(choices) != 4:
            raise ValueError(f"choices must have exactly 4 items, got {len(choices)}")
        cleaned = [str(c).strip() for c in choices]
        if any(not c for c in cleaned):
            raise ValueError("choices must all be non-empty after strip")
        if len({c.lower() for c in cleaned}) != 4:
            raise ValueError("choices must be distinct (case-insensitive)")
        normalized['choices'] = cleaned

        # --- answer -----------------------------------------------------------
        answer = normalized.get('answer')
        if not isinstance(answer, str):
            raise ValueError("answer must be a string")
        answer_stripped = answer.strip()
        if not answer_stripped:
            raise ValueError("answer is empty")

        # Letter-index promotion: model sometimes returns "A"/"B"/"C"/"D".
        if answer_stripped in ('A', 'B', 'C', 'D'):
            answer_stripped = cleaned[ord(answer_stripped) - ord('A')]

        if answer_stripped not in cleaned:
            raise ValueError(
                f"answer {answer_stripped!r} not in choices {cleaned!r}"
            )

        normalized['answer'] = answer_stripped
        correct_index = cleaned.index(answer_stripped)
        normalized['correct_answer_index'] = correct_index

        # --- distractor_types -------------------------------------------------
        # When present it must align 1:1 with choices: exactly 4 entries, with
        # the correct choice's slot null (it is not a distractor). A short/long
        # list silently corrupts the per-choice tagging, so reject it (which
        # triggers call_llm's one-shot repair retry).
        dt = normalized.get('distractor_types')
        if dt is not None:
            if not isinstance(dt, list):
                raise ValueError("distractor_types must be a list")
            if len(dt) != 4:
                raise ValueError(
                    f"distractor_types must have 4 entries, got {len(dt)}"
                )
            if dt[correct_index] is not None:
                raise ValueError(
                    f"distractor_types[{correct_index}] (the correct choice) "
                    f"must be null, got {dt[correct_index]!r}"
                )

        return normalized


# ---------------------------------------------------------------------------
# Judge verdict schemas (Wave 2)
# ---------------------------------------------------------------------------

class AnswerEntailmentVerdict(BaseModel):
    """Judge output: how strongly does the passage support the correct answer?

    v2 (TASK-723) replaces the raw 0.0-1.0 confidence with the same 5-point
    Likert rating the distractor judge uses, so ``llm_calls.judge_confidence``
    carries one scale instead of two mutually inverting ones — see
    ``migrations/null_legacy_judge_confidence.sql`` for the collision that forced
    888 rows to be erased. Bands are a single axis (strength of textual support)
    and are mutually exclusive:

        5  stated explicitly in the passage
        4  not stated, but uniquely inferable from it
        3  partially supported — the passage also permits a different answer
        2  unsupported; merely on the same topic
        1  contradicted by the passage, or unrelated to it

    ``likert_to_verdict`` maps 5/4 → accept, 3 → flag, 2/1 → reject.

    The judge prompt uses numeric keys so the prompt body can be authored
    entirely in the target language (no English field names leak into ZH/JA
    prompts).  ``_normalize`` maps both the numeric-key shape returned by
    non-English prompts and the named-key shape the English prompt may return:

        {"1": 4, "2": "reasoning text"}     → rating=4, reason="..."
        {"rating": 4, "reason": "..."}      → passthrough

    ``rating`` is ``None`` when the judge answered but gave no usable rating —
    the same "no rating, not a weak one" semantics as
    ``DistractorPlausibilityVerdict``. It is deliberately NOT coerced to a
    number: ``likert_to_verdict(None)`` accepts, so an absent rating can never
    manufacture a rejection.
    """

    rating: Optional[int] = None
    reason: str

    @model_validator(mode='before')
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out: dict[str, Any] = {}
        for k, v in data.items():
            if k in ('1', 1):
                out['rating'] = v
            elif k in ('2', 2):
                out['reason'] = v
            elif k == 'confidence':
                # Pre-v2 prompt row still active against v2 code. Surfaced by
                # _validate rather than silently rescaled — see there.
                out['rating'] = v
            else:
                out[k] = v
        # An empty or bare-numeric reason is useless as regen feedback; replace
        # it with a deterministic sentence. Leave a missing key alone so the
        # required-field validation still fires.
        if 'reason' in out:
            out['reason'] = _clean_reason(out['reason'])
        return out

    @model_validator(mode='after')
    def _validate(self) -> 'AnswerEntailmentVerdict':
        if self.rating is None:
            return self
        if not 1 <= self.rating <= 5:
            raise ValueError(f'rating {self.rating!r} must be in [1, 5]')
        return self

    @field_validator('rating', mode='before')
    @classmethod
    def _reject_legacy_float_scale(cls, value: Any) -> Any:
        """Backstop for a pre-v3 (0.0-1.0) prompt row feeding v3 code.

        **This is a backstop, not the guard.** It catches only the *fractional*
        legacy values (0.85, 0.9, 0.5), because the two scales overlap at
        exactly one point — ``1`` — where they mean opposite things: "maximum
        confidence, accept" on the old float scale and "worst rating, reject"
        on Likert. A legacy ``1.0`` is indistinguishable by value from a Likert
        ``1`` and passes straight through here. That is not a corner case: over
        391 historical responses in ``llm_calls.raw_response``, **77% were
        exactly 1.0**, so value-shape detection would miss the majority of a
        scale mismatch and invert it into a rejection.

        The real guard is therefore the version check in
        ``judges.answer_entailment._is_pre_likert``, which refuses to run at all
        against a row older than v3. Keep both: this one still fires if a v3 row
        is active but the model answers on the old scale anyway.

        Raising routes through the judge's normal error path: ``safe_accept``
        when serving (a dead judge must not break a live session) and
        ``JudgeUnavailable`` inside a generation batch, so a half-applied
        migration aborts the batch rather than shipping unjudged questions.
        """
        if value is None or isinstance(value, bool):
            return value
        if isinstance(value, float) and not value.is_integer():
            raise ValueError(
                f'rating {value!r} is not an integer — this is the pre-v2 '
                f'0.0-1.0 confidence scale. The prompt_templates row for '
                f'test_answer_entailment is older than the code; apply '
                f'migrations/entailment_likert_v2.sql.'
            )
        return value


class DistractorPlausibilityVerdict(BaseModel):
    """Judge output: TWO Likert ratings per distractor (v7 — TASK-719).

    The judge prompt uses numeric keys so the prompt body can be authored
    entirely in the target language (no English field names in ZH/JA rows).

    v7 splits the single v4 rating onto the two axes it was conflating — see the
    long note above ``axes_to_verdict`` for what each band means and why the
    verdict arithmetic lives in Python. The model returns, per distractor, a
    three-element array ``[fit, confusability, reason]``::

        {"1": [5, 4, "reason0"], "2": [4, 5, "reason1"], "3": [2, 1, "reason2"]}
        -> fit=[5, 4, 2]  confusability=[4, 5, 1]  reasons=["reason0", ...]

    That is one integer more than the shape v4/v6 already ask for and get
    reliably, which is the whole reason it was chosen over a redesign of the
    output contract.

    **Reading a single-rating (v4/v6) response is a supported path, not a bug.**
    A two-element ``[rating, reason]`` array yields ``fit=rating`` and
    ``confusability=None``, and ``fit``'s bands are identical to v4's, so the
    verdicts are unchanged. This is what lets the code deploy ahead of the
    prompt rows.

    ``per_distractor`` survives as a read-only alias for ``fit`` — several call
    sites and two test modules read it, and under v4 semantics it *was* the fit
    axis. It is also accepted as an input key.

    A rating of ``None`` on either axis means the judge returned no number for
    that axis of that item — not a weak one. It is deliberately NOT coerced:
    ``axes_to_verdict`` treats a ``None`` axis as contributing 'accept', so an
    absent rating can never manufacture a rejection or a review-queue entry.

    ``_validate`` enforces matching list lengths and ratings in [1, 5].
    """

    fit: list[int | None]
    confusability: list[int | None] = []
    reasons: list[str]

    @property
    def per_distractor(self) -> list[int | None]:
        """Legacy alias for ``fit`` — see the class docstring."""
        return self.fit

    @model_validator(mode='before')
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        # The judge model intermittently returns off-schema shapes that survive
        # call_llm's repair retry: a bare list, a ``per_distractor`` list with no
        # ``reasons``, alias keys, or a list of {rating, reason} dicts. Coerce
        # the common variants into ``{fit, confusability, reasons}`` so the judge
        # yields a real verdict instead of failing open (safe_accept). An
        # unparseable rating becomes None — "the judge returned no rating for
        # this item" — NOT a fabricated number.
        #
        # This used to fall back to 3, which mapped to 'flag'. That made a parse
        # miss indistinguishable from a genuine "weak" verdict, and because the
        # v3 prompt's numeric keys were ambiguous the model frequently returned
        # reasons with no ratings at all: 80% of live ratings were fabricated 3s
        # and the review queue filled with judgments that were never made. A
        # missing rating must stay visibly missing so the judge can accept the
        # item outright (judges.base.accept_item) instead of queueing a fake
        # review.
        #
        # Every branch below is here because a real response needed it. The v7
        # additions are the second axis: a third array slot, a three-key
        # field-selector shape, and confusability-named dict keys. Nothing was
        # removed — a v4/v6 row still parses, to fit-only.

        _NO_RATING = None  # the judge returned no rating for this item

        def _as_likert(x):
            """Coerce a value to an int Likert rating in [1, 5], or None."""
            if isinstance(x, bool):
                return None
            v = None
            if isinstance(x, (int, float)):
                v = float(x)
            elif isinstance(x, str):
                try:
                    v = float(x.strip())
                except ValueError:
                    return None
            if v is None:
                return None
            r = int(round(v))
            return 1 if r < 1 else 5 if r > 5 else r

        # Keys that name a distractor's position, NOT its rating — must never be
        # read as the score (the model emits ``{"distractor": "1", "rating": 4}``
        # and the index 1 would otherwise masquerade as the rating).
        _INDEX_KEYS = ('distractor', 'index', 'idx', 'option', 'choice',
                       'number', 'num', 'item', 'id')
        # Checked in this order, most specific first. A v4-era generic rating key
        # lands on `fit`, which is the axis whose bands v4 actually used.
        _CONF_KEYS = ('confusab', 'confusion', 'confusing', 'tempt', 'attract',
                      'closeness', 'similar')
        _FIT_KEYS = ('fit', 'topical', 'topic', 'subject', 'domain', 'relevan')
        _RATING_KEYS = ('rating', 'score', 'likert', 'plausibility', 'verdict')

        def _triple(item):
            """Extract (fit, confusability, reason) from one per-distractor element.

            Handles a scalar, a ``[fit, confusability, reason]`` list (or the v4
            ``[rating, reason]`` two-element form), or a dict with named keys.
            For lists the axes are POSITIONAL — first number is fit, second is
            confusability — which is why the prompt fixes that order, and why a
            truncated array degrades to fit-only rather than guessing. For dicts
            an explicit axis-named key wins; an index/id key is never read as a
            rating.
            """
            if isinstance(item, (int, float, str)):
                return _as_likert(item), None, ''
            if isinstance(item, list):
                fit, conf, reason = None, None, ''
                for x in item:
                    s = _as_likert(x)
                    if s is not None:
                        if fit is None:
                            fit = s
                        elif conf is None:
                            conf = s
                    elif isinstance(x, str) and not reason:
                        reason = x
                return fit, conf, reason
            if isinstance(item, dict):
                fit, conf, reason = None, None, ''
                # Pass 1: honour explicit axis / reason keys.
                for k, v in item.items():
                    kl = str(k).lower()
                    if 'reason' in kl or 'explanation' in kl:
                        reason = str(v)
                    elif any(t in kl for t in _CONF_KEYS):
                        s = _as_likert(v)
                        if s is not None:
                            conf = s
                    elif any(t in kl for t in _FIT_KEYS):
                        s = _as_likert(v)
                        if s is not None:
                            fit = s
                    elif any(t in kl for t in _RATING_KEYS):
                        s = _as_likert(v)
                        if s is not None and fit is None:
                            fit = s
                # Pass 2: fall back to the first scoreable non-index values, in
                # order, filling fit then confusability.
                for k, v in item.items():
                    if fit is not None and conf is not None:
                        break
                    kl = str(k).lower()
                    if 'reason' in kl or 'explanation' in kl:
                        continue
                    if any(t in kl for t in _INDEX_KEYS):
                        continue
                    if any(t in kl for t in _CONF_KEYS + _FIT_KEYS + _RATING_KEYS):
                        continue          # already handled in pass 1
                    s = _as_likert(v)
                    if s is None:
                        continue
                    if fit is None:
                        fit = s
                    else:
                        conf = s
                return fit, conf, reason
            return None, None, ''

        def _all_numeric(seq):
            return (isinstance(seq, list) and bool(seq)
                    and all(_as_likert(x) is not None for x in seq))

        def _starts_with_text(seq):
            return (isinstance(seq, list) and bool(seq)
                    and _as_likert(seq[0]) is None)

        # Resolve `data` into an `out` dict carrying fit + confusability + reasons.
        if isinstance(data, list):
            # Bare list → unzip into the parallel lists.
            fits, confs, reasons = [], [], []
            for item in data:
                f, c, r = _triple(item)
                fits.append(f if f is not None else _NO_RATING)
                confs.append(c if c is not None else _NO_RATING)
                reasons.append(r)
            out: dict[str, Any] = {
                'fit': fits, 'confusability': confs, 'reasons': reasons}
        elif isinstance(data, dict):
            # The model frequently misreads the numeric-key convention: instead
            # of the intended {"1": [ratings], "2": [reasons]} (field selectors),
            # it emits {"1": [rating, reason], "2": [...], "3": [...]} where each
            # numeric key is a DISTRACTOR. That read only 2 of N entries → a
            # length mismatch → safe_accept fall-open (24% of v3 groups in the
            # 2026-06-06 fixture re-score). Detect and unzip it here.
            dig = {str(k): v for k, v in data.items() if str(k).isdigit()}
            seq = [str(i) for i in range(1, len(dig) + 1)]
            contiguous = len(dig) >= 2 and set(dig) == set(seq)
            first = dig.get('1')

            # v7 field-selector shape: {"1": [fits], "2": [confs], "3": [reasons]}.
            # Discriminated from three per-distractor triples by the fact that a
            # triple always carries its reason STRING inside its own array, so
            # "1" and "2" cannot both be all-numeric while "3" starts with text.
            selector3 = (
                set(dig) == {'1', '2', '3'}
                and _all_numeric(dig['1']) and _all_numeric(dig['2'])
                and _starts_with_text(dig['3'])
            )
            # Legacy v3 field-selector shape: {"1": [ratings], "2": [reasons]}.
            # The reliable discriminator is "2": a reasons array starts with a
            # STRING; a per-distractor pair starts with a NUMBER. "1" must itself
            # be a list (a scalar "1" means ratings are keyed by distractor).
            canonical = False
            if set(dig) <= {'1', '2'} and isinstance(first, list) and first:
                two = dig.get('2')
                if not isinstance(two, list) or not two:
                    canonical = True               # only "1", or "2" not a list
                else:
                    canonical = _as_likert(two[0]) is None  # "2"=[reason,...]

            if selector3:
                out = {'fit': dig['1'], 'confusability': dig['2'],
                       'reasons': dig['3']}
            elif contiguous and not canonical:
                fits, confs, reasons = [], [], []
                for k in seq:
                    f, c, r = _triple(dig[k])
                    fits.append(f if f is not None else _NO_RATING)
                    confs.append(c if c is not None else _NO_RATING)
                    reasons.append(r)
                out = {'fit': fits, 'confusability': confs, 'reasons': reasons}
            else:
                out = {}
                for k, v in data.items():
                    if k in ('1', 1):
                        out['fit'] = v
                    elif k in ('2', 2):
                        out['reasons'] = v
                    else:
                        out[k] = v
        else:
            return data

        # Alias keys for the two axis lists. `per_distractor` is the v4 name and
        # is still what most callers construct with, so it must map to `fit`.
        if 'fit' not in out:
            for alias in ('per_distractor', 'ratings', 'scores', 'confidences',
                          'plausibility', 'plausibilities', 'fits'):
                if isinstance(out.get(alias), list):
                    out['fit'] = out[alias]
                    break
        if 'confusability' not in out:
            for alias in ('confusabilities', 'confusable', 'temptation',
                          'tempting'):
                if isinstance(out.get(alias), list):
                    out['confusability'] = out[alias]
                    break

        # A list of {fit, confusability, reason} dicts under fit → unzip.
        pd = out.get('fit')
        if isinstance(pd, list) and pd and all(isinstance(x, dict) for x in pd):
            fits, confs, reasons = [], [], []
            for item in pd:
                f, c, r = _triple(item)
                fits.append(f if f is not None else _NO_RATING)
                confs.append(c if c is not None else _NO_RATING)
                reasons.append(r)
            out['fit'] = fits
            if not out.get('confusability'):
                out['confusability'] = confs
            if not out.get('reasons'):
                out['reasons'] = reasons

        # Coerce every rating to a valid Likert int (handles a plain list of
        # mixed floats/strings the model may emit, e.g. [5, "4", 2.0]).
        for axis in ('fit', 'confusability'):
            if isinstance(out.get(axis), list):
                out[axis] = [
                    (_as_likert(x) if _as_likert(x) is not None else _NO_RATING)
                    for x in out[axis]
                ]

        if isinstance(out.get('fit'), list):
            n = len(out['fit'])

            # An absent or short confusability axis pads with None — "no rating
            # on this axis" — which is exactly what a v4/v6 single-rating row
            # produces, and what keeps its verdicts unchanged.
            confs = out.get('confusability')
            if not isinstance(confs, list):
                confs = []
            if len(confs) < n:
                confs = confs + [_NO_RATING] * (n - len(confs))
            elif len(confs) > n:
                confs = confs[:n]
            out['confusability'] = confs

            # Reasons missing or wrong length → pad/truncate to fit, then coerce
            # each to a real sentence: the model occasionally emits a non-string
            # (a duplicated rating) or an empty slot, both of which would
            # otherwise poison the regen avoid_context. _clean_reason fixes those.
            reasons = out.get('reasons')
            if not isinstance(reasons, list):
                reasons = []
            if len(reasons) < n:
                reasons = reasons + [''] * (n - len(reasons))
            elif len(reasons) > n:
                reasons = reasons[:n]
            out['reasons'] = [_clean_reason(r) for r in reasons]

        return out

    @model_validator(mode='after')
    def _validate(self) -> 'DistractorPlausibilityVerdict':
        if len(self.fit) != len(self.reasons):
            raise ValueError(
                f'fit length ({len(self.fit)}) must '
                f'match reasons length ({len(self.reasons)})'
            )
        if len(self.confusability) != len(self.fit):
            raise ValueError(
                f'confusability length ({len(self.confusability)}) must '
                f'match fit length ({len(self.fit)})'
            )
        for axis in AXES:
            for i, c in enumerate(getattr(self, axis)):
                # None is legal and load-bearing: it records that the judge
                # returned no rating on this axis for this distractor, which
                # contributes 'accept' rather than a fabricated 'flag'.
                if c is None:
                    continue
                if not 1 <= c <= 5:
                    raise ValueError(
                        f'{axis}[{i}]={c!r} must be a Likert rating in [1, 5]'
                    )
        return self
