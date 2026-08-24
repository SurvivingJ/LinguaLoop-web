# services/vocabulary_ladder/asset_pipeline.py
"""
Vocabulary Asset Pipeline Orchestrator

Runs Prompts 1-3 sequentially for a word sense, validates outputs,
and stores immutable assets in the word_assets table. This is the
offline pipeline — runs at admin upload time, not in the request path.

Usage:
    pipeline = VocabAssetPipeline()
    result = pipeline.generate_for_sense(sense_id=42, language_id=2)
    # result = {'sense_id': 42, 'assets': {...}, 'errors': [...]}
"""

import logging
from concurrent.futures import as_completed
from datetime import datetime, timezone
from uuid import uuid4

from services.exercise_generation.judges.base import (
    BatchModeThreadPoolExecutor, JudgeUnavailable,
)
from services.supabase_factory import get_supabase_admin
from services.timing import stage, log_stage_seconds
from services.vocabulary_ladder.config import (
    compute_active_levels, active_levels_for_context, normalize_semantic_class,
    prompt3_levels_for_context, capability_context_from_core,
    SENTENCE_SOURCE_MINED, SPLIT_LEVEL_TASKS,
    SENTENCE_ASSIGNMENTS_A, SENTENCE_ASSIGNMENTS_B,
    L7_CORRECT_INDICES_A, L7_CORRECT_INDICES_B,
)
from services.vocabulary_ladder.asset_generators.prompt1_core import CoreAssetGenerator
from services.vocabulary_ladder.asset_generators.prompt2_exercises import ExerciseAssetGenerator
from services.vocabulary_ladder.asset_generators.prompt3_transforms import TransformAssetGenerator
from services.vocabulary_ladder.asset_generators.l4_morphology import MorphologySlotGenerator
from services.vocabulary_ladder.asset_generators.l8_repair import CollocationRepairGenerator
from services.vocabulary_ladder.asset_generators import typed_llm
from services.vocabulary_ladder.collocation_grounding import (
    GROUNDING_ASSERTED, GROUNDING_CORPUS, CollocationGrounder, ground_core_asset,
)
from services.vocabulary_ladder.validators import VocabAssetValidator

logger = logging.getLogger(__name__)

# language_id → llm_calls/generation_stage_timings.language_code. Same
# hardcoded map used by the asset_generators — see prompt1_core.py.
_LANG_ID_TO_CODE: dict[int, str] = {1: 'zh', 2: 'en', 3: 'ja'}


