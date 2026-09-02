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
import os
import json
import logging
import threading
import time
from functools import wraps

import httpx

from services.llm_service import (
    call_llm as llm_call,
    SENSE_MODEL_DEFAULT,
    SENSE_MODEL_FALLBACK,
)
from services.vocabulary.language_detection import check_text_language

logger = logging.getLogger(__name__)

# TASK-737: transient network faults on the shared Supabase client. Plain
# SELECT/INSERT calls here had no retry at all — harmless under the old
# serial per-word loop, but parallelizing generate_sense() across a worker
# pool puts far more concurrent load on that ONE shared client (and its
# connection pool) than a single request at a time ever did, and
# "Server disconnected" (httpx.RemoteProtocolError) started reaching callers
# as an outright failure instead of a retried blip. Mirrors llm_service.py's
# _RETRYABLE for the same class of fault, on the DB client instead of the
# LLM client.
_DB_RETRYABLE = (
    httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadError,
    httpx.WriteError,
)


def retry_transient_db_call(fn):
    """Retry a Supabase call up to 3x (0.5s/1s backoff) on a transient
    connection fault. Reused by orchestrator.py's _get_or_create_vocab_id."""
    @wraps(fn)
    def _wrapped(*args, **kwargs):
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                return fn(*args, **kwargs)
            except _DB_RETRYABLE as exc:
                last_exc = exc
                if attempt < 2:
                    logger.warning(
                        "%s: transient DB error (attempt %d/3): %s — retrying",
                        fn.__name__, attempt + 1, exc,
                    )
                    time.sleep(0.5 * (2 ** attempt))
        raise last_exc
    return _wrapped

# Prompt template version these call-sites are written against (source_ref tag).
SENSE_PROMPT_VERSION = 2

# Confidence at/above which a generated sense is treated as validated.
VALIDATION_CONFIDENCE_THRESHOLD = 0.7

