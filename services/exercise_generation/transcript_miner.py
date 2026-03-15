# services/exercise_generation/transcript_miner.py

import logging
from services.exercise_generation.config import (
    MIN_TRANSCRIPT_SENTENCES, DEFAULT_SENTENCE_TARGET,
    LLM_BATCH_SIZE,
    LANG_CHINESE, LANG_ENGLISH, LANG_JAPANESE,
)
from services.exercise_generation.language_processor import LanguageProcessor

logger = logging.getLogger(__name__)

# tests.language is a TEXT column ('cn','en','jp'), not an integer FK
_LANGUAGE_ID_TO_CODE: dict[int, str] = {
    LANG_CHINESE:  'cn',
    LANG_ENGLISH:  'en',
    LANG_JAPANESE: 'jp',
}


class TranscriptMiner:
    """
    Extracts usable sentences from tests.transcript for a given source.
    Uses the Reuse First strategy; does not call the LLM.
    """

    def __init__(self, db, language_processor: LanguageProcessor):
        self.db = db
        self.lp = language_processor

    def mine(
        self,
        source_type: str,
        source_id: int,
        language_id: int,
    ) -> list[dict]:
        """
        Entry point. Dispatches to the appropriate mining strategy.
        Returns deduplicated list of sentence dicts.
        """
        if source_type == 'vocabulary':
            raw = self._mine_vocabulary(source_id, language_id)
        elif source_type == 'grammar':
            raw = self._mine_grammar(source_id, language_id)
        elif source_type == 'collocation':
            raw = self._mine_collocation(source_id, language_id)
        else:
            raise ValueError(f"Unknown source_type: {source_type}")

        return SentenceFilter.deduplicate(raw)

    def _mine_vocabulary(self, sense_id: int, language_id: int) -> list[dict]:
        """Vocabulary mining via GIN-indexed vocab_sense_ids array."""
        result = self.db.rpc('tests_containing_sense', {
            'p_sense_id': sense_id,
            'p_language_id': language_id,
        }).execute()

        sentences = []
        for test in (result.data or []):
            transcript = test.get('transcript', '')
            token_map  = test.get('vocab_token_map', [])
            cefr       = self._difficulty_to_cefr(test.get('difficulty', 2))

            target_tokens = [entry[0] for entry in token_map if entry[1] == sense_id]
            if not target_tokens:
                continue

            for token_text in target_tokens:
                extracted = self._extract_sentences_containing(
                    transcript, token_text, test['id'], cefr
                )
                sentences.extend(extracted)

        return sentences

    def _mine_grammar(self, pattern_id: int, language_id: int) -> list[dict]:
        """Grammar mining: scan transcripts for pattern matches via regex heuristics."""
        pattern_row = self.db.table('dim_grammar_patterns') \
            .select('pattern_code, cefr_level') \
            .eq('id', pattern_id) \
            .single() \
            .execute().data

        pattern_code = pattern_row['pattern_code']

        lang_code = _LANGUAGE_ID_TO_CODE.get(language_id)
        if not lang_code:
            raise ValueError(f"Unknown language_id: {language_id}")

        tests = self.db.table('tests') \
            .select('id, transcript, difficulty') \
            .eq('language', lang_code) \
            .eq('is_active', True) \
            .execute()

        sentences = []
        for test in (tests.data or []):
            transcript = test.get('transcript', '')
            cefr       = self._difficulty_to_cefr(test.get('difficulty', 2))
            raw_sents  = self.lp.split_sentences(transcript)

            for sent in raw_sents:
                if self.lp.matches_pattern(sent, pattern_code):
                    sentences.append(self._make_sentence_dict(sent, test['id'], cefr))

        return sentences

    def _mine_collocation(self, collocation_id: int, language_id: int) -> list[dict]:
        """Collocation mining: substring-search all active transcripts."""
        col_row = self.db.table('corpus_collocations') \
            .select('collocation_text') \
            .eq('id', collocation_id) \
            .single() \
            .execute().data

        collocation_text = col_row['collocation_text']

        lang_code = _LANGUAGE_ID_TO_CODE.get(language_id)
        if not lang_code:
            raise ValueError(f"Unknown language_id: {language_id}")

        tests = self.db.table('tests') \
            .select('id, transcript, difficulty') \
            .eq('language', lang_code) \
            .eq('is_active', True) \
            .execute()

        sentences = []
        for test in (tests.data or []):
            transcript = test.get('transcript', '')
            cefr       = self._difficulty_to_cefr(test.get('difficulty', 2))
            raw_sents  = self.lp.split_sentences(transcript)

            for sent in raw_sents:
                if self.lp.contains_collocation(sent, collocation_text):
                    sentences.append(self._make_sentence_dict(sent, test['id'], cefr))

        return sentences

    def _extract_sentences_containing(
        self, transcript: str, token_text: str, test_id: str, cefr: str,
    ) -> list[dict]:
        raw_sents = self.lp.split_sentences(transcript)
        return [
            self._make_sentence_dict(sent, test_id, cefr)
            for sent in raw_sents
            if self.lp.contains_collocation(sent, token_text)
        ]

    @staticmethod
    def _make_sentence_dict(sentence: str, test_id: str, cefr: str) -> dict:
        return {
            'sentence':    sentence,
            'translation': None,
            'topic':       'existing_content',
            'source':      'transcript',
            'cefr_level':  cefr,
            'test_id':     test_id,
        }

    @staticmethod
    def _difficulty_to_cefr(difficulty: float) -> str:
        if difficulty < 1.5:  return 'A1'
        if difficulty < 2.5:  return 'A2'
        if difficulty < 3.5:  return 'B1'
        if difficulty < 4.0:  return 'B2'
        if difficulty < 4.5:  return 'C1'
        return 'C2'


