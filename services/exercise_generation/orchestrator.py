# services/exercise_generation/orchestrator.py

import uuid
import logging
from services.exercise_generation.config import (
    GRAMMAR_DISTRIBUTION, VOCABULARY_DISTRIBUTION, COLLOCATION_DISTRIBUTION,
    PHASE_MAP,
)
from services.exercise_generation.transcript_miner import get_sentence_pool
from services.exercise_generation.generators.cloze             import ClozeGenerator
from services.exercise_generation.generators.jumbled_sentence  import JumbledSentenceGenerator
from services.exercise_generation.generators.translation       import TlNlTranslationGenerator, NlTlTranslationGenerator
from services.exercise_generation.generators.flashcard         import FlashcardGenerator
from services.exercise_generation.generators.spot_incorrect    import SpotIncorrectGenerator
from services.exercise_generation.generators.semantic          import SemanticDiscrimGenerator, OddOneOutGenerator
from services.exercise_generation.generators.collocation       import (
    CollocationGapFillGenerator, CollocationRepairGenerator, OddCollocationOutGenerator,
)
from services.exercise_generation.generators.verb_noun_match   import VerbNounMatchGenerator
from services.exercise_generation.generators.context_spectrum  import ContextSpectrumGenerator
from services.exercise_generation.generators.timed_speed_round import TimedSpeedRoundGenerator

logger = logging.getLogger(__name__)


class ExerciseGenerationOrchestrator:
    """
    Coordinates the full five-phase exercise generation pipeline for one source.

    Phase 1 - Sentence Pool Assembly
    Phase 2 - Exercise Assembly (per-type generator classes)
    Phase 3 - Deterministic Validation (inside generate_batch)
    Phase 4 - Difficulty Calibration (inside generate_batch)
    Phase 5 - Persistence (batch insert to exercises table)
    """

    def __init__(self, db, audio_synthesizer=None, nl_language_code: str = 'en'):
        self.db                = db
        self.audio_synthesizer = audio_synthesizer
        self.nl_language_code  = nl_language_code

    def run(
        self,
        source_type: str,
        source_id: int,
        language_id: int,
        phases: list[str] | None = None,
    ) -> dict:
        """
        Execute the full pipeline for one source.
        Returns a summary dict with counts per exercise type.
        """
        batch_id     = str(uuid.uuid4())
        model, sent_model = self._load_models(language_id)
        distribution = self._get_distribution(source_type)

        logger.info(
            "ExerciseGenerationOrchestrator.run: source=%s id=%s lang=%s batch=%s",
            source_type, source_id, language_id, batch_id,
        )

        # Phase 1: Sentence pool
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

        for ex_type, gen in generators.items():
            if ex_type not in distribution:
                continue
            if not self._in_requested_phases(ex_type, phases):
                continue
            target = distribution[ex_type]
            rows   = gen.generate_batch(sentence_pool, source_id, target, batch_id)
            all_rows.extend(rows)
            counts[ex_type] = len(rows)
            logger.info("Generated %d x %s", len(rows), ex_type)

        # Phase 5: Persistence
        self._batch_insert(all_rows)

        total = sum(counts.values())
        logger.info("Batch %s complete: %d total exercises", batch_id, total)
        return {'batch_id': batch_id, 'counts': counts, 'total': total}

    def _load_models(self, language_id: int) -> tuple[str, str]:
        """Fetch exercise_model and exercise_sentence_model from dim_languages."""
        row = self.db.table('dim_languages') \
            .select('exercise_model, exercise_sentence_model') \
            .eq('id', language_id).single().execute().data
        default = 'google/gemini-flash-1.5'
        return (
            (row or {}).get('exercise_model') or default,
            (row or {}).get('exercise_sentence_model') or default,
        )

    def _get_distribution(self, source_type: str) -> dict[str, int]:
        return {
            'grammar':     GRAMMAR_DISTRIBUTION,
            'vocabulary':  VOCABULARY_DISTRIBUTION,
            'collocation': COLLOCATION_DISTRIBUTION,
        }[source_type]

    def _build_generators(
        self, source_type: str, language_id: int, model: str
    ) -> dict[str, object]:
        """Instantiate all applicable generator classes for the given source_type."""
        kw = dict(db=self.db, language_id=language_id, model=model)

        grammar_generators = {
            'cloze_completion':        ClozeGenerator(**kw, source_type='grammar'),
            'jumbled_sentence':        JumbledSentenceGenerator(**kw, source_type='grammar'),
            'tl_nl_translation':       TlNlTranslationGenerator(**kw, source_type='grammar',
                                           nl_language_code=self.nl_language_code),
            'nl_tl_translation':       NlTlTranslationGenerator(**kw, source_type='grammar',
                                           nl_language_code=self.nl_language_code),
            'text_flashcard':          FlashcardGenerator(**kw, mode='text', source_type='grammar'),
            'listening_flashcard':     FlashcardGenerator(**kw, mode='listening', source_type='grammar',
                                           audio_synthesizer=self.audio_synthesizer),
            'semantic_discrimination': SemanticDiscrimGenerator(**kw, source_type='grammar'),
            'spot_incorrect_sentence': SpotIncorrectGenerator(**kw),
            'odd_one_out':             OddOneOutGenerator(**kw, source_type='grammar'),
            'context_spectrum':        ContextSpectrumGenerator(**kw),
            'timed_speed_round':       TimedSpeedRoundGenerator(**kw),
        }

        vocabulary_generators = {
            'text_flashcard':          FlashcardGenerator(**kw, mode='text', source_type='vocabulary'),
            'listening_flashcard':     FlashcardGenerator(**kw, mode='listening', source_type='vocabulary',
                                           audio_synthesizer=self.audio_synthesizer),
            'cloze_completion':        ClozeGenerator(**kw, source_type='vocabulary'),
            'tl_nl_translation':       TlNlTranslationGenerator(**kw, source_type='vocabulary',
                                           nl_language_code=self.nl_language_code),
            'semantic_discrimination': SemanticDiscrimGenerator(**kw, source_type='vocabulary'),
        }

        collocation_generators = {
            'collocation_gap_fill':  CollocationGapFillGenerator(**kw),
            'collocation_repair':    CollocationRepairGenerator(**kw),
            'odd_collocation_out':   OddCollocationOutGenerator(**kw),
            'text_flashcard':        FlashcardGenerator(**kw, mode='text', source_type='collocation'),
            'verb_noun_match':       VerbNounMatchGenerator(**kw),
        }

        return {
            'grammar':     grammar_generators,
            'vocabulary':  vocabulary_generators,
            'collocation': collocation_generators,
        }[source_type]

    def _batch_insert(self, rows: list[dict]) -> None:
        if not rows:
            return
        try:
            self.db.table('exercises').insert(rows).execute()
            logger.info("Inserted %d exercise rows", len(rows))
        except Exception as exc:
            logger.error("Batch insert failed: %s", exc)

    @staticmethod
    def _call_llm_with_model(model: str):
        """Return a partial callable with the model pre-bound for sentence generation."""
        from services.exercise_generation.llm_client import call_llm
        def _call(prompt: str, response_format: str = 'json', **kwargs):
            return call_llm(prompt, model=model, response_format=response_format)
        return _call

    @staticmethod
    def _in_requested_phases(ex_type: str, phases: list[str] | None) -> bool:
        if phases is None:
            return True
        return any(ex_type in PHASE_MAP.get(p, []) for p in phases)
