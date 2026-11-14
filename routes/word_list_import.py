# routes/word_list_import.py
"""Word-list upload API — Step 7 of wiki/tasklist/word-list-import.plan.md.

``POST /api/word-list/submit``
    Validates the submitted words + language and starts Step 3's upload
    pipeline (``services.word_list_import.upload_handler.
    process_word_list_upload``) in the background, returning an
    ``upload_batch_id`` immediately rather than waiting for it to finish.

``GET /api/word-list/watchlist``
    Returns the authenticated user's ``user_word_watchlist`` rows (ladder
    status, most recent match, active flag, and a resolved ``lemma`` — the
    actual word text, joined in from ``dim_word_senses``/``dim_vocabulary``
    since the watchlist row itself only stores ``sense_id``) — this doubles
    as the pollable status surface for a submission in progress, since
    ``process_word_list_upload`` writes one watchlist row per word as it
    completes that word's processing.

Async-execution pattern
------------------------
Per-word ladder-asset generation is a real three-prompt LLM pipeline —
observed around ~5.5 min/sense end-to-end for a brand-new sense (see the
batch-economics notes referenced from wiki/tasklist/word-list-import.plan.md
Step 3) — so running it inline inside this request handler for more than a
couple of words is not viable.

The nightly ``generation_queue`` drain
(``services/vocabulary_ladder/queue_drain.py``) is not used here: a word
uploaded at any other time of day would wait up to ~24h for its exercises.

Instead a submission is handed to a small fixed worker pool
(``services.word_list_import.batch_limits.WorkerPool``) and the route returns
202 with a pre-generated ``upload_batch_id``. Progress is polled via
``GET /api/word-list/watchlist`` (filterable by the client on
``upload_batch_id``), which ``process_word_list_upload`` writes durably as it
goes.

Admission control (see ``batch_limits``): one in-flight batch per user, a
per-user daily batch cap, a bounded queue, and per-word validation
(``services.word_list_import.validation``). Over-quota requests get a 429.

Auth follows ``routes/test_intros.py``'s convention exactly: the
``@jwt_required`` decorator, ``g.current_user_id`` for the caller's identity,
and the same ``utils.responses`` success/error helpers.
"""

import logging
from uuid import uuid4

from flask import Blueprint, g, request

from middleware.auth import jwt_required
from services.word_list_import.upload_handler import process_word_list_upload
from services.word_list_import import batch_limits
from services.word_list_import.validation import clean_words
from utils.responses import (
    ApiResponse, api_error, api_success, bad_request, server_error,
)

logger = logging.getLogger(__name__)

word_list_import_bp = Blueprint(
    'word_list_import', __name__, url_prefix='/api/word-list',
)

# No other upload-style route in this repo imposes (or needs) a cap on list
# size — routes/vocab_admin.py::upload_words (the closest analog, an
# admin-only word-list uploader) has none, and no shared constant exists to
# mirror. This is therefore a fresh, documented judgment call rather than a
# borrowed convention: per-word ladder generation can cost real wall-clock
# minutes for a brand-new sense (see module docstring), so an unbounded list
# would tie up a single background thread for a very long time. 50 is
# generous for a real vocabulary list while keeping worst-case wall clock
# (every word brand-new) bounded to a small number of hours rather than an
# open-ended run.
MAX_WORDS_PER_SUBMIT = 50

_limiter = batch_limits.BatchLimiter()
_pool = batch_limits.WorkerPool()

_REJECTION_MESSAGES = {
    batch_limits.REJECT_IN_FLIGHT: (
        'A word list is still being processed. Please wait for it to finish '
        'before submitting another.'
    ),
    batch_limits.REJECT_DAILY_CAP: (
        'Daily word-list limit reached. Please try again tomorrow.'
    ),
    batch_limits.REJECT_BUSY: (
        'Word-list processing is busy right now. Please try again later.'
    ),
}


def _too_many(reason: str) -> ApiResponse:
    return api_error(_REJECTION_MESSAGES[reason], 429, 'RATE_LIMITED')

