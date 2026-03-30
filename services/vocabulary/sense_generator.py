"""
Word Sense Generator Service

Generates and validates word sense definitions using LLM prompts.
Used by both the test generation orchestrator (inline) and the
backfill script (batch).

Prompt templates used (from prompt_templates table):
- vocab_sense_selection (id=31): Pick existing definition or flag need for new one
- vocab_definition_generation (id=32): Generate new definition for a word in context
- vocab_validation (id=33): Quality-check a proposed definition
"""

import re
import json
import logging

from services.llm_service import call_llm as llm_call
from services.vocabulary.language_detection import check_text_language

logger = logging.getLogger(__name__)

# Language-specific notes for LLM prompts
LINGUISTIC_NOTES = {
    "en": "English words inflect for tense, number, and comparison. Lemmas are base forms.",
    "cn": "Chinese characters do not inflect. Words may be single characters or compounds (成语, 词语).",
    "jp": "Japanese verbs and adjectives conjugate. Lemmas are dictionary forms (辞書形).",
}

LANGUAGE_NAMES = {
    "en": "English",
    "cn": "Chinese",
    "jp": "Japanese",
}


def find_sentence(transcript: str, lemma: str) -> str:
    """
    Find the sentence in transcript that contains the given lemma.

    Splits on sentence-ending punctuation (. ! ? and CJK equivalents),
    returns first sentence containing the lemma (case-insensitive).
    Falls back to the full transcript if no match.
    """
    sentences = re.split(r'[.!?。！？\n]+', transcript)
    sentences = [s.strip() for s in sentences if s.strip()]

    # Try exact match first
    for s in sentences:
        if lemma in s:
            return s

    # Try case-insensitive match
    lemma_lower = lemma.lower()
    for s in sentences:
        if lemma_lower in s.lower():
            return s

    # Fallback: return full transcript (truncated)
    return transcript[:500]


