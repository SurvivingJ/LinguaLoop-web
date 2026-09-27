# services/vocabulary_ladder/bundle/judge.py
"""``BundleJudge`` — TASK-816: one ``ladder_bundle_judge`` call/sense.

Collapses the render-time judge calls exercise_renderer.py makes today
(``filter_l1_distractors``, ``filter_distractors`` (cloze),
``filter_collocation_distractors``/``judge_collocation_repair``,
``judge_wrong_sentences`` (L6 and L7), and the typed generators' own
``filter_relation_foils``/``filter_particle_foils``) — up to 7 calls per
variant, 14 per sense — into ONE call per sense covering both variants,
per ADR-028 Decision §4.

Only zh and ja have a ``ladder_bundle_judge`` prompt row (see
``migrations/exercise_gen_bundle_prompts_draft.sql``) — there is no en row,
so :meth:`BundleJudge.judge_bundle` always falls back to the existing
per-judge calls for language_id=2. The P1 sentence-corpus judge
(``judges/p1_sentences``) is NOT part of this bundle — ADR-028 keeps it
separate (it is what catches compound-word anchoring).

Fail-closed contract (mirrors every existing judge — see
``services.exercise_generation.judges.base``): a judge going missing must
never silently accept unjudged content. Concretely:

* The whole bundle call fails (no response, malformed top level) → EVERY
  request falls back to its real per-judge call. This is exactly today's
  call graph, plus one wasted bundle attempt.
* An axis is entirely absent from an otherwise-valid response despite having
  requests → every request for that axis falls back.
* One request's own candidates are missing/malformed inside an otherwise
  present axis → that single request falls back (its own real judge call),
  every other request on the same axis is unaffected.

Fallback is per REQUEST, not per candidate: the underlying judge functions
each rule on a whole candidate list for one context in one call, so splicing
verdicts half from the bundle and half from a fallback call within the same
exercise item would mix inconsistent judge behaviour on one artifact. A
request that needs any fallback falls back whole.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from services.exercise_generation.judges.base import JudgeOutcome
from services.exercise_generation.judges.cloze import filter_distractors
from services.exercise_generation.judges.collocation import (
    filter_collocation_distractors, judge_collocation_repair,
)
from services.exercise_generation.judges.l1_distractor import filter_l1_distractors
from services.exercise_generation.judges.particle import filter_particle_foils
from services.exercise_generation.judges.relation import filter_relation_foils
from services.exercise_generation.judges.sentence_validity import judge_wrong_sentences
from services.llm_service import call_llm
from services.prompt_service import get_template_config
from services.test_generation.schemas import likert_to_verdict

logger = logging.getLogger(__name__)

TASK_NAME = 'ladder_bundle_judge'
_PIPELINE = 'vocab_ladder'

_LANG_ID_TO_CODE: dict[int, str] = {1: 'zh', 2: 'en', 3: 'ja'}

# No en row exists in migrations/exercise_gen_bundle_prompts_draft.sql today —
# every en request always falls back to the existing per-judge calls.
_SUPPORTED_LANGUAGES = frozenset({1, 3})

_MAX_TOKENS = 16000  # >=3x judge_ladder_sentence_validity's own baseline p99 (5247);
                      # the bundle axis with the most items is usually sentence_validity.


# ---------------------------------------------------------------------------
# Per-axis request shapes — one per render-time judge call site in
# exercise_renderer.py, so the wiring patch's substitution is 1:1.
# ---------------------------------------------------------------------------

@dataclass
class SentenceValidityRequest:
    """One ``judge_wrong_sentences`` call site (L6's 3 pairs, or L7's 1 pair)."""
    request_id: str
    target: str
    pairs: list[tuple[str, str]]   # (sentence_text, labeled_reason)


@dataclass
class DistractorRequest:
    """One cloze / l1_distractor / L5-collocation call site.

    ``line`` is the pre-rendered "sentence+correct+target" context shown on
    each numbered prompt line (built by the caller so this module stays
    axis-agnostic about wording). ``line_ctx`` carries the SAME context as
    plain fields, keyed exactly as the real per-judge function's positional
    args need them, so a fallback call can reconstruct them without
    re-parsing ``line``:

    * cloze:          ``{'sentence_with_blank': ..., 'correct_answer': ...}``
    * l1_distractor:  ``{'target': ...}``
    * collocation(L5): ``{'sentence': ..., 'target': ..., 'correct_collocate': ...}``
    """
    request_id: str
    candidates: list[str]
    line: str
    line_ctx: dict = field(default_factory=dict)


@dataclass
class CollocationVerdictRequest:
    """The L8 single-candidate verdict call site."""
    request_id: str
    sentence: str
    target: str
    correct_collocate: str
    error_collocate: str


@dataclass
class RelationRequest:
    """The ``synonym_antonym_match`` foil-filter call site."""
    request_id: str
    target: str
    definition: str
    relation: str
    correct_answer: str
    foils: list[str]


@dataclass
class ParticleRequest:
    """The ``particle_selection`` foil-filter call site (ja only)."""
    request_id: str
    sentence_with_blank: str
    correct_particle: str
    foils: list[str]


@dataclass
class BundleJudgeRequests:
    sentence_validity: list[SentenceValidityRequest] = field(default_factory=list)
    cloze: list[DistractorRequest] = field(default_factory=list)
    l1_distractor: list[DistractorRequest] = field(default_factory=list)
    collocation_filter: list[DistractorRequest] = field(default_factory=list)
    collocation_verdict: list[CollocationVerdictRequest] = field(default_factory=list)
    relation: list[RelationRequest] = field(default_factory=list)
    particle: list[ParticleRequest] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any((
            self.sentence_validity, self.cloze, self.l1_distractor,
            self.collocation_filter, self.collocation_verdict,
            self.relation, self.particle,
        ))


@dataclass
class BundleJudgeResult:
    ok: bool = False
    fallback_requests: list[str] = field(default_factory=list)
    sentence_validity: dict[str, list[JudgeOutcome]] = field(default_factory=dict)
    cloze: dict[str, tuple[list[str], dict]] = field(default_factory=dict)
    l1_distractor: dict[str, tuple[list[str], dict]] = field(default_factory=dict)
    collocation_filter: dict[str, tuple[list[str], dict]] = field(default_factory=dict)
    collocation_verdict: dict[str, JudgeOutcome] = field(default_factory=dict)
    relation: dict[str, tuple[list[str], dict]] = field(default_factory=dict)
    particle: dict[str, tuple[list[str], dict]] = field(default_factory=dict)


class BundleJudge:
    """One ``ladder_bundle_judge`` call/sense, with per-request fallback."""

    def __init__(self, db, language_id: int):
        self.db = db
        self.language_id = language_id
        self._cfg: dict | None = None

    @property
    def cfg(self) -> dict:
        if self._cfg is None:
            self._cfg = get_template_config(self.db, TASK_NAME, self.language_id)
        return self._cfg

    # ------------------------------------------------------------------

    def judge_bundle(
        self, sense_id: int, target: str, requests: BundleJudgeRequests,
    ) -> BundleJudgeResult:
        """Judge every request in one call, falling back per-request on failure.

        ``target`` is the sense's headword, used for the sentence_validity
        axis's ``{target}`` placeholder (the one axis whose template still
        carries a single shared context field, since it is genuinely the same
        word across every L6/L7 item for this sense).
        """
        result = BundleJudgeResult()
        if requests.is_empty():
            result.ok = True
            return result

        if self.language_id not in _SUPPORTED_LANGUAGES:
            logger.info(
                "ladder_bundle_judge has no row for language_id=%s — falling "
                "back to per-judge calls for every request (sense %s)",
                self.language_id, sense_id,
            )
            self._fallback_all(sense_id, requests, result)
            return result

        raw = self._call_bundle(sense_id, target, requests)
        result.ok = raw is not None
        if raw is None:
            self._fallback_all(sense_id, requests, result)
            return result

        self._resolve_sentence_validity(sense_id, requests, raw, result)
        self._resolve_distractor_axis(
            sense_id, 'cloze', requests.cloze, raw.get('cloze'), result, result.cloze,
            fallback=lambda r: filter_distractors(
                self.db, *_cloze_ctx(r), self.language_id,
            ),
        )
        self._resolve_distractor_axis(
            sense_id, 'l1_distractor', requests.l1_distractor, raw.get('l1_distractor'), result, result.l1_distractor,
            fallback=lambda r: filter_l1_distractors(
                self.db, _l1_target(r), r.candidates, self.language_id,
            ),
        )
        self._resolve_distractor_axis(
            sense_id, 'collocation_filter', requests.collocation_filter, raw.get('collocation'), result, result.collocation_filter,
            fallback=lambda r: filter_collocation_distractors(
                self.db, *_collocation_ctx(r), self.language_id,
            ),
        )
        self._resolve_collocation_verdict(sense_id, requests, raw.get('collocation'), result)
        self._resolve_relation(sense_id, requests, raw.get('relation'), result)
        self._resolve_particle(sense_id, requests, raw.get('particle'), result)

        return result

    # ------------------------------------------------------------------
    # The bundle LLM call
    # ------------------------------------------------------------------

    def _call_bundle(
        self, sense_id: int, target: str, requests: BundleJudgeRequests,
    ) -> dict | None:
        try:
            cfg = self.cfg
        except Exception as exc:
            logger.warning(
                "ladder_bundle_judge template load failed for sense %s: %s", sense_id, exc,
            )
            return None

        prompt_vars = {
            'target': target,
            'sentence_validity_pairs_numbered': _render_sentence_validity(requests.sentence_validity),
            'cloze_items_numbered': _render_distractor_axis(requests.cloze),
            'l1_items_numbered': _render_distractor_axis(requests.l1_distractor),
            'collocation_items_numbered': _render_collocation_axis(
                requests.collocation_filter, requests.collocation_verdict,
            ),
            'relation_items_numbered': _render_relation_axis(requests.relation),
            'particle_items_numbered': _render_particle_axis(requests.particle),
        }
        try:
            prompt = cfg['template'].format(**prompt_vars)
        except (KeyError, IndexError) as exc:
            # A judge template using {name} format specs; unlike
            # asset_generators._renderer.render_template, JSON braces here are
            # doubled ({{...}}) precisely so str.format leaves them alone —
            # matching the live per-judge templates' own convention.
            logger.warning(
                "ladder_bundle_judge template formatting failed for sense %s: %s",
                sense_id, exc,
            )
            return None

        try:
            raw = call_llm(
                prompt,
                model=cfg['model'],
                temperature=0.0,
                max_tokens=_MAX_TOKENS,
                response_format='json_object',
                provider=cfg['provider'],
                pipeline=_PIPELINE,
                task_name=TASK_NAME,
                template_version=cfg.get('version'),
                language_code=_LANG_ID_TO_CODE.get(self.language_id),
                sense_id=sense_id,
                allow_internal_repair=False,
            )
        except Exception as exc:
            logger.warning(
                "ladder_bundle_judge call failed for sense %s: %s", sense_id, exc,
            )
            return None

        if not isinstance(raw, dict):
            logger.warning(
                "ladder_bundle_judge non-dict response for sense %s (%s)",
                sense_id, type(raw).__name__,
            )
            return None
        return raw

    # ------------------------------------------------------------------
    # Per-axis resolution
    # ------------------------------------------------------------------

    def _resolve_sentence_validity(self, sense_id, requests, raw, result) -> None:
        # `axis` is a dict keyed "1".."N" (N = total pairs across every
        # request, in request order) — sentence_validity's flat numbering is
        # 1-based across the WHOLE axis, matching judge_wrong_sentences' own
        # numbering convention.
        axis = raw.get('sentence_validity') if isinstance(raw, dict) else None
        outcomes_by_index: dict[int, JudgeOutcome] | None = None
        if isinstance(axis, dict):
            outcomes_by_index = {}
            ok = True
            idx = 1
            for req in requests.sentence_validity:
                for _ in req.pairs:
                    entry = axis.get(str(idx))
                    if not isinstance(entry, dict):
                        ok = False
                    else:
                        try:
                            rating = float(entry.get('rating'))
                        except (TypeError, ValueError):
                            ok = False
                            rating = None
                        if rating is not None:
                            outcomes_by_index[idx] = JudgeOutcome(
                                verdict=likert_to_verdict(rating),
                                confidence=rating,
                                reason=str(entry.get('reason', ''))[:200],
                            )
                    idx += 1
            if not ok:
                outcomes_by_index = None  # any malformed item forces a full fallback pass below

        idx = 1
        for req in requests.sentence_validity:
            n = len(req.pairs)
            local_indices = list(range(idx, idx + n))
            idx += n
            if outcomes_by_index is not None and all(i in outcomes_by_index for i in local_indices):
                result.sentence_validity[req.request_id] = [
                    outcomes_by_index[i] for i in local_indices
                ]
                continue
            result.fallback_requests.append(f'sentence_validity:{req.request_id}')
            result.sentence_validity[req.request_id] = judge_wrong_sentences(
                self.db, req.target, req.pairs, self.language_id,
            )

    def _resolve_distractor_axis(self, sense_id, axis_name, reqs, axis, result, out, *, fallback) -> None:
        idx = 1
        for req in reqs:
            n = len(req.candidates)
            local_indices = list(range(idx, idx + n))
            idx += n
            parsed = _parse_verdict_axis(axis, local_indices)
            if parsed is not None:
                kept = [c for c, i in zip(req.candidates, local_indices) if parsed[i][0] == 'keep']
                rejected = [c for c, i in zip(req.candidates, local_indices) if parsed[i][0] == 'reject']
                meta = {
                    'rejected': len(rejected), 'kept': len(kept),
                    'rejected_items': rejected, 'model': self._cfg.get('model') if self._cfg else '',
                    'version': self._cfg.get('version') if self._cfg else 0,
                }
                out[req.request_id] = (kept, meta)
                continue
            logger.info(
                "bundle judge fallback for %s:%s (sense %s)", axis_name, req.request_id, sense_id,
            )
            result.fallback_requests.append(f'{axis_name}:{req.request_id}')
            out[req.request_id] = fallback(req)

    def _resolve_collocation_verdict(self, sense_id, requests, axis, result) -> None:
        # L5 candidates and the single L8 candidate share ONE axis
        # ("collocation") in the draft template, numbered contiguously after
        # every collocation_filter request. Compute the L8 offset from how
        # many L5 candidates preceded it.
        offset = sum(len(r.candidates) for r in requests.collocation_filter)
        idx = offset + 1
        for req in requests.collocation_verdict:
            parsed = _parse_rating_axis(axis, [idx])
            if parsed is not None:
                verdict, rating, reason = parsed[idx]
                result.collocation_verdict[req.request_id] = JudgeOutcome(
                    verdict=verdict, confidence=rating, reason=reason,
                )
            else:
                result.fallback_requests.append(f'collocation_verdict:{req.request_id}')
                result.collocation_verdict[req.request_id] = judge_collocation_repair(
                    self.db, req.sentence, req.target, req.correct_collocate,
                    req.error_collocate, self.language_id,
                )
            idx += 1

    def _resolve_relation(self, sense_id, requests, axis, result) -> None:
        idx = 1
        for req in requests.relation:
            n = len(req.foils)
            local_indices = list(range(idx, idx + n))
            idx += n
            parsed = _parse_rating_axis(axis, local_indices)
            if parsed is not None:
                kept = [f for f, i in zip(req.foils, local_indices) if parsed[i][0] != 'reject']
                rejected = [f for f, i in zip(req.foils, local_indices) if parsed[i][0] == 'reject']
                meta = {
                    'rejected': len(rejected), 'kept': len(kept),
                    'rejected_items': rejected, 'relation': req.relation,
                    'model': self._cfg.get('model') if self._cfg else '',
                    'version': self._cfg.get('version') if self._cfg else 0,
                }
                result.relation[req.request_id] = (kept, meta)
            else:
                result.fallback_requests.append(f'relation:{req.request_id}')
                result.relation[req.request_id] = filter_relation_foils(
                    self.db, req.target, req.definition, req.relation,
                    req.correct_answer, req.foils, self.language_id,
                )

    def _resolve_particle(self, sense_id, requests, axis, result) -> None:
        idx = 1
        for req in requests.particle:
            n = len(req.foils)
            local_indices = list(range(idx, idx + n))
            idx += n
            parsed = _parse_rating_axis(axis, local_indices)
            if parsed is not None:
                kept = [f for f, i in zip(req.foils, local_indices) if parsed[i][0] != 'reject']
                rejected = [f for f, i in zip(req.foils, local_indices) if parsed[i][0] == 'reject']
                meta = {
                    'rejected': len(rejected), 'kept': len(kept),
                    'rejected_items': rejected,
                    'model': self._cfg.get('model') if self._cfg else '',
                    'version': self._cfg.get('version') if self._cfg else 0,
                }
                result.particle[req.request_id] = (kept, meta)
            else:
                result.fallback_requests.append(f'particle:{req.request_id}')
                result.particle[req.request_id] = filter_particle_foils(
                    self.db, req.sentence_with_blank, req.correct_particle,
                    req.foils, self.language_id,
                )

    # ------------------------------------------------------------------

    def _fallback_all(self, sense_id, requests: BundleJudgeRequests, result: BundleJudgeResult) -> None:
        """Total bundle failure (or unsupported language): every request runs
        through its real judge call, unchanged from today's behaviour.
        """
        for req in requests.sentence_validity:
            result.fallback_requests.append(f'sentence_validity:{req.request_id}')
            result.sentence_validity[req.request_id] = judge_wrong_sentences(
                self.db, req.target, req.pairs, self.language_id,
            )
        for req in requests.cloze:
            result.fallback_requests.append(f'cloze:{req.request_id}')
            result.cloze[req.request_id] = filter_distractors(self.db, *_cloze_ctx(req), self.language_id)
        for req in requests.l1_distractor:
            result.fallback_requests.append(f'l1_distractor:{req.request_id}')
            result.l1_distractor[req.request_id] = filter_l1_distractors(
                self.db, _l1_target(req), req.candidates, self.language_id,
            )
        for req in requests.collocation_filter:
            result.fallback_requests.append(f'collocation_filter:{req.request_id}')
            result.collocation_filter[req.request_id] = filter_collocation_distractors(
                self.db, *_collocation_ctx(req), self.language_id,
            )
        for req in requests.collocation_verdict:
            result.fallback_requests.append(f'collocation_verdict:{req.request_id}')
            result.collocation_verdict[req.request_id] = judge_collocation_repair(
                self.db, req.sentence, req.target, req.correct_collocate,
                req.error_collocate, self.language_id,
            )
        for req in requests.relation:
            result.fallback_requests.append(f'relation:{req.request_id}')
            result.relation[req.request_id] = filter_relation_foils(
                self.db, req.target, req.definition, req.relation,
                req.correct_answer, req.foils, self.language_id,
            )
        for req in requests.particle:
            result.fallback_requests.append(f'particle:{req.request_id}')
            result.particle[req.request_id] = filter_particle_foils(
                self.db, req.sentence_with_blank, req.correct_particle,
                req.foils, self.language_id,
            )


# ---------------------------------------------------------------------------
# DistractorRequest context lines can't be un-rendered back into positional
# args, so the two axes that need a real per-judge fallback carry their
# context as a second, structured field rather than only ``line``. Kept as
# tiny wrapper dataclasses accessed via these helpers so DistractorRequest
# itself stays a single generic shape for the render step.
# ---------------------------------------------------------------------------

def _cloze_ctx(req: DistractorRequest):
    ctx = req.line_ctx
    return ctx['sentence_with_blank'], ctx['correct_answer'], req.candidates


def _l1_target(req: DistractorRequest) -> str:
    return req.line_ctx['target']


def _collocation_ctx(req: DistractorRequest):
    ctx = req.line_ctx
    return ctx['sentence'], ctx['target'], ctx['correct_collocate'], req.candidates


# ---------------------------------------------------------------------------
# Numbered-line rendering (Python-side; each line is self-contained so the
# bundle template can safely combine variant A and B in one flat sequence)
# ---------------------------------------------------------------------------

def _render_sentence_validity(requests: list[SentenceValidityRequest]) -> str:
    lines = []
    idx = 1
    for req in requests:
        tag = _variant_tag(req.request_id)
        for sentence, reason in req.pairs:
            lines.append(
                f'{idx}. [{tag}] Sentence: "{sentence}"\n   '
                f'Labeled reason it is wrong: {reason or "(none given)"}'
            )
            idx += 1
    return '\n'.join(lines) if lines else '(none)'


def _render_distractor_axis(requests: list[DistractorRequest]) -> str:
    lines = []
    idx = 1
    for req in requests:
        tag = _variant_tag(req.request_id)
        for candidate in req.candidates:
            lines.append(f'{idx}. [{tag}] {req.line} — candidate: {candidate}')
            idx += 1
    return '\n'.join(lines) if lines else '(none)'


def _render_collocation_axis(
    filter_requests: list[DistractorRequest],
    verdict_requests: list[CollocationVerdictRequest],
) -> str:
    lines = []
    idx = 1
    for req in filter_requests:
        tag = _variant_tag(req.request_id)
        for candidate in req.candidates:
            lines.append(f'{idx}. [{tag}] {req.line} — candidate: {candidate}')
            idx += 1
    for req in verdict_requests:
        tag = _variant_tag(req.request_id)
        lines.append(
            f'{idx}. [{tag}] Sentence: "{req.sentence}"; target: {req.target}; '
            f'correct collocate: {req.correct_collocate} — candidate: {req.error_collocate}'
        )
        idx += 1
    return '\n'.join(lines) if lines else '(none)'


def _render_relation_axis(requests: list[RelationRequest]) -> str:
    lines = []
    idx = 1
    for req in requests:
        tag = _variant_tag(req.request_id)
        for foil in req.foils:
            lines.append(
                f'{idx}. [{tag}] target: {req.target}; sense: {req.definition or "(none)"}; '
                f'relation: {req.relation}; correct answer: {req.correct_answer} — candidate: {foil}'
            )
            idx += 1
    return '\n'.join(lines) if lines else '(none)'


def _render_particle_axis(requests: list[ParticleRequest]) -> str:
    lines = []
    idx = 1
    for req in requests:
        tag = _variant_tag(req.request_id)
        for foil in req.foils:
            lines.append(
                f'{idx}. [{tag}] {req.sentence_with_blank} (correct: {req.correct_particle}) '
                f'— candidate: {foil}'
            )
            idx += 1
    return '\n'.join(lines) if lines else '(none)'


def _variant_tag(request_id: str) -> str:
    """``'A:L6' -> 'A'``; falls back to the whole id if it isn't ``V:...``."""
    head = request_id.split(':', 1)[0]
    return head if head in ('A', 'B') else request_id


