"""
Word-list upload handler — resolve + ladder-exercise guarantee.

Step 3 of wiki/tasklist/word-list-import.plan.md ("Word List Upload -> Ladder
Exposure + Matched Test Queueing"). For each raw word a user submits, this:

  1. Resolves it to a ``dim_word_senses`` row via
     :func:`services.vocabulary.word_resolver.resolve_or_create_sense`
     (Step 2), generating a brand-new sense when none exists.
  2. Guarantees that sense has ladder exercises: if ``exercises`` has no row
     for it yet, runs ``VocabAssetPipeline.generate_for_sense`` then
     ``LadderExerciseRenderer.render_all`` — the exact two-call sequence
     ``scripts/upload_exercises.py::apply_exercises`` and
     ``services/vocabulary_ladder/queue_drain.py::_regenerate`` both use for a
     sense with no prior assets (generate first; only render if generation
     did not fail outright).
  3. Records one ``user_word_watchlist`` row for (user, sense), skipping the
     insert if one already exists for this (user_id, sense_id) pair — see
     the open question in migrations/user_word_watchlist_schema.sql's header;
     this call resolves it as "no DB constraint, check-then-skip in code".

Does NOT run the match sweep (Step 4) or expose an API route (Step 7) — this
module's job ends at watchlist-row-insert + ladder-exercise-guarantee.

One bad word (a resolution failure, an asset-pipeline error) is recorded and
skipped; it never aborts the rest of the batch. The sole exception is
``JudgeUnavailable`` (an exercise-generation judge outage): that re-raises,
matching the fail-closed convention every other ladder batch caller in this
codebase uses (``VocabAssetPipeline.generate_batch``,
``scripts/run_generation_batch.py::run_chunk``) — a systemic judge outage
will fail identically for every remaining word, so surfacing it loudly and
stopping is correct rather than silently degrading every word to an error.
"""

import logging
from typing import Optional
from uuid import uuid4

from services.exercise_generation.judges.base import JudgeUnavailable
from services.vocabulary.word_resolver import resolve_or_create_sense
from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer

logger = logging.getLogger(__name__)

LADDER_STATUS_GENERATED = 'generated'
LADDER_STATUS_ALREADY_EXISTED = 'already_existed'
LADDER_STATUS_ERROR = 'error'

WATCHLIST_STATUS_INSERTED = 'inserted'
WATCHLIST_STATUS_ALREADY_WATCHED = 'already_watched'


def _sense_has_ladder_exercises(db, sense_id: int) -> bool:
    """Whether ``sense_id`` already has at least one row in ``exercises``.

    Same query shape as ``senses_with_exercises`` in
    ``scripts/export_exercise_worklist.py`` (``exercises.word_sense_id``
    membership) — that script's bulk ``.in_(...)`` form, narrowed here to a
    single-sense existence check via ``.limit(1)``.
    """
    resp = (
        db.table('exercises')
        .select('id')
        .eq('word_sense_id', sense_id)
        .limit(1)
        .execute()
    )
    return bool(resp.data)


def _watchlist_row_exists(db, user_id: str, sense_id: int) -> bool:
    """Whether a ``user_word_watchlist`` row already exists for (user, sense).

    No DB uniqueness constraint enforces this (see
    migrations/user_word_watchlist_schema.sql's header — deliberately left
    open for Step 3 to decide) — enforced here as a plain existence check
    before insert, so re-uploading the same word twice does not create a
    duplicate active row.
    """
    resp = (
        db.table('user_word_watchlist')
        .select('id')
        .eq('user_id', user_id)
        .eq('sense_id', sense_id)
        .limit(1)
        .execute()
    )
    return bool(resp.data)


def _ensure_ladder_exercises(
    db, pipeline: VocabAssetPipeline, renderer: LadderExerciseRenderer,
    sense_id: int, language_id: int,
) -> tuple[str, Optional[str]]:
    """Guarantee ``sense_id`` has ladder exercises. Returns (status, error).

    Mirrors the generate-then-render sequence
    ``services/vocabulary_ladder/queue_drain.py::_regenerate`` and
    ``scripts/upload_exercises.py::apply_exercises`` both use: run
    ``generate_for_sense`` first, and only call ``render_all`` when
    generation did not come back ``'failed'`` (a ``'skipped'`` status —
    valid assets already existed — still has exercises worth rendering; a
    ``'success'``/``'partial'`` status means fresh assets are ready to
    render; only ``'failed'`` means there is nothing usable to render from).
    """
    if _sense_has_ladder_exercises(db, sense_id):
        return LADDER_STATUS_ALREADY_EXISTED, None

    try:
        pipeline_result = pipeline.generate_for_sense(sense_id, language_id)
    except JudgeUnavailable:
        raise
    except Exception as exc:
        logger.error("Asset generation failed for sense %s: %s", sense_id, exc)
        return LADDER_STATUS_ERROR, str(exc)

    if pipeline_result.get('status') == 'failed':
        errors = pipeline_result.get('errors') or ['asset generation failed']
        return LADDER_STATUS_ERROR, '; '.join(errors)

    try:
        exercise_ids = renderer.render_all(sense_id, language_id)
    except JudgeUnavailable:
        raise
    except Exception as exc:
        logger.error("Exercise rendering failed for sense %s: %s", sense_id, exc)
        return LADDER_STATUS_ERROR, str(exc)

    if not exercise_ids:
        return LADDER_STATUS_ERROR, 'render_all produced no exercises'

    return LADDER_STATUS_GENERATED, None