class SentenceFilter:
    """Stateless utility for deduplication and quality filtering of sentence pools."""

    @staticmethod
    def deduplicate(sentences: list[dict]) -> list[dict]:
        seen: set[str] = set()
        result = []
        for s in sentences:
            key = s.get('sentence', '').lower().strip()
            if key and key not in seen:
                seen.add(key)
                result.append(s)
        return result

    @staticmethod
    def filter_quality(sentences: list[dict], language_id: int) -> list[dict]:
        from services.exercise_generation.config import LANG_CHINESE, LANG_JAPANESE
        valid = []
        for s in sentences:
            text = s.get('sentence', '').strip()
            if not text:
                continue
            if language_id == LANG_CHINESE:
                length = len(text)
                lo, hi = 5, 80
            elif language_id == LANG_JAPANESE:
                length = len(text)
                lo, hi = 5, 100
            else:
                length = len(text.split())
                lo, hi = 5, 80
            if lo <= length <= hi:
                valid.append(s)
        return valid


class LLMSentenceGenerator:
    """
    LLM fallback for sentence generation when transcript mining
    yields < MIN_TRANSCRIPT_SENTENCES.
    """

    def __init__(self, db, llm_client, model: str):
        self.db         = db
        self.llm_client = llm_client
        self.model      = model

    # Map source_type to its dedicated prompt template
    _TEMPLATE_BY_SOURCE: dict[str, str] = {
        'grammar':     'exercise_sentence_generation',
        'vocabulary':  'vocab_sentence_generation',
        'collocation': 'collocation_sentence_generation',
    }

    def generate(
        self, source_type: str, source_id: int, language_id: int, count: int,
    ) -> list[dict]:
        source_data   = self._load_source_data(source_type, source_id)
        template_name = self._TEMPLATE_BY_SOURCE.get(source_type, 'exercise_sentence_generation')
        template      = self._load_prompt_template(template_name)
        all_sentences: list[dict] = []

        for offset in range(0, count, LLM_BATCH_SIZE):
            batch_count = min(LLM_BATCH_SIZE, count - offset)
            prompt = template.format(count=batch_count, **source_data)
            try:
                result = self.llm_client(prompt, model=self.model, response_format='json')
                all_sentences.extend(result if isinstance(result, list) else [])
            except Exception as exc:
                logger.warning("LLM sentence generation batch failed: %s", exc)

        filtered = SentenceFilter.filter_quality(all_sentences, language_id)
        return SentenceFilter.deduplicate(filtered)

    def _load_source_data(self, source_type: str, source_id: int) -> dict:
        if source_type == 'grammar':
            row = self.db.table('dim_grammar_patterns') \
                .select('pattern_code, description, example_sentence, cefr_level') \
                .eq('id', source_id).single().execute().data
            return row or {}
        elif source_type == 'vocabulary':
            row = self.db.table('dim_word_senses') \
                .select('definition, dim_vocabulary(lemma)') \
                .eq('id', source_id).single().execute().data
            if not row:
                return {}
            vocab = row.get('dim_vocabulary') or {}
            return {
                'word': vocab.get('lemma', ''),
                'definition': row.get('definition', ''),
                'cefr_level': 'B1',
            }
        elif source_type == 'collocation':
            row = self.db.table('corpus_collocations') \
                .select('collocation_text, pos_pattern') \
                .eq('id', source_id).single().execute().data
            return row or {}
        return {}

    def _load_prompt_template(self, task_name: str) -> str:
        result = self.db.table('prompt_templates') \
            .select('template_text') \
            .eq('task_name', task_name) \
            .order('version', desc=True) \
            .limit(1) \
            .execute()
        if not result.data:
            raise RuntimeError(f"No prompt template found for task_name='{task_name}'")
        return result.data[0]['template_text']


def get_sentence_pool(
    source_type: str,
    source_id: int,
    language_id: int,
    db,
    llm_client,
    model: str,
    target_count: int = DEFAULT_SENTENCE_TARGET,
) -> list[dict]:
    """
    Top-level function: build sentence pool using Reuse First strategy.
    Calls TranscriptMiner first; falls back to LLMSentenceGenerator if needed.
    """
    lp      = LanguageProcessor.for_language(language_id)
    miner   = TranscriptMiner(db, lp)
    mined   = miner.mine(source_type, source_id, language_id)
    mined   = SentenceFilter.filter_quality(mined, language_id)

    if len(mined) >= MIN_TRANSCRIPT_SENTENCES:
        return mined[:target_count]

    needed    = target_count - len(mined)
    generator = LLMSentenceGenerator(db, llm_client, model)
    generated = generator.generate(source_type, source_id, language_id, needed)

    combined = SentenceFilter.deduplicate(mined + generated)
    return combined[:target_count]