# ---------------------------------------------------------------------------
# Response parsing — duplicates the MINIMAL classification each individual
# judge module already does (see judges/cloze.py, l1_distractor.py,
# collocation.py, relation.py, particle.py), since none of them expose that
# step as a standalone function separate from their own call_llm call.
# ---------------------------------------------------------------------------

def _parse_verdict_axis(
    axis: object, indices: list[int],
) -> dict[int, tuple[str, float | None, str]] | None:
    """``{'keep'|'verdict'}``-style axis (cloze / l1_distractor / L5 filter).

    Returns ``None`` if ANY requested index is missing/malformed — the caller
    then falls the whole request back to its real judge call. A per-item
    ``accept_item``-style "keep missing verdict" leniency is deliberately NOT
    applied here: for the bundle path, "malformed" means "the bundle prompt
    didn't answer this item", which is a bundle-availability problem, not a
    normal judge disagreement — the real judge call is cheap enough (one
    request, not the whole sense) that falling back is strictly safer than
    guessing.
    """
    if not isinstance(axis, dict):
        return None
    out: dict[int, tuple[str, float | None, str]] = {}
    for i in indices:
        entry = axis.get(str(i))
        if not isinstance(entry, dict):
            return None
        verdict = str(entry.get('verdict', '')).strip().lower()
        if verdict not in ('keep', 'reject'):
            if 'rating' in entry:
                try:
                    rating = float(entry['rating'])
                except (TypeError, ValueError):
                    return None
                verdict = 'reject' if likert_to_verdict(rating) == 'reject' else 'keep'
                out[i] = (verdict, rating, str(entry.get('reason', ''))[:200])
                continue
            return None
        out[i] = (verdict, None, str(entry.get('reason', ''))[:200])
    return out


def _parse_rating_axis(
    axis: object, indices: list[int],
) -> dict[int, tuple[str, float, str]] | None:
    """1-5 Likert axis (collocation / relation / particle). ``None`` on any
    missing/malformed requested index — see :func:`_parse_verdict_axis`.
    """
    if not isinstance(axis, dict):
        return None
    out: dict[int, tuple[str, float, str]] = {}
    for i in indices:
        entry = axis.get(str(i))
        if not isinstance(entry, dict):
            return None
        rating_raw = entry.get('rating', entry.get('0'))
        try:
            rating = float(rating_raw)
        except (TypeError, ValueError):
            return None
        reason = str(entry.get('reason', entry.get('1', '')) or '')[:200]
        out[i] = (likert_to_verdict(rating), rating, reason)
    return out