_WATCHLIST_COLUMNS = (
    'id, sense_id, language_id, upload_batch_id, created_at, '
    'ladder_exercises_generated, last_matched_test_id, last_matched_at, '
    'active'
)

# Batch chunk size for the sense_id -> lemma resolution below. Mirrors
# scripts/sense_linking_common.py::lemma_sense_lookup's own chunking constant
# exactly (PostgREST `.in_()` filters have a practical URL-length ceiling well
# under 500 simple integer ids, and that helper's value is the established
# convention for this exact reverse-lookup shape elsewhere in the repo).
_LEMMA_LOOKUP_CHUNK_SIZE = 500


def _resolve_lemmas(db_client, sense_ids: list) -> dict:
    """Batch-resolve ``sense_id -> dim_vocabulary.lemma`` for a list of
    watchlist rows' sense ids, in two round trips total (not one query per
    row) regardless of how many rows the caller has.

    Mirrors ``scripts/sense_linking_common.py::lemma_sense_lookup``'s own
    two-hop batching (``dim_word_senses`` for ``sense_id -> vocab_id``, then
    ``dim_vocabulary`` for ``vocab_id -> lemma``, each chunked at 500 ids per
    ``.in_()`` call) — that helper builds the reverse index (``lemma ->
    sense_id``); this one is a forward lookup (``sense_id -> lemma``) for
    display, so the dict shape differs but the join/chunking logic is the
    same and is reused rather than re-derived.

    Returns an empty dict for an empty/None input. Any ``sense_id`` that
    can't be resolved (deleted sense, orphaned vocab row, etc.) is simply
    absent from the result — callers must treat a missing key as "unknown",
    not raise.
    """
    if not sense_ids:
        return {}

    unique_sense_ids = list({sid for sid in sense_ids if sid is not None})
    if not unique_sense_ids:
        return {}

    sense_to_vocab = {}
    for i in range(0, len(unique_sense_ids), _LEMMA_LOOKUP_CHUNK_SIZE):
        chunk = unique_sense_ids[i:i + _LEMMA_LOOKUP_CHUNK_SIZE]
        resp = (
            db_client.client.table('dim_word_senses')
            .select('id, vocab_id')
            .in_('id', chunk)
            .execute()
        )
        for row in (resp.data or []):
            sense_to_vocab[row['id']] = row['vocab_id']

    vocab_ids = list(set(sense_to_vocab.values()))
    vocab_to_lemma = {}
    for i in range(0, len(vocab_ids), _LEMMA_LOOKUP_CHUNK_SIZE):
        chunk = vocab_ids[i:i + _LEMMA_LOOKUP_CHUNK_SIZE]
        resp = (
            db_client.client.table('dim_vocabulary')
            .select('id, lemma')
            .in_('id', chunk)
            .execute()
        )
        for row in (resp.data or []):
            vocab_to_lemma[row['id']] = row['lemma']

    return {
        sense_id: vocab_to_lemma[vocab_id]
        for sense_id, vocab_id in sense_to_vocab.items()
        if vocab_id in vocab_to_lemma
    }


def _get_db_client():
    """Factory for the ``TestDatabaseClient`` this route needs (language
    lookup, watchlist query) — a thin, monkeypatchable seam so tests never
    need a live Supabase admin client, matching this repo's existing
    lazy-factory test seams (e.g. ``routes.tests.get_test_service``)."""
    from services.test_generation.database_client import TestDatabaseClient
    return TestDatabaseClient()


def _get_openai_client():
    """Factory for the OpenAI/OpenRouter client ``resolve_or_create_sense``
    expects (signature compatibility only — see its docstring). Mirrors
    ``scripts/validate_sense_languages.py::get_openai_client``'s
    OpenRouter-first construction, the existing convention for building this
    client outside of Flask's ``app.py`` service wiring. Returns ``None``
    when no key is configured, exactly as an unconfigured environment would
    for any other LLM-backed script in this repo."""
    from openai import OpenAI
    from config import Config

    if Config.USE_OPENROUTER and Config.OPENROUTER_API_KEY:
        return OpenAI(
            api_key=Config.OPENROUTER_API_KEY,
            base_url='https://openrouter.ai/api/v1',
        )
    if Config.OPENAI_API_KEY:
        return OpenAI(api_key=Config.OPENAI_API_KEY)
    return None


