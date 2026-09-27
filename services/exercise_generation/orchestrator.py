# services/exercise_generation/orchestrator.py

import uuid
import logging
from services.exercise_generation.config import (
    COLLOCATION_DISTRIBUTION, PHASE_MAP,
)
from services.exercise_generation.transcript_miner import get_sentence_pool
from services.vocabulary_ladder.exercise_caps import (
    apply_caps, cap_key, count_existing, log_dropped,
)
from services.exercise_generation.generators.flashcard         import FlashcardGenerator
from services.exercise_generation.generators.collocation       import (
    CollocationGapFillGenerator, CollocationRepairGenerator, OddCollocationOutGenerator,
)
from services.exercise_generation.generators.verb_noun_match   import VerbNounMatchGenerator

logger = logging.getLogger(__name__)

# TASK-512: this orchestrator no longer generates vocabulary exercises. The
# vocabulary ladder (VocabAssetPipeline + LadderExerciseRenderer) is the sole
# vocab generator — its output is judge-gated and carries word_asset_id, which
# this pipeline's output never did. Only the collocation source remains here
# (frozen: no new work lands in it). The grammar, conversation and style sources
# were archived 2026-09-21 with their features — see archive/modules/.
_VOCAB_RETIRED_MSG = (
    "source_type='vocabulary' is retired from the legacy exercise pipeline "
    "(TASK-512). The vocabulary ladder is the sole vocab generator: call "
    "services.vocabulary_ladder.asset_pipeline.VocabAssetPipeline."
    "generate_for_sense(sense_id, language_id) followed by "
    "services.vocabulary_ladder.exercise_renderer.LadderExerciseRenderer."
    "render_all(sense_id, language_id), or use "
    "services.exercise_generation.run_exercise_generation.run_vocabulary_batch, "
    "which already routes there."
)