class VocabAssetPipeline:
    """Orchestrates the three-prompt asset generation for vocabulary words."""

    def __init__(self, db=None):
        self.db = db or get_supabase_admin()
        self.validator = VocabAssetValidator()

    def generate_for_sense(
        self,
        sense_id: int,
        language_id: int,
        force: bool = False,
        batch_id: str | None = None,
    ) -> dict:
        """Generate all assets for a single word sense.

        Thin wrapper around ``_generate_for_sense_impl`` that persists the
        stage-timing bucket exactly once regardless of which of the impl's
        several early-return paths fired — mirrors the run()/_run_impl split
        in test_generation.orchestrator. ``batch_id`` doubles as
        generation_stage_timings.run_id, so a whole ladder batch's wall clock
        can be summed by run_id without a time-window guess.
        """
        batch_id = batch_id or str(uuid4())
        result = self._generate_for_sense_impl(sense_id, language_id, force, batch_id)
        log_stage_seconds(
            result.get('stage_seconds') or {},
            pipeline='vocab_ladder',
            language_code=_LANG_ID_TO_CODE.get(language_id),
            artifact_id=str(sense_id),
            run_id=batch_id,
        )
        return result

    def _generate_for_sense_impl(
        self,
        sense_id: int,
        language_id: int,
        force: bool,
        batch_id: str,
    ) -> dict:
        """Generate all assets for a single word sense.

        Runs Prompt 1 once (10 sentences), then Prompts 2 and 3 twice each
        (variants A and B) using different sentence assignments. Variants
        run in parallel for latency parity with the old single-variant path.

        Args:
            sense_id: The dim_word_senses ID.
            language_id: Language ID (2 = English).
            force: If True, regenerate even if assets exist.
            batch_id: Batch UUID (str) for tracking — always set by the
                ``generate_for_sense`` wrapper before this runs.

        Returns:
            {'sense_id': int, 'status': 'success'|'partial'|'failed', 'errors': [...]}
        """
        result = {'sense_id': sense_id, 'status': 'failed', 'errors': [], 'warnings': []}
        # TASK-737: per-stage wall clock for this sense, folded into `result`
        # so run_content_build.py's canary/ladder phases can report where the
        # ~5.5 min/sense baseline actually goes instead of only the total.
        # Persisted to generation_stage_timings by the generate_for_sense
        # wrapper once this returns, on every path (TASK-758).
        stage_seconds: dict[str, float] = {}
        result['stage_seconds'] = stage_seconds

        # Check existing assets
        if not force and self._assets_exist(sense_id):
            result['status'] = 'skipped'
            return result

        # Step 1: Fetch corpus sentences (reuse existing content)
        with stage('fetch_corpus', stage_seconds):
            corpus_sentences = self._fetch_corpus_sentences(sense_id, language_id)

        # Step 2: Run Prompt 1 — Core classification + 10 sentences
        p1_gen = CoreAssetGenerator(self.db, language_id)
        with stage('p1_generate', stage_seconds):
            core_asset = p1_gen.generate(sense_id, corpus_sentences)

        if core_asset is None:
            result['errors'].append('Prompt 1 generation failed')
            return result

        p1_valid, p1_errors, p1_warnings = self.validator.validate_prompt1(
            core_asset, language_id,
        )
        if not p1_valid:
            with stage('p1_repair', stage_seconds):
                repaired = p1_gen.repair(core_asset, p1_errors, sense_id)
            if repaired:
                p1_valid, p1_errors, p1_warnings = self.validator.validate_prompt1(
                    repaired, language_id,
                )
                if p1_valid:
                    core_asset = repaired
                    logger.info("Prompt 1 repair succeeded for sense %s", sense_id)
        if not p1_valid:
            result['errors'].extend(p1_errors)
            self._store_asset(sense_id, language_id, 'prompt1_core', core_asset,
                              p1_gen.model, batch_id, is_valid=False,
                              validation_errors=p1_errors)
            return result

        if p1_warnings:
            result['warnings'].extend(p1_warnings)
            logger.info(
                "Prompt 1 warnings for sense %s: %s", sense_id, p1_warnings,
            )

        # Sentence-tier hard gate (TASK-524). Deterministic and free, so it
        # runs *before* the LLM judge: a C2-lexis sentence for an A1 word is
        # rejected on a frequency table rather than on a judgement call, and
        # the judge's per-sentence spend is reserved for what only a model can
        # assess. Rejected sentences get the same in-place repair treatment as
        # judge rejects — indices are never disturbed.
        with stage('tier_gate', stage_seconds):
            tier_warnings, tier_stats = self._tier_gate_sentences(
                core_asset, language_id, p1_gen, sense_id,
            )
        if tier_warnings:
            p1_warnings = (p1_warnings or []) + tier_warnings
            result['warnings'].extend(tier_warnings)
        result['tier_gate'] = tier_stats

        # P1 sentence-corpus judge (Phase 4 / TASK-404). Runs after structural
        # validation and before the P2/P3 fan-out, so off-sense / off-register /
        # not-whole-word sentences are caught before every downstream level
        # inherits them. Fail-open and index-preserving (decision 4): sentences
        # are never deleted or reordered — rejected ones get one targeted repair
        # attempt, the final per-sentence verdicts are recorded as warnings, and
        # the asset is blocked only if too few acceptable sentences remain.
        with stage('p1_judge', stage_seconds):
            judge_warnings, p1_blocked = self._judge_p1_sentences(
                core_asset, language_id, p1_gen, sense_id,
            )
        if judge_warnings:
            p1_warnings = (p1_warnings or []) + judge_warnings
            result['warnings'].extend(judge_warnings)
        if p1_blocked:
            result['errors'].append(
                'P1 sentence judge: too few acceptable sentences after repair'
            )
            self._store_asset(sense_id, language_id, 'prompt1_core', core_asset,
                              p1_gen.model, batch_id, is_valid=False,
                              validation_errors=result['errors'],
                              validation_warnings=p1_warnings or None)
            return result

        # Collocate grounding (TASK-523 / finding G6). P1 asserts a
        # primary_collocate for every sense and, being a model, never says "no
        # collocate". Grade the assertion against a frequency source and pin
        # the verdict onto the asset before it is stored, so L5's gate, L8's
        # prompt and every rendered exercise's provenance all read the same
        # tag. Never blocks: an unattested pair is annotated, not deleted.
        with stage('collocate_grounding', stage_seconds):
            grounding = ground_core_asset(core_asset, language_id, self.db)
        result['collocate_grounding'] = grounding.to_tag()
        if grounding.status == GROUNDING_ASSERTED:
            message = (
                f"Collocate {core_asset.get('primary_collocate')!r} is "
                f"llm_asserted — {grounding.reason}"
            )
            p1_warnings = (p1_warnings or []) + [message]
            result['warnings'].append(message)

        self._store_asset(sense_id, language_id, 'prompt1_core', core_asset,
                          p1_gen.model, batch_id,
                          validation_warnings=p1_warnings or None)
        self._update_vocabulary_metadata(sense_id, core_asset)

        semantic_class = normalize_semantic_class(core_asset.get('semantic_class'))

        # Matrix-gated planning (TASK-514/B5). This used to be a bare
        # compute_active_levels(), so L4 was planned for every word and the
        # pipeline relied on the model returning null morphology for languages
        # that have none — which it does not reliably do, yielding invented ZH
        # "inflections". Narrow the plan by what this word can actually
        # support: a capability row requiring morph_forms>=2 cannot fire for a
        # word P1 gave 0 or 1 forms.
        matrix_levels = compute_active_levels(semantic_class, language_id)
        capability_context = self._capability_context(core_asset)
        active_levels = active_levels_for_context(
            semantic_class, language_id, capability_context,
        )
        dropped = [lv for lv in matrix_levels if lv not in active_levels]
        if dropped:
            logger.info(
                "Sense %s: capability requirements dropped level(s) %s "
                "(semantic_class=%s, morph_forms=%d)",
                sense_id, dropped, semantic_class,
                len(core_asset.get('morphological_forms') or []),
            )

        # Aggressively gate L5 (Collocation Gap) on corpus evidence of a fixed
        # collocation. P1 happily returns 'advertising' as a primary_collocate
        # for "personalize", which produces synonym-soup distractors. Drop L5
        # entirely unless we have a high-PMI corpus_collocations row backing
        # the (lemma, collocate) pair.
        if 5 in active_levels and not self._collocation_is_fixed(
            core_asset, language_id,
        ):
            active_levels = [lv for lv in active_levels if lv != 5]
            logger.info(
                "Dropping L5 for sense %s — primary_collocate %r failed PMI gate",
                sense_id, core_asset.get('primary_collocate'),
            )

        # Step 3: Run every generation prompt for both variants in parallel
        p2_gen = ExerciseAssetGenerator(self.db, language_id)
        p3_gen = TransformAssetGenerator(self.db, language_id)
        # TASK-520: L4 and L8 have their own prompts, models and retries. They
        # are separate futures precisely so a morphology failure costs the
        # morphology item and nothing else — under the monolith it forced a
        # retry of spot-incorrect and repair as well.
        split_gens = {
            4: MorphologySlotGenerator(self.db, language_id),
            8: CollocationRepairGenerator(self.db, language_id),
        }

        # The P3-family levels the generators will actually request, after
        # per-type gating (TASK-514/B5). The validator must be held to the same
        # list — otherwise a correctly-suppressed L4 reads back as
        # "Missing level_4" and marks an otherwise-good asset invalid.
        p3_expected_levels = prompt3_levels_for_context(
            active_levels, semantic_class, language_id, capability_context,
        )
        split_levels = [lv for lv in p3_expected_levels if lv in SPLIT_LEVEL_TASKS]

        variants = {
            'A': {
                'sentence_assignments': SENTENCE_ASSIGNMENTS_A,
                'l7_correct_indices': L7_CORRECT_INDICES_A,
            },
            'B': {
                'sentence_assignments': SENTENCE_ASSIGNMENTS_B,
                'l7_correct_indices': L7_CORRECT_INDICES_B,
            },
        }

        variant_results = {}
        # BatchModeThreadPoolExecutor, not the bare one: batch mode is
        # thread-local, so plain pool threads judged fail-*open* for the whole
        # of P2/P3 and the split/typed levels — only P1, which runs on this
        # thread, was ever genuinely fail-closed. See judges/base.py.
        #
        # max_workers=12 (was 8, TASK-737): up to 2 variants x (P2 + P3 +
        # up to 2 split levels + typed) = up to 10 futures. At 8 workers, 2
        # of those queued behind the rest every sense — a small but free
        # latency win to remove, since each future is independently CPU/IO
        # light on this thread (the wait is all downstream LLM latency).
        with stage('fan_out', stage_seconds), \
                BatchModeThreadPoolExecutor(max_workers=12) as pool:
            futures = {}
            for variant_key, cfg in variants.items():
                # Submit P2 variant
                futures[pool.submit(
                    p2_gen.generate, sense_id, core_asset, active_levels,
                    cfg['sentence_assignments'],
                )] = ('p2', variant_key)
                # Submit P3 variant. semantic_class + capability_context turn
                # on per-type gating inside the generator (TASK-514/B5) so P3
                # only asks for spot-incorrect when an enabled capability row
                # for that *type* can actually fire.
                futures[pool.submit(
                    p3_gen.generate, sense_id, core_asset, active_levels,
                    cfg['sentence_assignments'], cfg['l7_correct_indices'],
                    None, semantic_class, capability_context,
                )] = ('p3', variant_key)
                # Submit the split levels. Already gated by p3_expected_levels,
                # so each generator only has to decide whether *this sense*
                # gives it a usable sentence.
                for level in split_levels:
                    futures[pool.submit(
                        split_gens[level].generate, sense_id, core_asset,
                        cfg['sentence_assignments'],
                    )] = (f'l{level}', variant_key)
                # Type-registered LLM generators (TASK-522 syn/ant +
                # word_family, TASK-527 particle_selection). One future per
                # variant rather than per type: they share a driver that
                # already walks the capability matrix, and the matrix decides
                # which of them apply to this word.
                futures[pool.submit(
                    typed_llm.generate_all,
                    self.db, language_id, sense_id, core_asset, semantic_class,
                    cfg['sentence_assignments'], capability_context,
                )] = ('typed', variant_key)

            for future in as_completed(futures):
                prompt_type, variant_key = futures[future]
                try:
                    asset = future.result()
                    variant_results[(prompt_type, variant_key)] = asset
                except JudgeUnavailable:
                    # A judge outage during a batch aborts the batch. Letting
                    # this fall into the generic handler below would downgrade
                    # a loud stop into "variant failed, carry on" — quieter
                    # than the fail-open bug it replaced.
                    raise
                except Exception as e:
                    logger.error("Variant %s_%s failed for sense %s: %s",
                                 prompt_type, variant_key, sense_id, e)
                    variant_results[(prompt_type, variant_key)] = None

        # Step 4: Validate and store each variant
        for variant_key in ('A', 'B'):
            # P2 variant
            p2_asset = variant_results.get(('p2', variant_key))
            asset_type = f'prompt2_exercises_{variant_key}'
            if p2_asset is None:
                result['errors'].append(f'Prompt 2 variant {variant_key} generation failed')
            else:
                p2_valid, p2_errors = self.validator.validate_prompt2(p2_asset, active_levels)
                self._store_asset(sense_id, language_id, asset_type, p2_asset,
                                  p2_gen.model, batch_id, is_valid=p2_valid,
                                  validation_errors=p2_errors if not p2_valid else None)
                if not p2_valid:
                    result['errors'].extend(
                        [f'[{variant_key}] {e}' for e in p2_errors])

            # P3-family variant. The monolith's level_7 and the split levels'
            # fragments are merged back into ONE prompt3_transforms_X asset:
            # the renderer and the validator keep reading the pre-split shape,
            # so the split is invisible downstream (and A/B behaviour is
            # unchanged). Each contributor reports its own failure, because
            # "morphology failed" and "spot-incorrect failed" are now genuinely
            # different events with different fixes.
            p3_sources = [('P3', variant_results.get(('p3', variant_key)))]
            for level in split_levels:
                p3_sources.append(
                    (f'L{level}', variant_results.get((f'l{level}', variant_key)))
                )

            p3_asset: dict | None = None
            for label, fragment in p3_sources:
                if fragment is None:
                    result['errors'].append(
                        f'Prompt 3 ({label}) variant {variant_key} generation failed'
                    )
                    continue
                p3_asset = {**(p3_asset or {}), **fragment}

            if p3_asset is not None:
                asset_type = f'prompt3_transforms_{variant_key}'
                p3_valid, p3_errors = self.validator.validate_prompt3(
                    p3_asset, p3_expected_levels)
                self._store_asset(sense_id, language_id, asset_type, p3_asset,
                                  p3_gen.model, batch_id, is_valid=p3_valid,
                                  validation_errors=p3_errors if not p3_valid else None)
                if not p3_valid:
                    result['errors'].extend(
                        [f'[{variant_key}] {e}' for e in p3_errors])

            # Type-registered LLM variant. Stored even when empty so the
            # renderer can tell "no applicable types for this word" (an empty
            # asset) from "generation never ran" (no asset at all).
            typed_result = variant_results.get(('typed', variant_key))
            if typed_result is None:
                result['errors'].append(
                    f'Typed LLM generators variant {variant_key} failed'
                )
            else:
                fragments, typed_failures = typed_result
                self._store_asset(
                    sense_id, language_id, f'llm_types_{variant_key}', fragments,
                    'per-type (see prompt_templates)', batch_id,
                )
                for type_code in typed_failures:
                    result['errors'].append(
                        f'[{variant_key}] {type_code} generation failed'
                    )

        # Determine final status
        if not result['errors']:
            result['status'] = 'success'
        else:
            # Partial if P1 succeeded but some variants failed
            result['status'] = 'partial'

        return result

    @staticmethod
    def _capability_context(core_asset: dict) -> dict:
        """Facts about this word that capability ``requires`` tokens can test.

        Thin alias for :func:`capability_context_from_core` — the renderer
        needs the same facts, so the construction lives in config alongside
        ``requirements_met``.
        """
        return capability_context_from_core(core_asset)

    def generate_batch(
        self,
        sense_ids: list[int],
        language_id: int,
        force: bool = False,
    ) -> dict:
        """Generate assets for multiple word senses.

        Returns:
            {'batch_id': str, 'total': int, 'success': int, 'partial': int,
             'failed': int, 'skipped': int, 'results': [...]}
        """
        batch_id = str(uuid4())
        results = []
        counts = {'success': 0, 'partial': 0, 'failed': 0, 'skipped': 0}

        for sense_id in sense_ids:
            try:
                result = self.generate_for_sense(
                    sense_id, language_id, force=force, batch_id=batch_id,
                )
                results.append(result)
                counts[result['status']] = counts.get(result['status'], 0) + 1
            except JudgeUnavailable:
                # Abort the whole batch rather than marking this one sense
                # failed and generating the remaining senses unjudged.
                raise
            except Exception as e:
                logger.error("Pipeline failed for sense %s: %s", sense_id, e)
                results.append({
                    'sense_id': sense_id, 'status': 'failed',
                    'errors': [str(e)],
                })
                counts['failed'] += 1

        logger.info(
            "Batch %s complete: %d total, %d success, %d partial, %d failed, %d skipped",
            batch_id, len(sense_ids), counts['success'], counts['partial'],
            counts['failed'], counts['skipped'],
        )

        return {
            'batch_id': batch_id,
            'total': len(sense_ids),
            **counts,
            'results': results,
        }

    # ------------------------------------------------------------------
    # Sentence-tier hard gate (TASK-524)
    # ------------------------------------------------------------------

    def _tier_gate_sentences(
        self, core_asset: dict, language_id: int, p1_gen, sense_id: int,
    ) -> tuple[list[str], dict]:
        """Screen P1's sentences on lexical frequency, repairing the misfits.

        Returns ``(warnings, stats)``. ``stats`` feeds the batch report
        (TASK-517) with ``{'tier', 'screened', 'rejected', 'repaired',
        'still_failing'}``.

        Mutates ``core_asset['sentences'][i]['text']`` in place when a repair
        succeeds and never changes their count or order — downstream levels
        reference sentence indices positionally.

        Deliberately never blocks the asset. A sentence set that is entirely
        off-tier is a prompt problem, not a data-integrity problem, and the
        judge that runs next already owns the block decision
        (``P1_MIN_ACCEPTABLE_SENTENCES``). Double-blocking on two different
        criteria would make failures hard to attribute.
        """
        from services.vocabulary_ladder.tier_gate import (
            morph_form_texts, screen_sentences, tier_for_lemma,
        )
        from services.vocabulary_ladder.config import get_sentence_target

        sentences = core_asset.get('sentences') or []
        stats = {'tier': None, 'screened': 0, 'rejected': 0,
                 'repaired': 0, 'still_failing': 0}
        if not sentences:
            return [], stats

        lemma = get_sentence_target(sentences[0])
        tier = tier_for_lemma(lemma, language_id)
        exempt = [lemma] + morph_form_texts(core_asset)
        stats['tier'] = tier
        stats['screened'] = len(sentences)

        verdicts = screen_sentences(
            sentences, language_id, tier, target_word=lemma, exempt=exempt,
        )
        rejected = [i for i, v in enumerate(verdicts) if not v.passed]
        stats['rejected'] = len(rejected)
        if not rejected:
            return [], stats

        reasons = {i: f'lexically too advanced — {verdicts[i].reason}'
                   for i in rejected}
        repaired = p1_gen.repair_sentences(core_asset, rejected, reasons, sense_id)
        if repaired:
            for idx, new_text in repaired.items():
                if 0 <= idx < len(sentences) and isinstance(sentences[idx], dict):
                    sentences[idx]['text'] = new_text
            # Re-screen only what changed; a repair that lands another
            # off-tier sentence must not be recorded as a success.
            redone = sorted(repaired.keys())
            re_verdicts = screen_sentences(
                [sentences[i] for i in redone], language_id, tier,
                target_word=lemma, exempt=exempt,
            )
            for j, idx in enumerate(redone):
                verdicts[idx] = re_verdicts[j]
            stats['repaired'] = sum(1 for i in redone if verdicts[i].passed)

        warnings: list[str] = []
        for i in rejected:
            if verdicts[i].passed:
                continue
            stats['still_failing'] += 1
            warnings.append(
                f'Tier gate: sentence[{i}] {verdicts[i].reason}'
            )

        logger.info(
            "Sense %s tier gate (%s): %d/%d rejected, %d repaired, %d still failing",
            sense_id, tier, stats['rejected'], stats['screened'],
            stats['repaired'], stats['still_failing'],
        )
        return warnings, stats

    # ------------------------------------------------------------------
    # P1 sentence-corpus judge (Phase 4)
    # ------------------------------------------------------------------

    def _judge_p1_sentences(
        self, core_asset: dict, language_id: int, p1_gen, sense_id: int,
    ) -> tuple[list[str], bool]:
        """Judge P1's base sentences, attempt one targeted repair, record warnings.

        Returns ``(warnings, blocked)``. ``warnings`` is a human-readable summary
        (also persisted onto the asset's ``validation_warnings``); ``blocked`` is
        True only when acceptable sentences fall below
        ``P1_MIN_ACCEPTABLE_SENTENCES`` after the repair pass. Fail-open: any
        judge error or length mismatch returns ``([], False)`` and leaves the
        asset untouched.

        Mutates ``core_asset['sentences'][i]['text']`` in place when a repair
        succeeds, but never changes their count or order — downstream levels
        reference sentence indices positionally.
        """
        from services.exercise_generation.judges.p1_sentences import judge_p1_sentences
        from services.vocabulary_ladder.config import (
            get_sentence_target, P1_MIN_ACCEPTABLE_SENTENCES,
        )

        sentences = core_asset.get('sentences') or []
        if not sentences:
            return [], False

        lemma = get_sentence_target(sentences[0])
        definition = core_asset.get('definition', '')
        fingerprint = core_asset.get('sense_fingerprint') or ''
        register = core_asset.get('register') or 'neutral'

        def _run(texts):
            return judge_p1_sentences(
                self.db, lemma=lemma, definition=definition,
                sense_fingerprint=fingerprint, register=register,
                sentences=texts, language_id=language_id,
            )

        outcomes = _run([s.get('text', '') for s in sentences])
        if len(outcomes) != len(sentences):
            # Length mismatch — can't safely map verdicts to indices. Fail open.
            return [], False

        rejected = [i for i, o in enumerate(outcomes) if o.verdict == 'reject']
        if rejected:
            reasons = {i: outcomes[i].reason for i in rejected}
            repaired = p1_gen.repair_sentences(core_asset, rejected, reasons, sense_id)
            if repaired:
                for idx, new_text in repaired.items():
                    if 0 <= idx < len(sentences) and isinstance(sentences[idx], dict):
                        sentences[idx]['text'] = new_text
                repaired_idxs = sorted(repaired.keys())
                re_outcomes = _run([sentences[i].get('text', '') for i in repaired_idxs])
                if len(re_outcomes) == len(repaired_idxs):
                    for j, idx in enumerate(repaired_idxs):
                        outcomes[idx] = re_outcomes[j]

        warnings: list[str] = []
        acceptable = 0
        for i, o in enumerate(outcomes):
            if o.verdict == 'accept':
                acceptable += 1
            elif o.verdict == 'flag':
                acceptable += 1  # flagged sentences are kept, surfaced for review
                warnings.append(
                    f'P1 sentence[{i}] flagged (rating {o.confidence:g}): {o.reason}'
                )
            else:  # reject survived the repair pass
                warnings.append(
                    f'P1 sentence[{i}] rejected (rating {o.confidence:g}): {o.reason}'
                )

        blocked = acceptable < P1_MIN_ACCEPTABLE_SENTENCES
        if blocked:
            warnings.append(
                f'P1 sentence judge: only {acceptable} acceptable sentences '
                f'(< {P1_MIN_ACCEPTABLE_SENTENCES}) after repair — asset blocked.'
            )
        return warnings, blocked

    # ------------------------------------------------------------------
    # Corpus sentence sourcing
    # ------------------------------------------------------------------

    def _fetch_corpus_sentences(
        self, sense_id: int, language_id: int
    ) -> list[dict]:
        """Mine transcript sentences that use *this sense* of the word (TASK-513).

        Replaces a blind scan of 50 arbitrary transcripts plus 30 conversations,
        matching on the bare lemma. That path was wrong twice over: it had no
        way to tell one sense of a word from another, and its 50-row window
        meant a word could be all over the corpus and still be missed.

        The index built for exactly this question is used instead:
        ``tests.vocab_sense_ids`` (GIN) narrows to transcripts containing the
        sense, and ``tests.vocab_token_map`` gives the *surface tokens* that
        realise it — which is how an inflected or segmented occurrence is found
        without a ``\\b`` regex the CJK languages cannot support.

        Mined sentences are markup-stripped, tier-screened against the sense's
        own band (TASK-524 — no point seeding P1 with a sentence the gate will
        reject downstream), deduplicated, and tagged ``sentence_source='mined'``.

        Returns at most ``VOCAB_SENTENCES_PER_WORD`` dicts with keys: text,
        target_word, source, complexity_tier, sentence_source, test_id.
        Returns ``[]`` on any failure — P1 then generates the full set, which
        is the correct degradation.
        """
        from services.exercise_generation.language_processor import LanguageProcessor
        from services.exercise_generation.transcript_miner import TranscriptMiner
        from services.vocabulary_ladder.tier_gate import screen_sentence, tier_for_lemma

        lemma = self._lemma_for_sense(sense_id)
        if not lemma:
            return []

        try:
            resp = self.db.rpc('tests_containing_sense', {
                'p_sense_id': sense_id,
                'p_language_id': language_id,
            }).execute()
            rows = resp.data or []
        except Exception as e:
            logger.warning(
                "Transcript mining RPC failed for sense %s: %s — P1 will "
                "generate all sentences", sense_id, e,
            )
            return []

        if not rows:
            logger.info("No transcripts contain sense %s — nothing to mine", sense_id)
            return []

        try:
            processor = LanguageProcessor.for_language(language_id)
        except Exception as e:
            logger.warning("No language processor for %s: %s", language_id, e)
            return []

        tier = tier_for_lemma(lemma, language_id)
        limit = Config.VOCAB_SENTENCES_PER_WORD
        seen: set[str] = set()
        mined: list[dict] = []
        screened_out = 0

        for test in rows:
            transcript = test.get('transcript') or ''
            if not transcript:
                continue
            tokens = self._sense_surface_tokens(test.get('vocab_token_map'), sense_id)
            if not tokens:
                # The sense is indexed on the test but the token map has no
                # surface form for it — fall back to the lemma itself.
                tokens = [lemma]
            test_tier = TranscriptMiner._difficulty_to_tier(test.get('difficulty') or 2)

            try:
                candidates = processor.split_sentences(transcript)
            except Exception:
                continue

            for raw_sentence in candidates:
                text = TranscriptMiner._strip_markup(raw_sentence).strip()
                if len(text) < 10:
                    continue

                matched = next(
                    (tok for tok in tokens
                     if self._mentions_token(processor, text, tok)), None,
                )
                if matched is None:
                    continue

                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)

                if not screen_sentence(
                    text, language_id, tier, target_word=matched,
                ).passed:
                    screened_out += 1
                    continue

                mined.append({
                    'text': text,
                    'target_word': matched,
                    'source': 'transcript',
                    'complexity_tier': test_tier,
                    'sentence_source': SENTENCE_SOURCE_MINED,
                    'test_id': test.get('id'),
                })
                if len(mined) >= limit:
                    break
            if len(mined) >= limit:
                break

        logger.info(
            "Mined %d sentence(s) for sense %s from %d transcript(s) "
            "(%d rejected by the tier gate at %s)",
            len(mined), sense_id, len(rows), screened_out, tier,
        )
        return mined

    @staticmethod
    def _mentions_token(processor, text: str, token: str) -> bool:
        """Whether ``text`` attests ``token`` as a word, for mining purposes.

        The strict path is ``processor.contains_whole_word`` (audit B4): the
        token must be an exact contiguous run of segmenter output. That is the
        right default and it is what rejects 咖啡 inside 咖啡馆 ("cafe") — a
        different lexeme that happens to start with the target.

        It also, however, rejects 咖啡 inside 喝咖啡, where jieba has merged a
        verb and its object into one token. The sentence plainly attests the
        word; refusing to mine it is lost recall, not precision.

        The two cases are told apart by *position*, which in Chinese is
        linguistically load-bearing: compounding is overwhelmingly head-final,
        so a target that is a **prefix** of a longer token is usually part of a
        derived word (咖啡+馆, 电话+亭), while a target that is a **suffix** is
        usually the object of a merged phrase (喝+咖啡, 看+电视). Suffix
        position is therefore accepted as a fallback; prefix position is not.

        Deliberately local to mining rather than folded into
        ``contains_whole_word``: that helper is shared with sentence
        *validation*, where the strict reading is the correct one.
        """
        if not text or not token:
            return False
        if processor.contains_whole_word(text, token):
            return True
        if token.isascii():
            # Space-delimited languages have no merge problem to solve, and a
            # substring fallback there would match "run" inside "running".
            return False
        try:
            merged = [t for t in processor.tokenize(text)
                      if t != token and t.endswith(token)]
        except Exception:
            return False
        return bool(merged)

    def _lemma_for_sense(self, sense_id: int) -> str:
        """Lemma text for a sense, or '' if it cannot be resolved."""
        try:
            resp = (
                self.db.table('dim_word_senses')
                .select('dim_vocabulary(lemma)')
                .eq('id', sense_id)
                .single()
                .execute()
            )
            vocab = (resp.data or {}).get('dim_vocabulary') or {}
            return (vocab.get('lemma') or '').strip()
        except Exception as e:
            logger.warning("Lemma lookup failed for sense %s: %s", sense_id, e)
            return ''

    @staticmethod
    def _sense_surface_tokens(token_map, sense_id: int) -> list[str]:
        """Surface forms in ``vocab_token_map`` that resolve to ``sense_id``.

        The column is a JSONB array whose entries pair a token with the sense
        it was resolved to. Both the legacy pair shape ``["ran", 42]`` and the
        object shape ``{"token": "ran", "sense_id": 42}`` are accepted, because
        the map is written by more than one backfill generation.
        """
        tokens: list[str] = []
        for entry in (token_map or []):
            token = resolved = None
            if isinstance(entry, dict):
                token = entry.get('token') or entry.get('text')
                resolved = entry.get('sense_id')
            elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                token, resolved = entry[0], entry[1]
            if token and resolved == sense_id and token not in tokens:
                tokens.append(str(token))
        return tokens

    # ------------------------------------------------------------------
    # L5 collocation gate
    # ------------------------------------------------------------------

    def _collocation_is_fixed(self, core_asset: dict, language_id: int) -> bool:
        """True if (lemma, primary_collocate) has corpus evidence as a fixed pair.

        Delegates to the grounding service (TASK-523), which owns the PMI
        threshold and the bundled-list source. This used to be a second,
        independent ``corpus_collocations`` query with its own copy of the
        threshold; one number deciding "is this a fixed pair" in two places
        was drift waiting to happen, and the grounder also consults the
        English frequency list this query never saw.

        Reads the tag ``ground_core_asset`` already pinned onto the asset
        rather than re-querying, so the L5 decision and the stored provenance
        can never disagree about the same pair.

        Unattested drops L5, and so does ``no_source``: this gate protects a
        quality-sensitive exercise, and "we cannot check" is not a reason to
        ship a collocation item built on an unverified pair.
        """
        tag = (core_asset or {}).get('collocate_grounding')
        if isinstance(tag, dict):
            return tag.get('status') == GROUNDING_CORPUS

        # No tag: an asset generated before grounding existed, or a caller
        # that skipped the annotation step. Grade it now rather than guessing.
        lemma = self._extract_lemma_from_core(core_asset)
        collocate = (core_asset or {}).get('primary_collocate') or ''
        return CollocationGrounder(self.db).validate(
            lemma, collocate, language_id,
        ).validated

    def _extract_lemma_from_core(self, core_asset: dict) -> str:
        """Pull the lemma off the first sentence's target_word (alias-aware)."""
        sentences = core_asset.get('sentences') or []
        if not sentences:
            return ''
        from services.vocabulary_ladder.config import get_sentence_target
        return (get_sentence_target(sentences[0]) or '').strip().lower()

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def _assets_exist(self, sense_id: int) -> bool:
        """Check if all asset types exist and are valid for this sense.

        Accepts both old-format (prompt2_exercises, prompt3_transforms) and
        new variant format (prompt2_exercises_A/B, prompt3_transforms_A/B).
        """
        try:
            resp = (
                self.db.table('word_assets')
                .select('asset_type')
                .eq('sense_id', sense_id)
                .eq('is_valid', True)
                .execute()
            )
            types = {row['asset_type'] for row in (resp.data or [])}
            has_p1 = 'prompt1_core' in types
            has_p2 = (
                types >= {'prompt2_exercises_A', 'prompt2_exercises_B'}
                or 'prompt2_exercises' in types
            )
            has_p3 = (
                types >= {'prompt3_transforms_A', 'prompt3_transforms_B'}
                or 'prompt3_transforms' in types
            )
            return has_p1 and has_p2 and has_p3
        except Exception:
            return False

    def _store_asset(
        self,
        sense_id: int,
        language_id: int,
        asset_type: str,
        content: dict,
        model_used: str,
        batch_id: str,
        is_valid: bool = True,
        validation_errors: list[str] | None = None,
        validation_warnings: list[str] | None = None,
    ):
        """Upsert a word asset row.

        Guard: never overwrite a previously-valid asset with an invalid one.
        A failed/stricter regeneration (e.g. P1 fails validation) should not
        clobber a good asset that is still serving exercises — keep the old
        valid row and let the caller surface the errors instead.
        """
        if not is_valid:
            try:
                existing = (
                    self.db.table('word_assets')
                    .select('is_valid')
                    .eq('sense_id', sense_id)
                    .eq('asset_type', asset_type)
                    .eq('is_valid', True)
                    .limit(1)
                    .execute()
                )
                if existing.data:
                    logger.warning(
                        "Skipping invalid %s asset for sense %s — a valid row "
                        "already exists and will be retained",
                        asset_type, sense_id,
                    )
                    return
            except Exception as e:
                logger.error(
                    "Failed to check existing %s asset for sense %s: %s",
                    asset_type, sense_id, e,
                )

        try:
            row = {
                'sense_id': sense_id,
                'language_id': language_id,
                'asset_type': asset_type,
                'content': content,
                'model_used': model_used,
                'prompt_version': 'v1',
                'is_valid': is_valid,
                'validation_errors': validation_errors,
                'validation_warnings': validation_warnings,
                'generation_batch_id': batch_id,
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
            self.db.table('word_assets').upsert(
                row, on_conflict='sense_id,asset_type'
            ).execute()

            logger.info(
                "Stored %s asset for sense %s (valid=%s)",
                asset_type, sense_id, is_valid,
            )
        except Exception as e:
            logger.error("Failed to store %s asset for sense %s: %s",
                         asset_type, sense_id, e)

    def _update_vocabulary_metadata(self, sense_id: int, core_asset: dict):
        """Update dim_vocabulary.semantic_class and dim_word_senses phonetics."""
        try:
            # Get vocab_id and current definition from sense
            resp = (
                self.db.table('dim_word_senses')
                .select('vocab_id, definition')
                .eq('id', sense_id)
                .single()
                .execute()
            )
            vocab_id = resp.data.get('vocab_id') if resp.data else None

            if vocab_id:
                self.db.table('dim_vocabulary').update({
                    # Normalise legacy P1 labels to the ratified enum so the
                    # write stays inside the dim_vocabulary CHECK constraint.
                    'semantic_class': normalize_semantic_class(core_asset.get('semantic_class')),
                    'part_of_speech': core_asset.get('pos'),
                }).eq('id', vocab_id).execute()

            # Update dim_word_senses with phonetic data
            updates = {}
            if core_asset.get('ipa'):
                updates['ipa_pronunciation'] = core_asset['ipa']
            if core_asset.get('morphological_forms'):
                updates['morphological_forms'] = core_asset['morphological_forms']
            if core_asset.get('pronunciation'):
                updates['pronunciation'] = core_asset['pronunciation']
            # JA P1 emits a keigo register (PROMPT1_KEY_MAP '10'); persist it to
            # dim_word_senses.register. No-op for ZH/EN P1 (no register key) and
            # safe pre-backfill (column added by migrations/dim_word_senses_register.sql).
            if core_asset.get('register'):
                updates['register'] = core_asset['register']

            # Replace placeholder definitions with the LLM-generated one. The
            # admin upload helper writes "Definition for {lemma}" when no
            # definition is supplied — once P1 runs, we have a real one.
            new_def = (core_asset.get('definition') or '').strip()
            if new_def:
                current = (resp.data.get('definition') if resp.data else '') or ''
                if not current or current.startswith('Definition for '):
                    updates['definition'] = new_def

            if updates:
                self.db.table('dim_word_senses').update(updates).eq('id', sense_id).execute()

        except Exception as e:
            logger.error("Failed to update vocabulary metadata for sense %s: %s",
                         sense_id, e)


# Import Config at module level for VOCAB_SENTENCES_PER_WORD
from config import Config
