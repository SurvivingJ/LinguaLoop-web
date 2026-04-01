# services/exercise_generation/base_generator.py

import uuid
import logging
from abc import ABC, abstractmethod
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class ExerciseGenerator(ABC):
    """
    Abstract base class for all exercise generators.
    Subclasses implement generate_one() and set exercise_type / source_type.
    """

    exercise_type: str
    source_type:   str

    def __init__(self, db, language_id: int, model: str):
        self.db          = db
        self.language_id = language_id
        self.model       = model

    @abstractmethod
    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """
        Generate a single exercise item from a sentence dict.
        Returns a content JSONB dict on success, or None to skip.
        """

    def generate_batch(
        self,
        sentence_pool: list[dict],
        source_id: int,
        target_count: int,
        generation_batch_id: str,
    ) -> list[dict]:
        """
        Iterate the sentence pool, calling generate_one() for each sentence
        until target_count valid exercises are accumulated.
        """
        from services.exercise_generation.validators import ExerciseValidator
        from services.exercise_generation.difficulty import DifficultyCalibrator

        validator  = ExerciseValidator()
        calibrator = DifficultyCalibrator()
        results    = []

        for sent in sentence_pool:
            if len(results) >= target_count:
                break
            try:
                content = self.generate_one(sent, source_id)
                if content is None:
                    continue
                is_valid, errors = validator.validate(content, self.exercise_type)
                if not is_valid:
                    logger.warning(
                        "Validation failed for %s: %s", self.exercise_type, errors
                    )
                    continue
                row = self._build_exercise_row(content, sent, source_id, generation_batch_id)
                row = calibrator.attach_difficulty(row, sent.get('complexity_tier', 'T3'))
                results.append(row)
            except Exception as exc:
                logger.error("generate_one error for %s: %s", self.exercise_type, exc)

        return results

    def _build_exercise_row(
        self, content: dict, sentence_dict: dict, source_id: int, generation_batch_id: str,
    ) -> dict:
        # Determine the actual source context: if the sentence came from a
        # conversation, the FK target is conversation_id (uuid) regardless
        # of the generator's own source_type label.
        sentence_source = sentence_dict.get('source', self.source_type)
        is_conversation = sentence_source == 'conversation'

        row = {
            'id':                    str(uuid.uuid4()),
            'language_id':           self.language_id,
            'exercise_type':         self.exercise_type,
            'source_type':           'conversation' if is_conversation else self.source_type,
            'content':               content,
            'tags':                  self._build_tags(source_id, sentence_dict),
            'complexity_tier':        sentence_dict.get('complexity_tier'),
            'is_active':             True,
            'generation_batch_id':   generation_batch_id,
            'grammar_pattern_id':    None,
            'word_sense_id':         None,
            'corpus_collocation_id': None,
        }

        if is_conversation:
            row['conversation_id'] = source_id
        else:
            fk_map = {
                'grammar':     'grammar_pattern_id',
                'vocabulary':  'word_sense_id',
                'collocation': 'corpus_collocation_id',
            }
            fk_col = fk_map.get(self.source_type)
            if fk_col:
                row[fk_col] = source_id

        return row

    def _build_tags(self, source_id: int, sentence_dict: dict) -> dict:
        return {
            'source_type':  self.source_type,
            'source_id':    source_id,
            'complexity_tier': sentence_dict.get('complexity_tier'),
            'sentence_src': sentence_dict.get('source', 'unknown'),
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def call_llm(self, prompt: str, response_format: str = 'json') -> dict | list:
        """Call the LLM via OpenRouter with retry on failure."""
        from services.exercise_generation.llm_client import call_llm as _call_llm
        return _call_llm(prompt, model=self.model, response_format=response_format)

    def load_prompt_template(self, task_name: str) -> str:
        """Fetch the latest version of a named prompt template. Caches per instance."""
        if not hasattr(self, '_template_cache'):
            self._template_cache: dict[str, str] = {}
        if task_name not in self._template_cache:
            result = self.db.table('prompt_templates') \
                .select('template_text') \
                .eq('task_name', task_name) \
                .order('version', desc=True) \
                .limit(1) \
                .execute()
            if not result.data:
                raise RuntimeError(f"No prompt template for task_name='{task_name}'")
            self._template_cache[task_name] = result.data[0]['template_text']
        return self._template_cache[task_name]

    def batch_insert(self, rows: list[dict]) -> int:
        """Insert exercise rows into the exercises table in a single batch."""
        if not rows:
            return 0
        result = self.db.table('exercises').insert(rows).execute()
        return len(result.data or [])
