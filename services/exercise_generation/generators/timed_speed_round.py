# services/exercise_generation/generators/timed_speed_round.py

from services.exercise_generation.base_generator import ExerciseGenerator


class TimedSpeedRoundGenerator(ExerciseGenerator):
    """
    Generates timed_speed_round exercise rows by sampling existing exercises
    for the same source_id and wrapping them in timing metadata.
    No LLM. Should be run after Phase A generators have populated the exercises table.
    """

    exercise_type = 'timed_speed_round'
    source_type   = 'grammar'

    WRAPPABLE_TYPES: list[str] = [
        'cloze_completion', 'text_flashcard', 'tl_nl_translation',
        'collocation_gap_fill',
    ]
    DEFAULT_ROUND_SIZE: int = 10
    DEFAULT_TIME_LIMIT_SECONDS: int = 60

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        fk_col = {
            'grammar':     'grammar_pattern_id',
            'vocabulary':  'word_sense_id',
            'collocation': 'corpus_collocation_id',
        }.get(self.source_type)

        result = self.db.table('exercises') \
            .select('id') \
            .eq(fk_col, source_id) \
            .in_('exercise_type', self.WRAPPABLE_TYPES) \
            .eq('is_active', True) \
            .limit(self.DEFAULT_ROUND_SIZE) \
            .execute()

        exercise_ids = [r['id'] for r in (result.data or [])]
        if len(exercise_ids) < 5:
            return None

        return {
            'exercise_ids':        exercise_ids,
            'round_size':          len(exercise_ids),
            'time_limit_seconds':  self.DEFAULT_TIME_LIMIT_SECONDS,
            'source_type':         self.source_type,
            'source_id':           source_id,
        }
