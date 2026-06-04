"""
Word Sense Generator Service

Generates target-language word-sense definitions at TWO graded levels in a
single LLM call, and writes them to dim_word_senses. Used by both the test
generation orchestrator (inline, per new test) and the backfill scripts (batch).

Single-call design (numeric-key JSON, JSON mode):
    "1" = simple   — same meaning rewritten at LinguaLoop's lower child age
                     tiers (T1 "The Toddler" / T2 "The Primary Schooler")
    "2" = standard — the normal learner definition
    "3" = example_sentence — a NEW example, different from the input sentence
    "4" = part_of_speech — integer code (language-neutral legend, mapped to a
                     canonical POS string in code; never an English word)
    "5" = confidence — self-rated 0..1; replaces the old separate validation
                     call (sets is_validated / gen_confidence)
    "6" = should_skip — true only for proper nouns / numbers / symbols /
                     punctuation; function words (把, 的, が, を, the) are normal

One sense becomes TWO dim_word_senses rows (definition_level simple+standard)
at the same sense_rank, source='llm', source_ref='<model> v<prompt_version>'.
pronunciation is filled deterministically later (pypinyin / fugashi), not here.

Prompt templates (prompt_templates table, numeric-key, per language incl. ja):
- vocab_sense_selection     : pick an existing standard sense for this occurrence
- vocab_definition_generation : single-call two-level generation (above)
(vocab_validation is retired — confidence subsumes it.)
"""

import re
import json
import logging

from services.llm_service import (
    call_llm as llm_call,
    SENSE_MODEL_DEFAULT,
    SENSE_MODEL_FALLBACK,
)
from services.vocabulary.language_detection import check_text_language

logger = logging.getLogger(__name__)

# Prompt template version these call-sites are written against (source_ref tag).
SENSE_PROMPT_VERSION = 2

# Confidence at/above which a generated sense is treated as validated.
VALIDATION_CONFIDENCE_THRESHOLD = 0.7

# Language-specific notes (kept for callers/logging; prompts are now self-contained).
LINGUISTIC_NOTES = {
    "en": "English words inflect for tense, number, and comparison. Lemmas are base forms.",
    "zh": "Chinese characters do not inflect. Words may be single characters or compounds (成语, 词语).",
    "ja": "Japanese verbs and adjectives conjugate. Lemmas are dictionary forms (辞書形).",
}

LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
}

# Integer POS legend per language -> canonical, language-neutral POS string.
# The legends MUST match the numeric "4" codes in the prompt templates
# (migrations/rewrite_sense_prompts_two_level.sql).
POS_LEGENDS = {
    "zh": {1: "noun", 2: "verb", 3: "adjective", 4: "adverb", 5: "pronoun",
           6: "preposition", 7: "conjunction", 8: "particle", 9: "measure_word",
           10: "idiom", 11: "numeral", 0: "other"},
    "ja": {1: "noun", 2: "verb", 3: "adjective", 4: "adverb", 5: "pronoun",
           6: "particle", 7: "conjunction", 8: "auxiliary", 9: "adnominal",
           10: "idiom", 11: "numeral", 0: "other"},
    "en": {1: "noun", 2: "verb", 3: "adjective", 4: "adverb", 5: "pronoun",
           6: "preposition", 7: "conjunction", 8: "determiner", 9: "interjection",
           10: "phrase", 11: "numeral", 0: "other"},
}