def _run_upload_in_background(user_id, words, language_code, upload_batch_id):
    """Worker-pool job. Builds its own db/openai clients rather than reusing
    any built during request validation — the request's thread may tear down
    before this one finishes, and Supabase client objects are not documented
    as safe to share concurrently across threads."""
    try:
        db_client = _get_db_client()
        openai_client = _get_openai_client()
        process_word_list_upload(
            user_id, words, language_code, db_client, openai_client,
            upload_batch_id=upload_batch_id,
        )
    except Exception:
        logger.exception(
            'Background word-list upload failed for batch %s', upload_batch_id,
        )
    finally:
        _limiter.release(user_id)


@word_list_import_bp.route('/submit', methods=['POST'])
@jwt_required
def submit() -> ApiResponse:
    """Validate words + language, start upload processing in the
    background, return an ``upload_batch_id`` immediately."""
    try:
        body = request.get_json(silent=True) or {}
        words = body.get('words')
        language = body.get('language')

        if not isinstance(words, list) or not words:
            return bad_request('words must be a non-empty list')
        if len(words) > MAX_WORDS_PER_SUBMIT:
            return bad_request(
                f'words must not exceed {MAX_WORDS_PER_SUBMIT} per submission',
            )
        if not language or not isinstance(language, str):
            return bad_request('language is required')

        db_client = _get_db_client()
        if not db_client.get_language_config_by_code(language):
            return bad_request(f'Unsupported language: {language!r}')

        words, problem = clean_words(words, language)
        if problem:
            return bad_request(f'Invalid word list: {problem}')

        user_id = g.current_user_id
        rejection = _limiter.reserve(
            user_id,
            known_batches_today=batch_limits.count_recent_batches(
                db_client.client, user_id,
            ),
        )
        if rejection:
            return _too_many(rejection)

        upload_batch_id = str(uuid4())
        queued = _pool.submit(
            lambda: _run_upload_in_background(
                user_id, words, language, upload_batch_id,
            )
        )
        if not queued:
            _limiter.release(user_id, refund=True)
            return _too_many(batch_limits.REJECT_BUSY)

        return api_success({'upload_batch_id': upload_batch_id}, status_code=202)
    except Exception:
        logger.exception('word-list submit failed')
        return server_error()


@word_list_import_bp.route('/watchlist', methods=['GET'])
@jwt_required
def watchlist() -> ApiResponse:
    """Return the authenticated user's `user_word_watchlist` rows, each
    annotated with a `lemma` field (the actual word text the user uploaded,
    e.g. "拖延") resolved via `sense_id -> dim_word_senses.vocab_id ->
    dim_vocabulary.lemma`. Without this the frontend has nothing but an
    internal `sense_id` to show the user, defeating the point of a watchlist
    they're meant to recognize their own words on.

    `lemma` (not e.g. `word`) was chosen to match the column name it's
    actually sourced from (`dim_vocabulary.lemma`) — consistent with this
    row already surfacing raw-ish internal names like `sense_id` and
    `language_id` rather than pre-humanized ones.
    """
    try:
        db_client = _get_db_client()
        resp = (
            db_client.client.table('user_word_watchlist')
            .select(_WATCHLIST_COLUMNS)
            .eq('user_id', g.current_user_id)
            .execute()
        )
        rows = resp.data or []

        lemma_by_sense_id = _resolve_lemmas(
            db_client, [row.get('sense_id') for row in rows],
        )
        for row in rows:
            row['lemma'] = lemma_by_sense_id.get(row.get('sense_id'))

        return api_success({'watchlist': rows})
    except Exception:
        logger.exception('word-list watchlist fetch failed')
        return server_error()