def process_word_list_upload(
    user_id: str, words: list[str], language_code: str, db_client, openai_client,
    upload_batch_id: Optional[str] = None,
) -> dict:
    """For each uploaded word: resolve to a sense, ensure ladder exercises
    exist, record a watchlist row.

    Args:
        user_id: The uploading user's ``users.id`` (uuid string).
        words: Raw surface-form words/short phrases as submitted.
        language_code: ISO 639-1 code ('en', 'zh', 'ja') shared by every word
            in this upload.
        db_client: TestDatabaseClient (or duck-typed equivalent exposing
            ``.client`` for direct table access and
            ``.get_language_config_by_code``) — the same object
            ``resolve_or_create_sense`` expects.
        openai_client: Passed through to ``resolve_or_create_sense`` /
            ``SenseGenerator`` for signature compatibility.
        upload_batch_id: Optional pre-generated batch id. Step 7's
            ``POST /api/word-list/submit`` runs this function in a
            background thread (per-word ladder generation is an LLM
            pipeline, too slow to run inline in the request) but must
            return an ``upload_batch_id`` to the caller *before* this
            function has finished — so it generates the id up front and
            threads it through here rather than waiting for this
            function's own return value. Defaults to a fresh ``uuid4()``
            when omitted, preserving the original behavior for every
            existing caller (including this module's own test suite) that
            has no need to know the id ahead of time.

    Returns:
        {
            'upload_batch_id': str,
            'language_code': str,
            'results': [
                {
                    'word': str,
                    'sense_id': int | None,
                    'ladder_status': 'generated' | 'already_existed'
                                     | 'error' | None,
                    'watchlist_status': 'inserted' | 'already_watched' | None,
                    'error': str | None,
                },
                ...
            ],
        }
        One entry per input word, in input order.
    """
    upload_batch_id = upload_batch_id or str(uuid4())
    results: list[dict] = []

    lang_config = db_client.get_language_config_by_code(language_code)
    if not lang_config:
        error_msg = (
            f"Language {language_code!r} not found or inactive in database"
        )
        return {
            'upload_batch_id': upload_batch_id,
            'language_code': language_code,
            'results': [
                {
                    'word': word, 'sense_id': None, 'ladder_status': None,
                    'watchlist_status': None, 'error': error_msg,
                }
                for word in words
            ],
        }
    language_id = lang_config.id

    db = db_client.client
    pipeline = VocabAssetPipeline(db)
    renderer = LadderExerciseRenderer(db)

    for word in words:
        result = {
            'word': word, 'sense_id': None, 'ladder_status': None,
            'watchlist_status': None, 'error': None,
        }

        # Step 1: resolve to a sense. One bad word must not abort the batch.
        try:
            sense_id = resolve_or_create_sense(
                word, language_code, db_client, openai_client,
            )
        except Exception as exc:
            logger.warning("Word resolution failed for %r: %s", word, exc)
            result['error'] = str(exc)
            results.append(result)
            continue
        result['sense_id'] = sense_id

        # Step 2: guarantee ladder exercises exist for this sense.
        ladder_status, ladder_error = _ensure_ladder_exercises(
            db, pipeline, renderer, sense_id, language_id,
        )
        result['ladder_status'] = ladder_status
        if ladder_error:
            result['error'] = ladder_error

        # Step 3: watchlist row, de-duplicated on (user_id, sense_id).
        try:
            if _watchlist_row_exists(db, user_id, sense_id):
                result['watchlist_status'] = WATCHLIST_STATUS_ALREADY_WATCHED
            else:
                db.table('user_word_watchlist').insert({
                    'user_id': user_id,
                    'sense_id': sense_id,
                    'language_id': language_id,
                    'upload_batch_id': upload_batch_id,
                    'ladder_exercises_generated': ladder_status in (
                        LADDER_STATUS_GENERATED, LADDER_STATUS_ALREADY_EXISTED,
                    ),
                }).execute()
                result['watchlist_status'] = WATCHLIST_STATUS_INSERTED
        except Exception as exc:
            logger.error(
                "Watchlist insert failed for user %s sense %s: %s",
                user_id, sense_id, exc,
            )
            watchlist_error = f'watchlist insert failed: {exc}'
            result['error'] = (
                f"{result['error']}; {watchlist_error}"
                if result['error'] else watchlist_error
            )

        results.append(result)

    return {
        'upload_batch_id': upload_batch_id,
        'language_code': language_code,
        'results': results,
    }