# Fallback child-register text if dim_complexity_tiers can't be read. Mirrors the
# T1/T2 description columns (ADR-003-age-tiers).
_SIMPLE_REGISTER_FALLBACK = (
    "The Toddler (Age 4-5): 500 words, basic verbs/nouns, one idea per sentence; "
    "The Primary Schooler (Age 8-9): 2000 words, compound sentences, literal/concrete"
)


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
    Generates target-language word senses at two levels via a single LLM call.

    Entry points:
    - generate_sense(...) : inline test-gen path. Reuses an existing sense when
      one exists (selection call, or short-circuit when prefer_existing=True);
      otherwise generates a brand-new two-level sense.
    - seed_word(...)      : batch backfill path. Idempotently upserts both levels
      for the word's primary sense (adds the missing `simple` level to words that
      already have a `standard` sense). Skips source='manual' rows.
    """

    def __init__(self, openai_client, db, db_client, language_code: str,
                 language_id: int, model: str | None = None,
                 fallback_model: str | None = None,
                 prefer_existing: bool = False, dry_run: bool = False):
        """
        Args:
            openai_client: OpenAI client instance (unused by call_llm but kept for
                signature compatibility with existing call sites).
            db: Supabase admin client (for dim_word_senses / dim_vocabulary).
            db_client: TestDatabaseClient (for prompt template loading).
            language_code: ISO 639-1, e.g., 'en', 'zh', 'ja'.
            language_id: Integer language ID.
            model: Sense LLM model. Defaults to SENSE_MODEL_DEFAULT (DeepSeek V4 Flash).
            fallback_model: Used only when the primary returns invalid/empty JSON.
                Defaults to SENSE_MODEL_FALLBACK (Qwen3.6 Flash).
            prefer_existing: When True, words that already have a sense are reused
                without any LLM call (resumable backfill / throughput).
            dry_run: If True, log but don't write to DB.
        """
        self._client = openai_client
        self._db = db
        self._db_client = db_client
        self._language_code = language_code
        self._language_id = language_id
        self._model = model or SENSE_MODEL_DEFAULT
        self._fallback_model = fallback_model or SENSE_MODEL_FALLBACK
        self._prefer_existing = prefer_existing
        self._dry_run = dry_run
        self._language_name = LANGUAGE_NAMES.get(language_code, language_code)
        self._linguistic_notes = LINGUISTIC_NOTES.get(language_code, "")
        self._pos_legend = POS_LEGENDS.get(language_code, POS_LEGENDS["en"])
        self._simple_register = self._load_simple_register()

        # Cache: vocab_id -> list of existing STANDARD sense dicts
        self._sense_cache: dict[int, list[dict]] = {}

        # Stats
        self.stats = {
            'senses_created': 0,    # words that got freshly generated senses
            'senses_reused': 0,
            'senses_skipped': 0,
            'senses_failed': 0,
            'rows_written': 0,      # individual dim_word_senses rows (2 per sense)
            'fallback_used': 0,
        }

    # ------------------------------------------------------------------ setup

    def _load_simple_register(self) -> str:
        """Build the child-register guide for `simple` from dim_complexity_tiers
        T1/T2 (single source of truth, ADR-003). Falls back to a constant."""
        try:
            resp = self._db.table('dim_complexity_tiers') \
                .select('tier_code, description') \
                .in_('tier_code', ['T1', 'T2']) \
                .execute()
            by_code = {r['tier_code']: r['description'] for r in (resp.data or [])}
            parts = [by_code[c] for c in ('T1', 'T2') if by_code.get(c)]
            if parts:
                return "; ".join(parts)
        except Exception as e:
            logger.warning(f"Could not load T1/T2 register, using fallback: {e}")
        return _SIMPLE_REGISTER_FALLBACK

    # ------------------------------------------------------------- LLM helper

    def _call_llm(self, prompt: str, task_name: str,
                  max_tokens: int = 600) -> dict | None:
        """Call the sense model expecting numeric-key JSON. Falls back to the
        secondary model ONLY when the primary returns invalid/empty JSON."""
        try:
            return llm_call(
                prompt, model=self._model, temperature=0.0,
                max_tokens=max_tokens, response_format='json_object',
                pipeline='vocab_senses', task_name=task_name,
            )
        except (json.JSONDecodeError, RuntimeError, ValueError) as e:
            logger.warning(f"Primary model invalid JSON ({e}); retrying with fallback {self._fallback_model}")
        except Exception as e:
            logger.error(f"Sense LLM call failed: {e}")
            return None

        try:
            result = llm_call(
                prompt, model=self._fallback_model, temperature=0.0,
                max_tokens=max_tokens, response_format='json_object',
                pipeline='vocab_senses', task_name=f"{task_name}__fallback",
            )
            self.stats['fallback_used'] += 1
            return result
        except Exception as e:
            logger.error(f"Fallback model also failed: {e}")
            return None

    # ------------------------------------------------------------ DB helpers

    def _get_existing_senses(self, vocab_id: int) -> list[dict]:
        """Fetch existing STANDARD-level senses for a vocab_id (ordered by rank)."""
        if vocab_id in self._sense_cache:
            return self._sense_cache[vocab_id]

        if vocab_id < 0:  # dry-run fake id
            self._sense_cache[vocab_id] = []
            return []

        response = self._db.table('dim_word_senses') \
            .select('id, definition, sense_rank, example_sentence, source') \
            .eq('vocab_id', vocab_id) \
            .eq('definition_language_id', self._language_id) \
            .eq('definition_level', 'standard') \
            .order('sense_rank') \
            .execute()

        senses = response.data or []
        self._sense_cache[vocab_id] = senses
        return senses

    def _has_simple_level(self, vocab_id: int) -> bool:
        """True if the word already has at least one `simple` row (already seeded
        with the two-level treatment) — the backfill resumability gate."""
        if vocab_id < 0:
            return False
        resp = self._db.table('dim_word_senses') \
            .select('id') \
            .eq('vocab_id', vocab_id) \
            .eq('definition_language_id', self._language_id) \
            .eq('definition_level', 'simple') \
            .limit(1) \
            .execute()
        return bool(resp.data)

    def _maybe_set_pos(self, vocab_id: int, pos_code) -> None:
        """Write the canonical POS to dim_vocabulary.part_of_speech when it's
        currently blank. Best-effort; never raises into the pipeline."""
        if vocab_id < 0 or not isinstance(pos_code, int):
            return
        pos = self._pos_legend.get(pos_code)
        if not pos or pos == 'other':
            return
        try:
            self._db.table('dim_vocabulary') \
                .update({'part_of_speech': pos}) \
                .eq('id', vocab_id) \
                .or_('part_of_speech.is.null,part_of_speech.eq.') \
                .execute()
        except Exception as e:
            logger.debug(f"POS update skipped for vocab {vocab_id}: {e}")

    # --------------------------------------------------------- generation core

    def _parse_generation(self, data: dict) -> dict | None:
        """Validate a numeric-key generation payload into typed fields.

        Returns {simple, standard, example, pos_code, confidence, skip} or None
        when required text fields are missing.
        """
        simple = str(data.get('1', '') or '').strip()
        standard = str(data.get('2', '') or '').strip()
        example = str(data.get('3', '') or '').strip()
        pos_code = data.get('4')
        confidence = data.get('5')
        skip = bool(data.get('6', False))

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = None
        try:
            pos_code = int(pos_code)
        except (TypeError, ValueError):
            pos_code = None

        if not standard or not simple:
            return None
        return {
            'simple': simple, 'standard': standard, 'example': example,
            'pos_code': pos_code, 'confidence': confidence, 'skip': skip,
        }

    def _generate_payload(self, lemma: str, sentence: str) -> dict | None:
        """Run the single two-level generation call and return parsed fields."""
        template = self._db_client.get_prompt_template(
            'vocab_definition_generation', self._language_id, required=False
        )
        if not template:
            logger.warning(f"No vocab_definition_generation prompt for language_id={self._language_id}")
            return None
        try:
            prompt = template.format(
                lemma=lemma,
                sentence=sentence or '',
                simple_register=self._simple_register,
            )
        except KeyError as e:
            logger.error(f"Definition generation template missing variable: {e}")
            return None

        data = self._call_llm(prompt, task_name='vocab_definition_generation')
        if not data:
            return None
        return self._parse_generation(data)

    def _write_two_levels(self, vocab_id: int, lemma: str, fields: dict,
                          sense_rank: int) -> int | None:
        """Upsert the simple + standard rows for one sense. Returns the standard
        row's id (the canonical id used for flashcard/token-map linkage)."""
        is_validated = bool(
            fields['confidence'] is not None
            and fields['confidence'] >= VALIDATION_CONFIDENCE_THRESHOLD
        )
        # Language guard — soft. Wrong language only lowers is_validated; the
        # prompt now hard-locks output language, so no extra repair round-trip.
        ok_lang, lang_reason = check_text_language(fields['standard'], self._language_code)
        if not ok_lang:
            is_validated = False
            logger.warning(f"  {lemma}: standard def flagged wrong language ({lang_reason})")

        source_ref = f"{self._model} v{SENSE_PROMPT_VERSION}"
        example = (fields['example'] or '')[:500]

        if self._dry_run:
            logger.info(
                f"  [DRY RUN] {lemma} (rank={sense_rank}, conf={fields['confidence']}, "
                f"pos={self._pos_legend.get(fields['pos_code'])}):\n"
                f"      simple:   {fields['simple'][:80]}\n"
                f"      standard: {fields['standard'][:80]}\n"
                f"      example:  {example[:80]}"
            )
            self.stats['senses_created'] += 1
            self.stats['rows_written'] += 2
            return -1

        rows = [
            {
                'vocab_id': vocab_id,
                'definition_language_id': self._language_id,
                'definition_level': level,
                'definition': fields[level],
                'example_sentence': example,
                'sense_rank': sense_rank,
                'is_validated': is_validated,
                'gen_confidence': fields['confidence'],
                'source': 'llm',
                'source_ref': source_ref,
            }
            for level in ('simple', 'standard')
        ]
        try:
            response = self._db.table('dim_word_senses') \
                .upsert(rows, on_conflict='vocab_id,definition_language_id,definition_level,sense_rank') \
                .execute()
        except Exception as e:
            logger.error(f"Failed to upsert senses for {lemma}: {e}")
            self.stats['senses_failed'] += 1
            return None

        written = response.data or []
        self.stats['senses_created'] += 1
        self.stats['rows_written'] += len(written)
        self._maybe_set_pos(vocab_id, fields['pos_code'])
        self._sense_cache.pop(vocab_id, None)  # invalidate

        standard_id = next(
            (r['id'] for r in written if r.get('definition_level') == 'standard'),
            None,
        )
        if standard_id is None:  # upsert returned partial/none — read it back
            standard_id = self._lookup_standard_id(vocab_id, sense_rank)
        logger.debug(f"  {lemma}: wrote simple+standard at rank {sense_rank} (std id={standard_id})")
        return standard_id

    def _lookup_standard_id(self, vocab_id: int, sense_rank: int) -> int | None:
        resp = self._db.table('dim_word_senses') \
            .select('id') \
            .eq('vocab_id', vocab_id) \
            .eq('definition_language_id', self._language_id) \
            .eq('definition_level', 'standard') \
            .eq('sense_rank', sense_rank) \
            .limit(1) \
            .execute()
        return resp.data[0]['id'] if resp.data else None

    def _generate_new(self, vocab_id: int, lemma: str, sentence: str,
                      existing: list[dict]) -> int | None:
        """Generate a brand-new two-level sense at the next free rank."""
        fields = self._generate_payload(lemma, sentence)
        if not fields:
            self.stats['senses_failed'] += 1
            return None
        if fields['skip']:
            self.stats['senses_skipped'] += 1
            logger.debug(f"  {lemma}: skipped (proper noun, number, symbol, etc.)")
            return None
        next_rank = (max((s.get('sense_rank') or 0 for s in existing), default=0) + 1)
        return self._write_two_levels(vocab_id, lemma, fields, next_rank)

    def _select_sense(self, vocab_id: int, lemma: str, sentence: str,
                      existing: list[dict]) -> int | None:
        """Numeric-key selection: reuse a matching standard sense or generate a
        new one for this occurrence."""
        template = self._db_client.get_prompt_template(
            'vocab_sense_selection', self._language_id, required=False
        )
        if not template:
            # No selection prompt — fall back to reusing the primary sense.
            self.stats['senses_reused'] += 1
            return existing[0]['id']

        definitions_list = "\n".join(
            f"{i+1}. {s.get('definition', '(no definition)')}"
            for i, s in enumerate(existing)
        )
        try:
            prompt = template.format(
                lemma=lemma, sentence=sentence or '',
                definitions_list=definitions_list,
            )
        except KeyError as e:
            logger.error(f"Sense selection template missing variable: {e}")
            self.stats['senses_reused'] += 1
            return existing[0]['id']

        data = self._call_llm(prompt, task_name='vocab_sense_selection', max_tokens=60)
        selected = 0
        if data:
            try:
                selected = int(data.get('1', 0))
            except (TypeError, ValueError):
                selected = 0

        if selected > 0 and selected <= len(existing):
            self.stats['senses_reused'] += 1
            logger.debug(f"  {lemma}: reused existing sense #{selected}")
            return existing[selected - 1]['id']

        # No match -> a new sense for this occurrence.
        return self._generate_new(vocab_id, lemma, sentence, existing)

    # --------------------------------------------------------------- entry pts

    def generate_sense(self, vocab_id: int, lemma: str,
                       phrase_type: str | None, sentence: str,
                       transcript: str) -> int | None:
        """
        Inline path (test generation). Returns the STANDARD sense_id to link, or
        None if skipped/failed.

        phrase_type is accepted for call-site compatibility; the single-call
        prompt infers POS itself.
        """
        existing = self._get_existing_senses(vocab_id)

        if existing:
            if self._prefer_existing:
                self.stats['senses_reused'] += 1
                return existing[0]['id']
            return self._select_sense(vocab_id, lemma, sentence, existing)
        return self._generate_new(vocab_id, lemma, sentence, existing)

    def seed_word(self, vocab_id: int, lemma: str, sentence: str = "") -> int | None:
        """
        Batch backfill path. Idempotently writes the two-level treatment for the
        word's PRIMARY sense: adds the missing `simple` row and refreshes
        `standard` at the same rank. Returns the standard sense_id, or None.

        Resumable: when prefer_existing is set, words that already have a
        `simple` row are skipped without any LLM call. source='manual' senses
        are never overwritten.
        """
        existing = self._get_existing_senses(vocab_id)

        if self._prefer_existing and self._has_simple_level(vocab_id):
            self.stats['senses_reused'] += 1
            return existing[0]['id'] if existing else None

        if any(s.get('source') == 'manual' for s in existing):
            logger.debug(f"  {lemma}: has manual sense, skipping backfill")
            self.stats['senses_skipped'] += 1
            return existing[0]['id'] if existing else None

        fields = self._generate_payload(lemma, sentence)
        if not fields:
            self.stats['senses_failed'] += 1
            return None
        if fields['skip']:
            self.stats['senses_skipped'] += 1
            logger.debug(f"  {lemma}: skipped (proper noun, number, symbol, etc.)")
            return None

        # Upsert at the existing primary rank (so we overwrite the old standard
        # and add simple alongside it); rank 1 for a brand-new word.
        rank = existing[0]['sense_rank'] if existing else 1
        return self._write_two_levels(vocab_id, lemma, fields, rank)
