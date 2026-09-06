"""
Shared word -> dim_vocabulary / dim_word_senses resolver.

Two entry points:

- ``get_or_create_vocab_id(...)`` — the get-or-create ``dim_vocabulary`` logic,
  extracted from ``TestGenerationOrchestrator._get_or_create_vocab_id``
  (services/test_generation/orchestrator.py) so there is exactly ONE copy of
  the look-before-insert + 23505 unique-violation race handling documented
  there. ``TestGenerationOrchestrator._get_or_create_vocab_id`` now delegates
  to this function (passing its own instance cache/lock), so behavior for
  that existing caller is unchanged.

- ``resolve_or_create_sense(...)`` — the request-safe "resolve existing sense
  or create a new one" path for a single raw word with no surrounding
  transcript (e.g. a user-submitted word-list upload — see
  wiki/tasklist/word-list-import.plan.md Step 2). It tokenizes the word with
  the appropriate per-language processor, gets/creates its ``dim_vocabulary``
  row via the function above, then reuses an existing standard-level sense
  (no LLM call) or generates exactly one new sense.

Why ``generate_sense`` and not ``seed_word`` for the sense step:
``SenseGenerator.generate_sense`` is the *inline, per-occurrence* entry point
— "reuse an existing sense when one exists (or short-circuit with zero LLM
calls when ``prefer_existing=True``), otherwise generate a brand-new
two-level sense". That is exactly "resolve or create" for a single word.
``SenseGenerator.seed_word`` is the *batch backfill* entry point — it always
writes when the word is missing the `simple` definition level, even when a
`standard` sense already exists (idempotent upsert-refresh semantics for a
one-off corpus-wide backfill run). Using ``seed_word`` here would silently
regenerate/overwrite sense text for words that already have a perfectly good
sense, which is not "resolve or create".
"""

import threading
from typing import Optional

from postgrest.exceptions import APIError

from services.vocabulary.frequency_service import compute_zipf_for_vocab_item
from services.vocabulary.pipeline import VocabularyExtractionPipeline
from services.vocabulary.processors.base import LemmaToken
from services.vocabulary.sense_generator import SenseGenerator, retry_transient_db_call


@retry_transient_db_call
def get_or_create_vocab_id(
    db,
    item: dict,
    language_id: int,
    language_code: str,
    cache: Optional[dict] = None,
    cache_lock: Optional[threading.Lock] = None,
) -> int:
    """
    Get existing vocab ID or create new entry in dim_vocabulary.

    Extracted from TestGenerationOrchestrator._get_or_create_vocab_id — see
    that method's TASK-737 comment for why the whole DB round trip below is
    serialized under one lock, and the inline comment below for why a bare
    insert is preceded by a select.

    Args:
        db: Supabase admin client.
        item: Dict from extract_detailed() (or an equivalent single-word
            dict — see resolve_or_create_sense) with lemma, pos,
            phrase_type, components, reading.
        language_id: Integer language ID.
        language_code: ISO 639-1 code, used for zipf frequency lookup.
        cache: Optional (lemma, language_id) -> vocab_id memo, shared across
            calls by callers that want cross-call memoization.
            TestGenerationOrchestrator passes its instance-level
            ``_vocab_cache`` here so repeated lemmas across one run's worker
            pool short-circuit without a DB round trip. Callers resolving a
            single word (resolve_or_create_sense) can omit this — a
            throwaway dict scoped to this one call is used instead.
        cache_lock: Lock guarding `cache` and the DB round trip below. A
            fresh Lock is created when omitted.

    Returns:
        Integer vocab ID
    """
    if cache is None:
        cache = {}
    if cache_lock is None:
        cache_lock = threading.Lock()

    lemma = item['lemma']
    cache_key = (lemma, language_id)

    # Whole lookup+insert under one lock (TASK-737): a caller fanning this
    # out across a thread pool (TestGenerationOrchestrator does, one thread
    # per extracted vocab word) can otherwise race two cache misses on the
    # same brand-new lemma into two inserts. Serializing turns that into a
    # queue instead of relying solely on the cross-process 23505 handler
    # below.
    with cache_lock:
        if cache_key in cache:
            return cache[cache_key]

        row = {
            'lemma': lemma,
            'language_id': language_id,
            'part_of_speech': item.get('pos'),
        }

        if item.get('phrase_type'):
            row['phrase_type'] = item['phrase_type']
        if item.get('components'):
            row['component_lemmas'] = item['components']
        if item.get('reading'):
            # Populated for Japanese only (see extract_detailed /
            # LemmaToken.reading) — the homophone-family lookup key in
            # _resolve_kana_homophones. Stored at creation time so new
            # rows don't depend on the backfill script ever running.
            row['reading'] = item['reading']

        zipf = compute_zipf_for_vocab_item(item, language_code)
        if zipf is not None:
            row['frequency_rank'] = zipf

        # dim_vocabulary is shared across every run, so after a few hundred
        # tests most lemmas already exist. Look before inserting: a bare
        # insert raises APIError 23505 on uq_vocab_lemma, and a caller
        # looping over many items with no per-item guard would have that one
        # exception abort every remaining item at the first already-known
        # word.
        existing = db.table('dim_vocabulary') \
            .select('id') \
            .eq('lemma', lemma) \
            .eq('language_id', language_id) \
            .limit(1) \
            .execute()

        if existing.data:
            vocab_id = existing.data[0]['id']
        else:
            try:
                response = db.table('dim_vocabulary') \
                    .insert(row) \
                    .execute()
                vocab_id = response.data[0]['id']
            except APIError as exc:
                # Lost the insert race to a concurrent worker (another
                # process, or another caller) between the select above and
                # this insert — re-read rather than fail.
                if getattr(exc, 'code', None) != '23505':
                    raise
                lookup = db.table('dim_vocabulary') \
                    .select('id') \
                    .eq('lemma', lemma) \
                    .eq('language_id', language_id) \
                    .single() \
                    .execute()
                vocab_id = lookup.data['id']

        cache[cache_key] = vocab_id
        return vocab_id


