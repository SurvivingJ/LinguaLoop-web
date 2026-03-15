# services/exercise_generation/generators/flashcard.py

import uuid
from services.exercise_generation.base_generator import ExerciseGenerator


class FlashcardGenerator(ExerciseGenerator):
    """
    Generates text_flashcard and listening_flashcard exercises.
    No LLM calls. Definitions sourced from dim_word_senses.
    Audio flashcards call the existing AudioSynthesizer -> Cloudflare R2.
    """

    exercise_type = 'text_flashcard'
    source_type   = 'vocabulary'

    def __init__(self, db, language_id: int, model: str = '',
                 mode: str = 'text', source_type: str = 'vocabulary',
                 audio_synthesizer=None):
        super().__init__(db, language_id, model)
        self.mode              = mode
        self.source_type       = source_type
        self.audio_synthesizer = audio_synthesizer
        self.exercise_type     = 'listening_flashcard' if mode == 'listening' else 'text_flashcard'

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        sentence = sentence_dict['sentence']
        word, definition, sense_id = self._load_sense_data(source_id)
        if not word or word.lower() not in sentence.lower():
            return None

        if self.mode == 'text':
            return self._assemble_text_flashcard(sentence, word, definition, sense_id, sentence_dict)
        else:
            return self._assemble_listening_flashcard(sentence, word, definition, sense_id, sentence_dict)

    def _load_sense_data(self, source_id: int) -> tuple[str, str, int]:
        if self.source_type == 'vocabulary':
            row = self.db.table('dim_word_senses') \
                .select('id, definition, dim_vocabulary(lemma)') \
                .eq('id', source_id).single().execute().data
            if not row:
                return '', '', 0
            vocab = row.get('dim_vocabulary') or {}
            return vocab.get('lemma', ''), row['definition'], row['id']
        elif self.source_type == 'collocation':
            row = self.db.table('corpus_collocations').select('collocation_text, id') \
                .eq('id', source_id).single().execute().data
            if not row:
                return '', '', 0
            return row['collocation_text'], '', row['id']
        return '', '', 0

    def _assemble_text_flashcard(
        self, sentence: str, word: str, definition: str, sense_id: int, sentence_dict: dict,
    ) -> dict:
        front = sentence.replace(word, f'**{word}**', 1)
        return {
            'front_sentence':   front,
            'highlight_word':   word,
            'back_sentence':    sentence,
            'back_translation': None,
            'word_of_interest': word,
            'word_definition':  definition,
            'sense_id':         sense_id,
            'source_test_id':   sentence_dict.get('test_id'),
        }

    def _assemble_listening_flashcard(
        self, sentence: str, word: str, definition: str, sense_id: int, sentence_dict: dict,
    ) -> dict | None:
        if not self.audio_synthesizer:
            return None
        try:
            file_id = str(uuid.uuid4())
            audio_url = self.audio_synthesizer.generate_and_upload(
                text=sentence,
                file_id=file_id,
            )
        except Exception:
            return None

        return {
            'front_audio_url':  audio_url,
            'back_sentence':    sentence,
            'back_translation': None,
            'word_of_interest': word,
            'word_definition':  definition,
            'sense_id':         sense_id,
            'source_test_id':   sentence_dict.get('test_id'),
        }