class SenseGenerator:
    """
    Generates and validates word sense definitions using LLM.

    Uses three prompt templates from the database:
    - vocab_sense_selection: Pick existing def or flag new one needed
    - vocab_definition_generation: Generate new definition
    - vocab_validation: Quality-check a proposed definition
    """

    def __init__(self, openai_client, db, db_client, language_code: str,
                 language_id: int, model: str, dry_run: bool = False):
        """
        Args:
            openai_client: OpenAI client instance (direct or via OpenRouter)
            db: Supabase admin client (for dim_word_senses queries)
            db_client: TestDatabaseClient (for prompt template loading)
            language_code: e.g., 'en', 'cn', 'jp'
            language_id: Integer language ID
            model: LLM model name (from LanguageConfig.prose_model)
            dry_run: If True, log but don't write to DB
        """
        self._client = openai_client
        self._db = db
        self._db_client = db_client
        self._language_code = language_code
        self._language_id = language_id
        self._model = model
        self._dry_run = dry_run
        self._language_name = LANGUAGE_NAMES.get(language_code, language_code)
        self._linguistic_notes = LINGUISTIC_NOTES.get(language_code, "")

        # Cache: vocab_id → list of existing sense dicts
        self._sense_cache: dict[int, list[dict]] = {}

        # Stats
        self.stats = {
            'senses_created': 0,
            'senses_reused': 0,
            'senses_skipped': 0,
            'senses_failed': 0,
        }

    def _get_existing_senses(self, vocab_id: int) -> list[dict]:
        """Fetch existing word senses for a vocab_id."""
        if vocab_id in self._sense_cache:
            return self._sense_cache[vocab_id]

        if vocab_id < 0:
            # Dry-run fake ID
            self._sense_cache[vocab_id] = []
            return []

        response = self._db.table('dim_word_senses') \
            .select('id, definition, sense_rank, example_sentence') \
            .eq('vocab_id', vocab_id) \
            .order('sense_rank') \
            .execute()

        senses = response.data or []
        self._sense_cache[vocab_id] = senses
        return senses

    def _call_llm(self, prompt: str, max_tokens: int = 800) -> dict | None:
        """Make an LLM call expecting a JSON response. Returns parsed dict or None."""
        try:
            return llm_call(
                prompt,
                model=self._model,
                temperature=0.0,
                max_tokens=max_tokens,
                response_format='json_object',
            )
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None

    def _select_sense(self, vocab_id: int, lemma: str, sentence: str,
                      transcript: str, existing: list[dict]) -> int | None:
        """
        Call vocab_sense_selection prompt to check if an existing definition matches.

        Returns:
            sense_id if existing match found, or new sense_id if created, or None on skip/failure.
        """
        template = self._db_client.get_prompt_template(
            'vocab_sense_selection', self._language_id
        )
        if not template:
            logger.warning(f"No vocab_sense_selection prompt for language_id={self._language_id}")
            return None

        # Format definitions list
        definitions_list = "\n".join(
            f"{i+1}. {s.get('definition', '(no definition)')}"
            for i, s in enumerate(existing)
        )

        try:
            prompt = template.format(
                language=self._language_name,
                linguistic_notes=self._linguistic_notes,
                lemma=lemma,
                sentence=sentence,
                context=transcript[:1000],
                definitions_list=definitions_list,
            )
        except KeyError as e:
            logger.error(f"Sense selection template missing variable: {e}")
            return None

        data = self._call_llm(prompt)
        if not data:
            self.stats['senses_failed'] += 1
            return None

        selected_index = data.get('selected_index', 0)

        if isinstance(selected_index, int) and selected_index > 0:
            # Existing sense matches
            idx = selected_index - 1  # Convert 1-based to 0-based
            if 0 <= idx < len(existing):
                self.stats['senses_reused'] += 1
                logger.debug(f"  {lemma}: reused existing sense #{selected_index}")
                return existing[idx]['id']

        # Need a new sense — use the new_definition from response
        new_def = data.get('new_definition', '')
        if not new_def:
            self.stats['senses_skipped'] += 1
            return None

        # Check language before proceeding — new_definition should be in target language
        is_correct, reason = check_text_language(new_def, self._language_code)
        if not is_correct:
            logger.warning(f"  {lemma}: new_definition from sense selection in wrong language ({reason})")
            corrected = self._fix_definition_language(lemma, new_def)
            if corrected:
                is_correct_now, _ = check_text_language(corrected, self._language_code)
                if is_correct_now:
                    new_def = corrected

        return self._validate_and_insert(vocab_id, lemma, new_def, sentence, existing)

    def _generate_new(self, vocab_id: int, lemma: str, phrase_type: str | None,
                      sentence: str, transcript: str) -> int | None:
        """
        Call vocab_definition_generation prompt for a brand-new word.

        Returns:
            sense_id if created, or None on skip/failure.
        """
        template = self._db_client.get_prompt_template(
            'vocab_definition_generation', self._language_id
        )
        if not template:
            logger.warning(f"No vocab_definition_generation prompt for language_id={self._language_id}")
            return None

        try:
            prompt = template.format(
                language=self._language_name,
                linguistic_notes=self._linguistic_notes,
                lemma=lemma,
                phrase_type=phrase_type or 'word',
                sentence=sentence,
                context=transcript[:1000],
            )
        except KeyError as e:
            logger.error(f"Definition generation template missing variable: {e}")
            return None

        data = self._call_llm(prompt)
        if not data:
            self.stats['senses_failed'] += 1
            return None

        # Check if the LLM says to skip this word
        if data.get('should_skip', False):
            self.stats['senses_skipped'] += 1
            logger.debug(f"  {lemma}: skipped (proper noun, number, etc.)")
            return None

        definition = data.get('definition', '')
        if not definition:
            self.stats['senses_failed'] += 1
            return None

        return self._validate_and_insert(vocab_id, lemma, definition, sentence, [])

    def _fix_definition_language(self, lemma: str, definition: str) -> str | None:
        """Attempt to rewrite a definition in the correct language via LLM."""
        prompt = (
            f"The following definition for \"{lemma}\" is in the wrong language. "
            f"Rewrite it in {self._language_name}. Keep the same meaning.\n\n"
            f"Definition: \"{definition}\"\n\n"
            f"Reply with ONLY a JSON object: {{\"definition\": \"...\"}}"
        )
        data = self._call_llm(prompt, max_tokens=200)
        if data:
            return data.get('definition', '').strip() or None
        return None

    def _validate_and_insert(self, vocab_id: int, lemma: str, definition: str,
                             sentence: str, existing: list[dict]) -> int | None:
        """
        Validate a definition via LLM, then insert into dim_word_senses.

        Returns:
            sense_id if inserted, or None on failure.
        """
        # Language check — definition should be in the target language
        is_correct_lang, lang_reason = check_text_language(definition, self._language_code)
        if not is_correct_lang:
            logger.warning(
                f"  {lemma}: definition in wrong language ({lang_reason}), "
                f"attempting correction..."
            )
            corrected = self._fix_definition_language(lemma, definition)
            if corrected:
                is_correct_now, _ = check_text_language(corrected, self._language_code)
                if is_correct_now:
                    definition = corrected
                    logger.info(f"  {lemma}: definition language corrected")
                else:
                    logger.warning(f"  {lemma}: correction still wrong language, proceeding anyway")

        # Validation step
        is_valid, validation_notes = self._validate(lemma, definition, sentence)

        next_rank = len(existing) + 1

        if self._dry_run:
            status = "VALID" if is_valid else "LOW QUALITY"
            logger.info(
                f"  [DRY RUN] {lemma}: \"{definition[:60]}...\" "
                f"({status}, rank={next_rank})"
            )
            self.stats['senses_created'] += 1
            return -1  # Fake ID

        # Insert into dim_word_senses
        row = {
            'vocab_id': vocab_id,
            'definition_language_id': self._language_id,
            'definition': definition,
            'example_sentence': sentence[:500],
            'sense_rank': next_rank,
            'is_validated': is_valid,
            'validation_notes': validation_notes,
        }

        try:
            response = self._db.table('dim_word_senses') \
                .insert(row) \
                .execute()

            if response.data and len(response.data) > 0:
                sense_id = response.data[0]['id']
                self.stats['senses_created'] += 1
                # Update cache
                if vocab_id in self._sense_cache:
                    self._sense_cache[vocab_id].append(response.data[0])
                logger.debug(f"  {lemma}: created sense #{next_rank} (id={sense_id})")
                return sense_id
            else:
                self.stats['senses_failed'] += 1
                return None
        except Exception as e:
            logger.error(f"Failed to insert sense for {lemma}: {e}")
            self.stats['senses_failed'] += 1
            return None

    def _validate(self, lemma: str, definition: str, sentence: str) -> tuple[bool, str]:
        """
        Call vocab_validation prompt to quality-check a definition.

        Returns:
            (is_valid, validation_notes) — is_valid True if score >= 7
        """
        template = self._db_client.get_prompt_template(
            'vocab_validation', self._language_id
        )
        if not template:
            # No validation prompt — accept by default
            return True, "No validation prompt available"

        try:
            prompt = template.format(
                language=self._language_name,
                lemma=lemma,
                definition=definition,
                sentence=sentence,
            )
        except KeyError as e:
            logger.error(f"Validation template missing variable: {e}")
            return True, f"Template error: {e}"

        data = self._call_llm(prompt, max_tokens=400)
        if not data:
            return True, "Validation call failed — accepted by default"

        score = data.get('score', 0)
        notes = data.get('notes', data.get('feedback', ''))

        if isinstance(score, (int, float)):
            is_valid = score >= 7
        else:
            is_valid = True

        return is_valid, f"Score: {score}. {notes}"

    def generate_sense(self, vocab_id: int, lemma: str,
                       phrase_type: str | None, sentence: str,
                       transcript: str) -> int | None:
        """
        Generate or select a word sense definition.

        Returns:
            sense_id or None if skipped/failed.
        """
        existing = self._get_existing_senses(vocab_id)

        if existing:
            return self._select_sense(vocab_id, lemma, sentence, transcript, existing)
        else:
            return self._generate_new(vocab_id, lemma, phrase_type, sentence, transcript)
