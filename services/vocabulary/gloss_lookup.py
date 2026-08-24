"""
Definition-language preference resolution.

Given senses already fetched in their word's own (native) language, swaps in
a cross-language gloss (services/vocabulary/gloss_generator.py /
scripts/backfill_gloss_definitions.py) when a user's preferred definition
language differs from the word's own -- e.g. a Japanese word served to a
learner whose users.native_language_id is English gets its English gloss
instead of the Japanese definition, when one exists.

This is generation-time content's counterpart at SERVE time: exercise
content baked in by services/vocabulary_ladder/exercise_renderer.py is
shared across every user and stays in the word's own language on purpose
(the L2 immersion definition shown inside an exercise) -- this module only
touches definitions rendered fresh per request, where a specific user's
preference is known (vocab dojo, flashcards, exercise list fallback fill).

Falls back to the native definition silently when no gloss exists yet for
that (word, language) pair -- additive, best-effort substitution, never a
hard requirement.
"""

import logging

logger = logging.getLogger(__name__)

PAGE = 1000


def get_user_definition_language_id(db, user_id: str) -> int | None:
    """The learner's preferred definition language.

    Reuses users.native_language_id (TASK-607/619, dual translation) --
    "what language does this learner read" is the same question dual
    translation already asks, so this deliberately does not add a second
    setting. Returns None (not a default) when unset: unlike dual
    translation's English fallback, an unset preference here must mean "keep
    serving native-language definitions, unchanged" -- silently defaulting
    everyone to English glosses would be a real behavior change, not a
    graceful default.
    """
    try:
        resp = db.table('users').select('native_language_id').eq('id', user_id).single().execute()
        return (resp.data or {}).get('native_language_id')
    except Exception as e:
        logger.warning("Could not resolve definition language for user %s: %s", user_id, e)
        return None


def apply_definition_language_preference(
    db, rows: list[dict], preferred_language_id: int | None,
) -> None:
    """Mutate ``rows`` in place, substituting a gloss definition where one
    exists and is wanted.

    Each row must already carry: ``vocab_id``, ``sense_rank``,
    ``definition_level``, ``definition``, and ``language_id`` (the WORD's own
    language -- i.e. dim_vocabulary.language_id, NOT definition_language_id).

    Every row gets two keys stamped so callers can rely on them unconditionally:
    - ``definition_language_id``: the language the served ``definition`` is
      actually in (== preferred_language_id on a substitution, else the
      word's own language).
    - ``definition_is_gloss``: True only when a substitution happened.

    No-op substitution-wise (but still stamps the two keys) when
    ``preferred_language_id`` is None or already matches a row's own language.
    """
    for r in rows:
        r['definition_is_gloss'] = False
        r['definition_language_id'] = r.get('language_id')

    if not preferred_language_id:
        return

    needed = [r for r in rows if r.get('language_id') != preferred_language_id]
    vocab_ids = sorted({r['vocab_id'] for r in needed if r.get('vocab_id') is not None})
    if not vocab_ids:
        return

    glosses: dict[tuple[int, int, str], str] = {}
    offset = 0
    while True:
        page = (
            db.table('dim_word_senses')
            .select('vocab_id, sense_rank, definition_level, definition')
            .eq('definition_language_id', preferred_language_id)
            .eq('source', 'llm_gloss')
            .in_('vocab_id', vocab_ids)
            .range(offset, offset + PAGE - 1)
            .execute()
        ).data or []
        for g in page:
            glosses[(g['vocab_id'], g['sense_rank'], g['definition_level'])] = g['definition']
        if len(page) < PAGE:
            break
        offset += PAGE

    for r in needed:
        key = (r.get('vocab_id'), r.get('sense_rank'), r.get('definition_level'))
        gloss = glosses.get(key)
        if gloss:
            r['definition'] = gloss
            r['definition_language_id'] = preferred_language_id
            r['definition_is_gloss'] = True