class ExerciseGenerationOrchestrator:
    """
    Coordinates the full five-phase exercise generation pipeline for one source.

    Phase 1 - Sentence Pool Assembly
    Phase 2 - Exercise Assembly (per-type generator classes)
    Phase 3 - Deterministic Validation (inside generate_batch)
    Phase 4 - Difficulty Calibration (inside generate_batch)
    Phase 5 - Persistence (batch insert to exercises table)
    """

    def __init__(self, db, audio_synthesizer=None, nl_language_code: str | None = None):
        # No 'en' literal here by design (TASK-519). The fallback is the single
        # declared knob Config.DEFAULT_NATIVE_LANGUAGE, so the assumption is
        # visible and overridable in one place instead of being baked into a
        # signature — that literal is how the v1 corpus became English-only.
        from config import Config

        self.db                = db
        self.audio_synthesizer = audio_synthesizer
        self.nl_language_code  = nl_language_code or Config.DEFAULT_NATIVE_LANGUAGE

    def run(
        self,
        source_type: str,
        source_id: int,
        language_id: int,
        phases: list[str] | None = None,
        sentence_pool: list[dict] | None = None,
    ) -> dict:
        """
        Execute the full pipeline for one source.

        Args:
            sentence_pool: If provided, skip Phase 1 (sentence mining) and
                use this pool directly.

        Returns a summary dict with counts per exercise type.
        """
        batch_id     = str(uuid.uuid4())
        model, sent_model = self._load_models(language_id)
        distribution = self._get_distribution(source_type)

        logger.info(
            "ExerciseGenerationOrchestrator.run: source=%s id=%s lang=%s batch=%s",
            source_type, source_id, language_id, batch_id,
        )

        # Phase 1: Sentence pool (skip if pre-built pool provided)
        if sentence_pool is None:
            sentence_pool = get_sentence_pool(
                source_type, source_id, language_id,
                db=self.db, llm_client=self._call_llm_with_model(model),
                model=sent_model,
            )
        logger.info("Sentence pool size: %d", len(sentence_pool))

        # Phase 2-4: Generate, validate, calibrate per type
        counts: dict[str, int] = {}
        all_rows: list[dict]   = []

        generators = self._build_generators(source_type, language_id, model)

        # Same-language guard: when the target language IS the learner's native
        # language (e.g. English-target learners with an English UI), tl_nl /
        # nl_tl are not translation tasks — they degenerate into tense-variant
        # MCQs with no unique answer (eval HIGH #3, 0% acceptable). Skip them.
        # Cross-language pairs (ZH/JA target, EN native) keep translations.
        target_code = self._get_language_code(language_id)
        skip_translation = target_code == self.nl_language_code

        # Prefer level-appropriate sentences (simpler tiers first) so an A1 word
        # is not blanked from a C2 corpus sentence, and hand each exercise type a
        # distinct window of the pool so the same 3 sentences aren't reused across
        # text/listening/cloze/tl_nl (eval MEDIUM #7).
        ordered_pool = sorted(sentence_pool, key=lambda s: s.get('complexity_tier') or 'T3')
        cursor = 0

        for ex_type, gen in generators.items():
            if ex_type not in distribution:
                continue
            if skip_translation and ex_type in ('tl_nl_translation', 'nl_tl_translation'):
                logger.info(
                    "Skipping %s: target language '%s' == native '%s' (not a translation)",
                    ex_type, target_code, self.nl_language_code,
                )
                continue
            if not self._in_requested_phases(ex_type, phases):
                continue
            target = distribution[ex_type]
            # Distinct slice per type; fall back to the full pool if exhausted.
            type_pool = ordered_pool[cursor:] or ordered_pool
            rows   = gen.generate_batch(type_pool, source_id, target, batch_id)
            cursor += target
            all_rows.extend(rows)
            counts[ex_type] = len(rows)
            logger.info("Generated %d x %s", len(rows), ex_type)

        # Phase 5: Persistence
        self._batch_insert(all_rows)

        total = sum(counts.values())

        # L1: report per-type shortfalls so a thin batch is observable in
        # monitoring instead of looking like a clean success. Only types we
        # actually attempted (present in counts) are considered — intentionally
        # skipped types (translation/phase gating) are not shortfalls.
        shortfalls = {
            ex_type: distribution[ex_type] - produced
            for ex_type, produced in counts.items()
            if produced < distribution.get(ex_type, 0)
        }
        if shortfalls:
            logger.warning(
                "Batch %s under target for %d type(s): %s",
                batch_id, len(shortfalls), shortfalls,
            )

        logger.info("Batch %s complete: %d total exercises", batch_id, total)
        return {'batch_id': batch_id, 'counts': counts, 'total': total, 'shortfalls': shortfalls}

    def _load_models(self, language_id: int) -> tuple[str, str]:
        """Resolve the exercise_model and exercise_sentence_model for a language.

        Reads from prompt_templates.model — the single source of truth.
        Every legacy exercise-generation task shares one model and every
        sentence-mining task shares another, so picking one representative
        task per role gives the same answer the old dim_languages columns
        used to surface.
        """
        from services.prompt_service import get_template_config
        exercise_cfg = get_template_config(
            self.db, 'cloze_distractor_generation', language_id,
        )
        sentence_cfg = get_template_config(
            self.db, 'exercise_sentence_generation', language_id,
        )
        return exercise_cfg['model'], sentence_cfg['model']

    def _get_language_code(self, language_id: int) -> str:
        """Resolve the ISO language_code for a language_id (e.g. 2 -> 'en')."""
        row = self.db.table('dim_languages').select('language_code') \
            .eq('id', language_id).single().execute().data
        return (row or {}).get('language_code', 'unknown')

    def _get_distribution(self, source_type: str) -> dict[str, int]:
        if source_type == 'vocabulary':
            raise ValueError(_VOCAB_RETIRED_MSG)
        if source_type != 'collocation':
            raise ValueError(
                f"Unsupported source_type {source_type!r}: only 'collocation' remains "
                "(grammar/conversation/style archived 2026-09-21)."
            )
        return COLLOCATION_DISTRIBUTION

    def _build_generators(
        self, source_type: str, language_id: int, model: str
    ) -> dict[str, object]:
        """Instantiate all applicable generator classes for the given source_type."""
        kw = dict(db=self.db, language_id=language_id, model=model)

        # No vocabulary_generators: the vocabulary ladder is the sole vocab
        # generator (TASK-512). See _VOCAB_RETIRED_MSG.

        collocation_generators = {
            'collocation_gap_fill':  CollocationGapFillGenerator(**kw),
            'collocation_repair':    CollocationRepairGenerator(**kw),
            'odd_collocation_out':   OddCollocationOutGenerator(**kw),
            'text_flashcard':        FlashcardGenerator(**kw, mode='text', source_type='collocation'),
            'verb_noun_match':       VerbNounMatchGenerator(**kw),
        }

        if source_type == 'vocabulary':
            raise ValueError(_VOCAB_RETIRED_MSG)

        if source_type != 'collocation':
            raise ValueError(f"Unsupported source_type {source_type!r}")
        return collocation_generators

    def _batch_insert(self, rows: list[dict]) -> None:
        if not rows:
            return
        # TASK-743 (T3d.2): context-free types get at most N variants per
        # (sense, type, context anchor). This path appends to whatever a sense
        # already has, so the existing rows have to be counted first — unlike
        # the ladder renderer, which assembles a whole sense in one go.
        rows, dropped = apply_caps(rows, self._existing_cap_counts(rows))
        log_dropped(dropped, 'exercise-generation batch')
        if not rows:
            return
        try:
            self.db.table('exercises').insert(rows).execute()
            logger.info("Inserted %d exercise rows", len(rows))
        except Exception as exc:
            logger.error("Batch insert failed: %s", exc)

    def _existing_cap_counts(self, rows: list[dict]) -> dict[tuple, int]:
        """Cap-bucket counts for content already stored against these senses.

        Fails **open** — a lookup failure lets the batch through uncapped
        rather than dropping generated work. The partial unique index in
        task743 is the backstop that makes that safe.
        """
        sense_ids = sorted({
            r['word_sense_id'] for r in rows
            if r.get('word_sense_id') is not None
            and cap_key(r) is not None
        })
        if not sense_ids:
            return {}
        try:
            resp = (
                self.db.table('exercises')
                .select('word_sense_id, exercise_type, content')
                .in_('word_sense_id', sense_ids)
                .eq('is_active', True)
                .execute()
            )
        except Exception as exc:
            logger.warning(
                "Could not read existing exercises for the context-free cap; "
                "inserting uncapped (the unique index still guards): %s", exc,
            )
            return {}
        return count_existing(resp.data or [])

    @staticmethod
    def _call_llm_with_model(model: str, provider: str | None = None):
        """Return a partial callable with the model pre-bound for sentence generation.

        ``provider`` is threaded through so a batch can be routed to the headless
        Claude Code transport; None keeps LLM_DEFAULT_PROVIDER (openrouter).
        """
        from services.exercise_generation.llm_client import call_llm
        def _call(prompt: str, response_format: str = 'json', **kwargs):
            return call_llm(
                prompt, model=model, response_format=response_format,
                provider=provider,
            )
        return _call

    @staticmethod
    def _in_requested_phases(ex_type: str, phases: list[str] | None) -> bool:
        if phases is None:
            return True
        return any(ex_type in PHASE_MAP.get(p, []) for p in phases)