def _tokenize_single_word(
    word: str, language_code: str, pipeline: VocabularyExtractionPipeline,
) -> dict:
    """
    Build an extract_detailed()-shaped item dict for one raw word/phrase.

    Reuses the same per-language processor extract_detailed() relies on
    (see services/vocabulary/processors/), but skips the LLM phrase-detection
    stage: this is one user-submitted word, not a transcript to mine for
    phrases, so there is nothing to detect.

    Args:
        word: Raw surface-form word or short phrase (not pre-lemmatized).
        language_code: ISO 639-1 code.
        pipeline: A VocabularyExtractionPipeline instance (its processor
            cache is reused if the caller keeps it around across calls).

    Returns:
        Dict shaped like one entry of
        VocabularyExtractionPipeline.extract_detailed()'s return value.

    Raises:
        ValueError: the processor produced no tokens at all (e.g. input was
            pure punctuation/whitespace after stripping).
    """
    processor = pipeline.get_processor(language_code)
    tokens: list[LemmaToken] = processor.extract_lemma_tokens(word)
    if not tokens:
        raise ValueError(
            f"Could not tokenize {word!r} for language {language_code!r}"
        )

    if len(tokens) == 1:
        t = tokens[0]
        return {
            'lemma': t.lemma,
            'pos': t.pos,
            'is_phrase': False,
            'phrase_type': None,
            'components': None,
            'reading': t.reading or '',
        }

    # More than one token came back for a single submitted word/phrase
    # (e.g. a user typed a short multi-word phrase). Treat it as one
    # compound lemma rather than silently keeping only the first token.
    lemma = ' '.join(t.lemma for t in tokens)
    anchor = next((t for t in tokens if t.is_content), tokens[0])
    return {
        'lemma': lemma,
        'pos': anchor.pos,
        'is_phrase': True,
        'phrase_type': None,
        'components': [t.lemma for t in tokens],
        'reading': anchor.reading or '',
    }


def resolve_or_create_sense(
    word: str, language_code: str, db_client, openai_client,
) -> int:
    """
    Return a dim_word_senses.id for `word`, creating dim_vocabulary /
    dim_word_senses rows as needed.

    Request-safe: makes at most one LLM call (only when the word has no
    existing sense yet); reuses the existing standard-level sense with zero
    LLM calls otherwise. See the module docstring for why
    ``SenseGenerator.generate_sense`` (not ``seed_word``) is the method used
    here.

    Args:
        word: Raw word or short phrase, in its surface form (not
            pre-lemmatized) — tokenized here via the per-language processor.
        language_code: ISO 639-1 code ('en', 'zh', 'ja').
        db_client: TestDatabaseClient (or a duck-typed equivalent exposing
            `.client` for direct table access, `.get_language_config_by_code`,
            and `.get_prompt_template`).
        openai_client: OpenAI client instance, passed through to
            VocabularyExtractionPipeline / SenseGenerator for signature
            compatibility (unused by call_llm directly — see
            SenseGenerator.__init__).

    Returns:
        int: dim_word_senses.id (standard level) for `word`.

    Raises:
        ValueError: `word` is empty, the language is not configured in
            dim_languages, or the word could not be tokenized.
        RuntimeError: sense generation failed (both models exhausted, or the
            word was flagged should_skip) for a brand-new word.
    """
    if not word or not word.strip():
        raise ValueError("word must be non-empty")

    word = word.strip()

    lang_config = db_client.get_language_config_by_code(language_code)
    if not lang_config:
        raise ValueError(
            f"Language {language_code!r} not found or inactive in database"
        )

    pipeline = VocabularyExtractionPipeline(
        openai_client=openai_client, db_client=db_client,
    )
    item = _tokenize_single_word(word, language_code, pipeline)

    db = db_client.client
    vocab_id = get_or_create_vocab_id(
        db, item, lang_config.id, language_code,
    )

    sense_gen = SenseGenerator(
        openai_client=openai_client,
        db=db,
        db_client=db_client,
        language_code=language_code,
        language_id=lang_config.id,
        # Reuse an existing sense with zero LLM calls; only generate when
        # this vocab item truly has none yet — see module docstring.
        prefer_existing=True,
    )
    sense_id = sense_gen.generate_sense(
        vocab_id=vocab_id,
        lemma=item['lemma'],
        phrase_type=item.get('phrase_type'),
        sentence='',
        transcript='',
    )
    if sense_id is None:
        raise RuntimeError(
            f"Sense generation failed for {item['lemma']!r} "
            f"(language={language_code!r}, vocab_id={vocab_id})"
        )
    return int(sense_id)