# Output ceiling for a batched generation call. Below the 64k that current
# frontier models allow, with headroom: a batch that runs out of output tokens
# is truncated mid-JSON rather than erroring, so the cost of guessing high is a
# silently short response.
_BATCH_MAX_OUTPUT_TOKENS = int(os.getenv('SENSE_BATCH_MAX_OUTPUT_TOKENS', '32000'))

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
                 prefer_existing: bool = False, dry_run: bool = False,
                 generation_max_tokens: int = 600):
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
            generation_max_tokens: max_tokens for the two-level generation call
                (_generate_payload / _generate_new). 600 is enough for a plain
                chat model, but a *reasoning* model (observed: qwen/qwen3.7-flash,
                qwen/qwen3.6-flash under OpenRouter) spends this budget entirely on
                hidden reasoning tokens before ever emitting the JSON answer —
                finish_reason='length', content=None, surfacing here as "LLM
                returned empty content" on BOTH primary and fallback. Verified
                qwen3.7-flash needs ~2200 reasoning tokens for a single word sense;
                callers that pass a reasoning-model slug must raise this
                accordingly (confirmed working at 4000). Selection calls
                (_select_sense) are unaffected — they pass their own max_tokens.
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
        self._generation_max_tokens = generation_max_tokens
        self._language_name = LANGUAGE_NAMES.get(language_code, language_code)
        self._linguistic_notes = LINGUISTIC_NOTES.get(language_code, "")
        self._pos_legend = POS_LEGENDS.get(language_code, POS_LEGENDS["en"])
        self._simple_register = self._load_simple_register()

        # Cache: vocab_id -> list of existing STANDARD sense dicts.
        # Guarded by _lock — TASK-737: the inline test-gen path now fans
        # generate_sense() out across a thread pool (one call per extracted
        # vocab word), so this cache and self.stats below are shared mutable
        # state accessed concurrently for the first time.
        self._sense_cache: dict[int, list[dict]] = {}
        self._lock = threading.Lock()

        # Stats
        self.stats = {
            'senses_created': 0,    # words that got freshly generated senses
            'senses_reused': 0,
            'senses_skipped': 0,
            'senses_failed': 0,
            'rows_written': 0,      # individual dim_word_senses rows (2 per sense)
            'fallback_used': 0,
            # Primary AND fallback both failed for one call. Distinct from
            # senses_failed: this is the model surface giving up, not a word
            # the model declined — the signal that tells a run report whether a
            # vocab shortfall is a provider outage or ordinary attrition.
            'both_models_failed': 0,
            # TASK-521 embed-on-create. Counted separately from senses_failed
            # because a sense written without its vector is a live, usable
            # sense — a degraded enrichment, not a generation failure.
            'embeddings_written': 0,
            'embeddings_failed': 0,
        }

    def _bump(self, key: str, n: int = 1) -> None:
        """Thread-safe ``self.stats[key] += n``.

        Plain ``self.stats[key] += n`` is a load-add-store across three
        bytecodes — safe under a single caller, but generate_sense() is now
        called concurrently (one thread per extracted vocab word), so two
        threads incrementing the same counter can lose an update without a
        lock around it.
        """
        with self._lock:
            self.stats[key] = self.stats.get(key, 0) + n

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
        """Call the sense model expecting numeric-key JSON, falling back to the
        secondary model when the primary fails.

        The fallback fires on ANY persistent primary failure, not only on bad
        JSON. ``call_llm`` already gives transient API errors three tenacity
        attempts and gives malformed/empty JSON its own repair turn, so anything
        reaching here has survived that ladder and is a property of the model
        rather than of the roll — a delisted slug, a persistent 4xx, a hard
        timeout. Those are precisely what a fallback model is for. Routing only
        bad JSON to it meant a dead primary returned None for *every word in
        the run* while a healthy fallback sat unused.
        """
        try:
            return llm_call(
                prompt, model=self._model, temperature=0.0,
                max_tokens=max_tokens, response_format='json_object',
                pipeline='vocab_senses', task_name=task_name,
                language_code=self._language_code,
            )
        except Exception as e:
            kind = ('invalid JSON'
                    if isinstance(e, (json.JSONDecodeError, RuntimeError))
                    else type(e).__name__)
            logger.warning(
                f"Primary sense model {self._model} failed ({kind}: {e}); "
                f"retrying with fallback {self._fallback_model}"
            )

        try:
            result = llm_call(
                prompt, model=self._fallback_model, temperature=0.0,
                max_tokens=max_tokens, response_format='json_object',
                pipeline='vocab_senses', task_name=f"{task_name}__fallback",
                language_code=self._language_code,
            )
            self._bump('fallback_used')
            return result
        except Exception as e:
            logger.error(
                f"Both sense models failed for {task_name} "
                f"({self._model} then {self._fallback_model}): {e}"
            )
            self._bump('both_models_failed')
            return None

    # ------------------------------------------------------------ DB helpers

    @retry_transient_db_call
    def _get_existing_senses(self, vocab_id: int) -> list[dict]:
        """Fetch existing STANDARD-level senses for a vocab_id (ordered by rank).

        The dict read/write is locked; the DB round-trip below deliberately
        is not, so a cache miss never blocks other threads on I/O. Two
        threads missing the cache for the same vocab_id at once both hit the
        DB and both write the same (idempotent) result — wasted work, not a
        correctness bug, and rare since a test's vocab_items are distinct
        lemmas.
        """
        with self._lock:
            cached = self._sense_cache.get(vocab_id)
        if cached is not None:
            return cached

        if vocab_id < 0:  # dry-run fake id
            with self._lock:
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
        with self._lock:
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

    def _render_generation_prompt(self, lemma: str, sentence: str) -> str | None:
        """Render the per-word generation prompt from prompt_templates.

        Shared by the single-word and batched paths so batching cannot fork the
        prompt corpus into a second copy that drifts from the DB.
        """
        template = self._db_client.get_prompt_template(
            'vocab_definition_generation', self._language_id, required=False
        )
        if not template:
            logger.warning(f"No vocab_definition_generation prompt for language_id={self._language_id}")
            return None
        try:
            return template.format(
                lemma=lemma,
                sentence=sentence or '',
                simple_register=self._simple_register,
            )
        except KeyError as e:
            logger.error(f"Definition generation template missing variable: {e}")
            return None

    def _generate_payload(self, lemma: str, sentence: str) -> dict | None:
        """Run the single two-level generation call and return parsed fields."""
        prompt = self._render_generation_prompt(lemma, sentence)
        if not prompt:
            return None

        data = self._call_llm(
            prompt, task_name='vocab_definition_generation',
            max_tokens=self._generation_max_tokens,
        )
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
            self._bump('senses_created')
            self._bump('rows_written', 2)
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
            self._bump('senses_failed')
            return None

        written = response.data or []
        self._bump('senses_created')
        self._bump('rows_written', len(written))
        self._maybe_set_pos(vocab_id, fields['pos_code'])
        self._sense_cache.pop(vocab_id, None)  # invalidate

        self._embed_new_senses(lemma, written)

        standard_id = next(
            (r['id'] for r in written if r.get('definition_level') == 'standard'),
            None,
        )
        if standard_id is None:  # upsert returned partial/none — read it back
            standard_id = self._lookup_standard_id(vocab_id, sense_rank)
        logger.debug(f"  {lemma}: wrote simple+standard at rank {sense_rank} (std id={standard_id})")
        return standard_id

    def _embed_new_senses(self, lemma: str, written: list) -> None:
        """Embed freshly-written senses (TASK-521 embed-on-create).

        Without this, every sense created after the one-off backfill carries a
        NULL embedding, and the features that read it — the mid-cosine
        distractor band, ``definition_match`` upgrades, syn/ant sanity checks —
        degrade silently for exactly the newest words. The backfill would have
        to be re-run forever to stay correct.

        Both levels are embedded, not just ``standard``: the backfill embeds
        every row with a NULL vector, so skipping ``simple`` here would leave
        the corpus in a state a later backfill "fixes" — the drift this exists
        to prevent.

        Failure is logged and swallowed. An embedding is an enrichment; a word
        that exists without one is usable, and a word that failed to be created
        because its embedding call timed out is not.
        """
        if self._dry_run or not written:
            return

        # Imported lazily: the embedding client pulls in the OpenAI stack, and
        # sense generation must stay importable in environments (tests, offline
        # CLI runs) that never embed anything.
        try:
            from scripts.backfill_sense_embeddings import build_text
            from services.topic_generation.agents.embedder import EmbeddingService
        except Exception as exc:
            logger.debug("embed-on-create unavailable: %s", exc)
            return

        rows = []
        for row in written:
            sense_id = row.get('id')
            text = build_text(lemma, row.get('definition'))
            if sense_id and text:
                rows.append((sense_id, text))
        if not rows:
            return

        try:
            vectors = EmbeddingService().embed_batch([text for _, text in rows])
        except Exception as exc:
            logger.warning("  %s: embed-on-create failed: %s", lemma, exc)
            self._bump('embeddings_failed', len(rows))
            return

        for (sense_id, _), vector in zip(rows, vectors):
            if not vector:
                self._bump('embeddings_failed')
                continue
            try:
                self._db.table('dim_word_senses').update(
                    {'embedding': vector}).eq('id', sense_id).execute()
                self._bump('embeddings_written')
            except Exception as exc:
                logger.warning("  %s: could not store embedding for sense %s: %s",
                               lemma, sense_id, exc)
                self._bump('embeddings_failed')

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
            self._bump('senses_failed')
            return None
        if fields['skip']:
            self._bump('senses_skipped')
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
            self._bump('senses_reused')
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
            self._bump('senses_reused')
            return existing[0]['id']

        data = self._call_llm(prompt, task_name='vocab_sense_selection', max_tokens=60)
        selected = 0
        if data:
            try:
                selected = int(data.get('1', 0))
            except (TypeError, ValueError):
                selected = 0

        if selected > 0 and selected <= len(existing):
            self._bump('senses_reused')
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
                self._bump('senses_reused')
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
            self._bump('senses_reused')
            return existing[0]['id'] if existing else None

        if any(s.get('source') == 'manual' for s in existing):
            logger.debug(f"  {lemma}: has manual sense, skipping backfill")
            self._bump('senses_skipped')
            return existing[0]['id'] if existing else None

        fields = self._generate_payload(lemma, sentence)
        if not fields:
            self._bump('senses_failed')
            return None
        if fields['skip']:
            self._bump('senses_skipped')
            logger.debug(f"  {lemma}: skipped (proper noun, number, symbol, etc.)")
            return None

        # Upsert at the existing primary rank (so we overwrite the old standard
        # and add simple alongside it); rank 1 for a brand-new word.
        rank = existing[0]['sense_rank'] if existing else 1
        return self._write_two_levels(vocab_id, lemma, fields, rank)

    # ------------------------------------------------------- batched backfill

    def _batch_skip_reason(self, vocab_id: int) -> str | None:
        """Why this word needs no LLM call, or None if it does.

        The same two guards ``seed_word`` applies, hoisted so a batch can drop
        skippable words *before* they consume a slot in a prompt.
        """
        if self._prefer_existing and self._has_simple_level(vocab_id):
            return 'senses_reused'
        if any(s.get('source') == 'manual' for s in self._get_existing_senses(vocab_id)):
            return 'senses_skipped'
        return None

    def seed_words_batch(
        self,
        words: list[tuple[int, str]],
        batch_size: int = 100,
        sentences: dict[int, str] | None = None,
    ) -> dict[int, int | None]:
        """Seed many words using multi-item prompts instead of one call per word.

        Same semantics as calling :meth:`seed_word` for each entry — the same
        resume guards, the same template, the same write path — but N words share
        one LLM turn. That matters most under the headless Claude Code transport,
        where each call is a process spawn against a subscription rate limit
        rather than a metered HTTP request.

        Words whose batch response is missing or malformed are automatically
        retried in progressively smaller batches (see services/batch_prompting.py),
        so one bad item costs a few extra small calls rather than the batch.

        Args:
            words:      [(vocab_id, lemma), …]
            batch_size: Words per LLM call. 1 falls back to the unbatched path.
            sentences:  Optional vocab_id -> example sentence for context.

        Returns:
            vocab_id -> standard sense_id (or None where nothing was written).
        """
        from services.batch_prompting import run_batched

        sentences = sentences or {}
        out: dict[int, int | None] = {}

        # Drop the skippable words first so they never occupy a batch slot.
        pending: list[tuple[int, str]] = []
        for vocab_id, lemma in words:
            reason = self._batch_skip_reason(vocab_id)
            if reason:
                self._bump(reason)
                existing = self._get_existing_senses(vocab_id)
                out[vocab_id] = existing[0]['id'] if existing else None
            else:
                pending.append((vocab_id, lemma))

        if not pending:
            return out

        payloads = run_batched(
            pending,
            render=lambda w: self._render_generation_prompt(w[1], sentences.get(w[0], '')),
            call=lambda prompt: self._call_llm(
                prompt,
                task_name='vocab_definition_generation',
                # One item's budget times the batch — clamped, because asking for
                # more than the model can emit does not raise. The response is
                # silently truncated mid-JSON, which surfaces as "the last 40
                # items are missing" rather than as an error.
                max_tokens=min(
                    self._generation_max_tokens * max(1, batch_size),
                    _BATCH_MAX_OUTPUT_TOKENS,
                ),
            ),
            batch_size=batch_size,
            validate=self._parse_generation,
        )

        for position, (vocab_id, lemma) in enumerate(pending):
            fields = payloads.get(position)
            if not fields:
                self._bump('senses_failed')
                out[vocab_id] = None
                continue
            if fields['skip']:
                self._bump('senses_skipped')
                logger.debug(f"  {lemma}: skipped (proper noun, number, symbol, etc.)")
                out[vocab_id] = None
                continue
            existing = self._get_existing_senses(vocab_id)
            rank = existing[0]['sense_rank'] if existing else 1
            out[vocab_id] = self._write_two_levels(vocab_id, lemma, fields, rank)

        return out
