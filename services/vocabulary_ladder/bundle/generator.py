# services/vocabulary_ladder/bundle/generator.py
"""``BundleGenerator`` — TASK-815: one ``vocab_bundle_generation`` call/sense.

Replaces, for a bundle-mode sense, the fan-out in
``VocabAssetPipeline._generate_for_sense_impl`` that submits up to 10
separate futures (P2 x2 variants, P3 x2, up to 2 split levels x2, typed x2)
with ONE ``call_llm`` producing both variants A and B together, per
ADR-028 Decision §4.

Partial-failure policy (per the Phase 2 brief): if a block fails its schema/
validator gate, fall back to the EXISTING per-generator call for ONLY that
asset family and variant (at most one fallback call per failed family) —
quality never drops below the current per-generator pipeline, and a total
bundle failure degrades all the way back to today's full per-generator call
graph (worse latency for that one sense, never worse output).

NOT wired into ``asset_pipeline.py`` yet — see
``wiki/tasklist/exercise-gen-cost.phase2-wiring.patch`` for the exact diff.
This module is self-contained and safe to import with zero effect on
production behaviour (nothing calls it yet).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from services.llm_service import call_llm
from services.prompt_service import get_template_config
from services.vocabulary_ladder.asset_generators._renderer import render_template
from services.vocabulary_ladder.asset_generators.l4_morphology import (
    MorphologySlotGenerator,
)
from services.vocabulary_ladder.asset_generators.l8_repair import (
    CollocationRepairGenerator,
)
from services.vocabulary_ladder.asset_generators.prompt2_exercises import (
    ExerciseAssetGenerator,
)
from services.vocabulary_ladder.asset_generators.prompt3_transforms import (
    TransformAssetGenerator,
)
from services.vocabulary_ladder.asset_generators import typed_llm
from services.vocabulary_ladder.bundle import mapping
from services.vocabulary_ladder.config import get_sentence_target

logger = logging.getLogger(__name__)

TASK_NAME = 'vocab_bundle_generation'
_PIPELINE = 'vocab_ladder'

_LANG_ID_TO_CODE: dict[int, str] = {1: 'zh', 2: 'en', 3: 'ja'}

# ADR-028's "≤2 real calls per step" rule: one primary attempt, one retry.
_MAX_ATTEMPTS = 2

# Bundle-call max_tokens, per language. Derived from summing the PER-COMPONENT
# completion_tokens MAX observed in the Phase 0 baseline
# (data/eval/runs/baseline_{en,ja}/*.json llm_calls: vocab_prompt2_exercises
# max 11385, vocab_prompt3_transforms max 6471, ladder_l4_morphology_generation
# max 1921, ladder_syn_ant_generation max 2017, ladder_word_family_generation
# max 1799, ladder_particle_selection_generation max 1908 — L8's own task_name
# logged zero completion_tokens rows in the baseline sample, so it borrows L4's
# magnitude as a stand-in), doubled for variants A+B, plus headroom. This is a
# WORST-CASE ceiling assuming every component's max co-occurs on one sense in
# one call, which baseline per-sense data suggests is rare — a real bundle-call
# measurement (blocked while the Phase 1 eval run is in flight; no paid LLM
# calls from this task) should replace these with observed p99s before "on"
# mode ships. Sized as a cap, not a target: it only affects the worst case,
# never the typical-cost path Decision §1 is measured against.
_MAX_TOKENS_BY_LANGUAGE: dict[int, int] = {
    1: 40000,  # zh: L1(in P2)+L3+L6 + L7 + L4 + syn_ant, x2 variants (L5/L8 disabled today)
    2: 44000,  # en: L1+L3+L5+L6 + L7 + L4 + L8 + syn_ant + word_family, x2 variants
    3: 34000,  # ja: L3+L6 + L7 + particle_selection + syn_ant, x2 variants (no L1; L5/L8 disabled)
}
_DEFAULT_MAX_TOKENS = 40000

# Which typed type_codes this module knows how to place into the bundle
# prompt/response. A type registered later but not listed here is simply
# never requested from the bundle (falls through to the existing per-type
# call every time) — safe by construction, never a silent drop of a type the
# bundle prompt doesn't know how to ask for.
_KNOWN_TYPED_CODES = frozenset({
    'synonym_antonym_match', 'word_family', 'particle_selection',
})
_TYPED_BUNDLE_KEY = {
    'synonym_antonym_match': 'syn_ant',
    'word_family': 'word_family',
    'particle_selection': '4',  # ja: particle_selection IS the bundle's L4 key
}


@dataclass
class BundleResult:
    """Mirrors the shape ``VocabAssetPipeline``'s ``variant_results`` dict
    already holds per ``(prompt_type, variant_key)`` — see ``to_variant_results``.
    """

    p2: dict[str, dict | None] = field(default_factory=dict)
    p3: dict[str, dict] = field(default_factory=dict)          # {'A': {} | {'level_7': ...}}
    l4: dict[str, dict | None] = field(default_factory=dict)
    l8: dict[str, dict | None] = field(default_factory=dict)
    typed: dict[str, tuple[dict, list[str]]] = field(default_factory=dict)  # {'A': (fragments, failures)}
    ok: bool = False                 # whether the bundle LLM call itself succeeded
    fallback_calls: list[str] = field(default_factory=list)     # e.g. ['p2:A', 'l4:B']
    raw: dict | None = None          # the parsed {"A": {...}, "B": {...}} bundle response, for shadow-mode logging

    def to_variant_results(self) -> dict[tuple[str, str], object]:
        """Flatten into the ``{(prompt_type, variant_key): value}`` shape
        ``VocabAssetPipeline._generate_for_sense_impl``'s step 4 already reads.
        """
        out: dict[tuple[str, str], object] = {}
        for variant_key in ('A', 'B'):
            out[('p2', variant_key)] = self.p2.get(variant_key)
            out[('p3', variant_key)] = self.p3.get(variant_key, {})
            out[(f'l4', variant_key)] = self.l4.get(variant_key, {})
            out[(f'l8', variant_key)] = self.l8.get(variant_key, {})
            out[('typed', variant_key)] = self.typed.get(variant_key, ({}, []))
        return out


class BundleGenerator:
    """One ``vocab_bundle_generation`` call/sense, with per-family fallback."""

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
    # Public entry point
    # ------------------------------------------------------------------

    def generate_bundle(
        self,
        sense_id: int,
        core_asset: dict,
        active_levels: list[int],
        semantic_class: str | None,
        capability_context: dict | None,
        p3_expected_levels: list[int],
        split_levels_wanted: list[int],
        typed_wanted_codes: set[str] | None,
        variants: dict[str, dict],
        l7_correct_indices: dict[str, list[int]],
    ) -> BundleResult:
        """Generate every requested asset family for BOTH variants in one call.

        Args:
            active_levels: this sense's planned ladder levels (post capability
                gating) — same value ``asset_pipeline`` already computes.
            p3_expected_levels: the P3-family levels worth asking for (level 7
                only ever comes from here in practice, since 4/8 are split).
            split_levels_wanted: which of {4, 8} to request via the split
                contract (mirrors ``asset_pipeline``'s ``split_levels``).
            typed_wanted_codes: type_codes to request, or ``None`` for "every
                applicable type" (mirrors ``asset_pipeline``'s
                ``typed_wanted_codes`` — TASK-811 level-scoped regen is
                out of scope for bundle mode; callers should only reach this
                method on an unscoped (``levels is None``) regen).
            variants: ``{'A': {'sentence_assignments': ...}, 'B': {...}}``.
            l7_correct_indices: ``{'A': [...], 'B': [...]}``.

        Returns:
            A :class:`BundleResult`. Never raises for a bundle-call failure —
            that degrades to ``ok=False`` and every family falling back.
        """
        result = BundleResult()

        try:
            raw = self._call_bundle(sense_id, core_asset, active_levels, variants)
        except Exception as exc:
            logger.warning(
                "Bundle generation call failed for sense %s: %s — falling back "
                "to per-generator calls for every family/variant", sense_id, exc,
            )
            raw = None

        result.ok = raw is not None
        result.raw = raw

        p2_levels = [lv for lv in active_levels if lv in {1, 3, 5, 6}]
        want_l7 = 7 in p3_expected_levels
        want_l4 = 4 in split_levels_wanted
        want_l8 = 8 in split_levels_wanted
        wanted_typed = (
            _typed_applicable_codes(self.language_id, semantic_class, capability_context)
            if typed_wanted_codes is None
            else set(typed_wanted_codes)
        )
        wanted_typed &= _KNOWN_TYPED_CODES

        for variant_key, vcfg in variants.items():
            sentence_assignments = vcfg['sentence_assignments']
            raw_variant = (raw or {}).get(variant_key) if raw else None

            self._resolve_p2(
                result, sense_id, core_asset, p2_levels, sentence_assignments,
                variant_key, raw_variant,
            )
            self._resolve_l7(
                result, sense_id, core_asset, active_levels, sentence_assignments,
                l7_correct_indices.get(variant_key), semantic_class,
                capability_context, variant_key, raw_variant, want_l7,
            )
            self._resolve_l4(
                result, sense_id, core_asset, sentence_assignments,
                variant_key, raw_variant, want_l4,
            )
            self._resolve_l8(
                result, sense_id, core_asset, sentence_assignments,
                variant_key, raw_variant, want_l8,
            )
            self._resolve_typed(
                result, sense_id, core_asset, semantic_class, sentence_assignments,
                capability_context, variant_key, raw_variant, wanted_typed,
            )

        return result

    # ------------------------------------------------------------------
    # The bundle LLM call
    # ------------------------------------------------------------------

    def _call_bundle(
        self, sense_id: int, core_asset: dict, active_levels: list[int],
        variants: dict[str, dict],
    ) -> dict | None:
        prompt_vars = self._prompt_vars(core_asset, active_levels, variants)
        prompt_text = render_template(self.cfg['template'], **prompt_vars)
        cfg = self.cfg
        max_tokens = _MAX_TOKENS_BY_LANGUAGE.get(self.language_id, _DEFAULT_MAX_TOKENS)

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                raw = call_llm(
                    prompt_text,
                    model=cfg['model'],
                    provider=cfg['provider'],
                    temperature=0.4,
                    max_tokens=max_tokens,
                    response_format='json_object',
                    pipeline=_PIPELINE,
                    task_name=TASK_NAME,
                    template_version=cfg.get('version'),
                    language_code=_LANG_ID_TO_CODE.get(self.language_id),
                    call_role='retry' if attempt > 1 else 'primary',
                    sense_id=sense_id,
                    allow_internal_repair=False,
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Bundle generation attempt %d failed for sense %s: %s",
                    attempt, sense_id, exc,
                )
                continue

            if not isinstance(raw, dict) or not any(k in raw for k in ('A', 'B')):
                last_exc = RuntimeError(
                    f'bundle response missing "A"/"B" top-level keys (got '
                    f'{type(raw).__name__})'
                )
                logger.warning(
                    "Bundle generation attempt %d for sense %s: %s",
                    attempt, sense_id, last_exc,
                )
                continue
            return raw

        if last_exc is not None:
            raise last_exc
        return None

    def _prompt_vars(
        self, core_asset: dict, active_levels: list[int], variants: dict[str, dict],
    ) -> dict:
        sentences = core_asset.get('sentences', [])

        def sentences_json(sentence_assignments: dict[int, int]) -> str:
            # The bundle prompt reads the FULL sentence pool (like every
            # per-generator prompt does) — sentence_assignments only tells it
            # which index each level should anchor to, passed separately below.
            return json.dumps(
                [
                    {'index': i, 'text': s.get('text', ''), 'target': get_sentence_target(s)}
                    for i, s in enumerate(sentences)
                ],
                ensure_ascii=False,
            )

        sa_a = variants['A']['sentence_assignments']
        sa_b = variants['B']['sentence_assignments']
        l7_a = variants['A'].get('l7_correct_indices', [0, 1, 2])
        l7_b = variants['B'].get('l7_correct_indices', [6, 7, 9])

        l8_idx_a = sa_a.get(8, 4)
        l8_idx_b = sa_b.get(8, 4)
        l8_text_a = sentences[l8_idx_a].get('text', '') if 0 <= l8_idx_a < len(sentences) else ''
        l8_text_b = sentences[l8_idx_b].get('text', '') if 0 <= l8_idx_b < len(sentences) else ''

        return {
            'word': self._extract_lemma(core_asset),
            'pos': core_asset.get('pos', ''),
            'semantic_class': core_asset.get('semantic_class', ''),
            'complexity_tier': self._extract_tier(core_asset),
            'definition': core_asset.get('definition', ''),
            'primary_collocate': core_asset.get('primary_collocate') or 'null',
            'register': core_asset.get('register') or 'neutral',
            'sense_fingerprint': core_asset.get('sense_fingerprint') or '',
            'sentences_json_a': sentences_json(sa_a),
            'sentences_json_b': sentences_json(sa_b),
            'morphological_forms_json': json.dumps(
                core_asset.get('morphological_forms', []), ensure_ascii=False,
            ),
            'active_levels_json': json.dumps([str(lv) for lv in active_levels]),
            'level_3_sentence_index_a': sa_a.get(3, 0),
            'level_3_sentence_index_b': sa_b.get(3, 6),
            'level_4_sentence_index_a': sa_a.get(4, 1),
            'level_4_sentence_index_b': sa_b.get(4, 7),
            'level_5_sentence_index_a': sa_a.get(5, 2),
            'level_5_sentence_index_b': sa_b.get(5, 8),
            'level_6_sentence_index_a': sa_a.get(6, 3),
            'level_6_sentence_index_b': sa_b.get(6, 9),
            'level_7_correct_indices_a': json.dumps(l7_a),
            'level_7_correct_indices_b': json.dumps(l7_b),
            'level_8_sentence_text_a': l8_text_a,
            'level_8_sentence_text_b': l8_text_b,
            'level_8_collocate_word': (core_asset.get('primary_collocate') or '').strip() or 'null',
        }

    @staticmethod
    def _extract_lemma(core_asset: dict) -> str:
        sentences = core_asset.get('sentences', [])
        return get_sentence_target(sentences[0]) if sentences else ''

    @staticmethod
    def _extract_tier(core_asset: dict) -> str:
        sentences = core_asset.get('sentences', [])
        return sentences[0].get('complexity_tier', 'T3') if sentences else 'T3'

    # ------------------------------------------------------------------
    # Per-family resolution: map bundle output, fall back on failure
    # ------------------------------------------------------------------

    def _resolve_p2(
        self, result: BundleResult, sense_id, core_asset, p2_levels,
        sentence_assignments, variant_key, raw_variant,
    ) -> None:
        if not p2_levels:
            result.p2[variant_key] = {}
            return
        content, errors = (
            mapping.build_p2_content(raw_variant, p2_levels, sentence_assignments, self.language_id)
            if raw_variant is not None else ({}, ['bundle call unavailable'])
        )
        if not errors:
            result.p2[variant_key] = content
            return
        logger.info(
            "Bundle P2 fallback for sense %s variant %s: %s", sense_id, variant_key, errors[:3],
        )
        result.fallback_calls.append(f'p2:{variant_key}')
        gen = ExerciseAssetGenerator(self.db, self.language_id)
        result.p2[variant_key] = gen.generate(
            sense_id, core_asset, p2_levels, sentence_assignments,
        )

    def _resolve_l7(
        self, result: BundleResult, sense_id, core_asset, active_levels,
        sentence_assignments, l7_correct_indices, semantic_class,
        capability_context, variant_key, raw_variant, want_l7,
    ) -> None:
        if not want_l7:
            result.p3[variant_key] = {}
            return
        fragment, errors = (
            mapping.build_l7_fragment(raw_variant, self.language_id)
            if raw_variant is not None else ({}, ['bundle call unavailable'])
        )
        if not errors and fragment:
            result.p3[variant_key] = fragment
            return
        logger.info(
            "Bundle L7 fallback for sense %s variant %s: %s", sense_id, variant_key, errors[:3],
        )
        result.fallback_calls.append(f'l7:{variant_key}')
        gen = TransformAssetGenerator(self.db, self.language_id)
        fallback = gen.generate(
            sense_id, core_asset, active_levels, sentence_assignments,
            l7_correct_indices, None, semantic_class, capability_context,
        )
        result.p3[variant_key] = fallback if fallback is not None else {}

    def _resolve_l4(
        self, result: BundleResult, sense_id, core_asset, sentence_assignments,
        variant_key, raw_variant, want_l4,
    ) -> None:
        if not want_l4:
            result.l4[variant_key] = {}
            return
        if raw_variant is None:
            # Whole bundle call failed — not the same as "the model omitted
            # this key", which mapping.build_l4_fragment(None, ...) treats as
            # a clean skip. A total failure must always fall back.
            fragment, errors = None, ['bundle call unavailable']
        else:
            raw_block = raw_variant.get('4')
            fragment, errors = mapping.build_l4_fragment(raw_block, sentence_assignments.get(4, 1), self.language_id)
        if not errors:
            result.l4[variant_key] = fragment
            return
        logger.info(
            "Bundle L4 fallback for sense %s variant %s: %s", sense_id, variant_key, errors[:3],
        )
        result.fallback_calls.append(f'l4:{variant_key}')
        gen = MorphologySlotGenerator(self.db, self.language_id)
        result.l4[variant_key] = gen.generate(sense_id, core_asset, sentence_assignments)

    def _resolve_l8(
        self, result: BundleResult, sense_id, core_asset, sentence_assignments,
        variant_key, raw_variant, want_l8,
    ) -> None:
        if not want_l8:
            result.l8[variant_key] = {}
            return
        if raw_variant is None:
            fragment, errors = None, ['bundle call unavailable']
        else:
            raw_block = raw_variant.get('8')
            fragment, errors = mapping.build_l8_fragment(raw_block, sentence_assignments.get(8, 4), self.language_id)
        if not errors:
            result.l8[variant_key] = fragment
            return
        logger.info(
            "Bundle L8 fallback for sense %s variant %s: %s", sense_id, variant_key, errors[:3],
        )
        result.fallback_calls.append(f'l8:{variant_key}')
        gen = CollocationRepairGenerator(self.db, self.language_id)
        result.l8[variant_key] = gen.generate(sense_id, core_asset, sentence_assignments)

    def _resolve_typed(
        self, result: BundleResult, sense_id, core_asset, semantic_class,
        sentence_assignments, capability_context, variant_key, raw_variant,
        wanted_typed: set[str],
    ) -> None:
        if not wanted_typed:
            result.typed[variant_key] = ({}, [])
            return

        fragments: dict = {}
        failed_codes: list[str] = []
        for type_code in wanted_typed:
            if raw_variant is None:
                # Same reasoning as _resolve_l4/_resolve_l8: a total bundle
                # failure must always fall back, unlike an omitted key in an
                # otherwise-successful response.
                failed_codes.append(type_code)
                continue
            bundle_key = _TYPED_BUNDLE_KEY.get(type_code, type_code)
            raw_block = raw_variant.get(bundle_key)
            gen_cls = typed_llm.generator_class(type_code)
            sentence_index = _typed_sentence_index(gen_cls, core_asset, sentence_assignments)
            fragment, errors = mapping.build_typed_fragment(
                type_code, raw_block, sentence_index, self.language_id, sense_id,
            )
            if not errors:
                fragments.update(fragment)
                continue
            failed_codes.append(type_code)

        if failed_codes:
            logger.info(
                "Bundle typed fallback for sense %s variant %s: %s",
                sense_id, variant_key, failed_codes,
            )
            result.fallback_calls.extend(f'typed:{c}:{variant_key}' for c in failed_codes)
            fallback_fragments, fallback_failures = typed_llm.generate_all(
                self.db, self.language_id, sense_id, core_asset, semantic_class,
                sentence_assignments, capability_context, type_codes=set(failed_codes),
            )
            fragments.update(fallback_fragments)
            failed_codes = fallback_failures

        result.typed[variant_key] = (fragments, failed_codes)


def _typed_applicable_codes(language_id, semantic_class, capability_context) -> set[str]:
    return {
        cap['type_code']
        for cap in typed_llm.applicable_types(language_id, semantic_class, capability_context)
    }


def _typed_sentence_index(gen_cls, core_asset: dict, sentence_assignments: dict[int, int]) -> int:
    """Best-effort sentence index for a typed block's remap step.

    Mirrors ``TypedLLMGenerator._sentence_index``'s default (the variant's
    slot for the type, clamped to the pool) closely enough for remap — the
    exact value only matters for ``fragment.setdefault('sentence_index', ...)``
    bookkeeping the renderer reads later, not for validation.
    """
    if gen_cls is None:
        return 0
    slot = getattr(gen_cls, 'SENTENCE_SLOT', None)
    sentences = (core_asset or {}).get('sentences') or []
    if slot is None or not sentences:
        return 0
    index = sentence_assignments.get(slot, 0)
    if index >= len(sentences):
        index = len(sentences) - 1
    return max(index, 0)
