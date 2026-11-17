#!/usr/bin/env python3
"""
Backfill Traditional-script mirrors for ZH content (TASK-509).

Two targets, both idempotent and both routed through ScriptConverter (OpenCC
s2twp + the script_conversion_overrides table):

  lemmas    — fill dim_vocabulary.lemma_traditional for every ZH lemma.
  exercises — set content['hant'] on every existing ZH exercise (~2,393 rows),
              a deep Traditional mirror of all learner-visible TL strings.

Idempotency / override-correction: each row's Traditional form is recomputed and
written ONLY when it differs from what is stored. So a plain re-run is a no-op,
but correcting an override row and re-running updates exactly the affected
mirrors (and only the `hant` key — the Simplified content is never touched).

Exercise content goes through the content store (ADR-049, TASK-1014). Rows are
read with `store.select_columns(...)` and their content filled by
`store.hydrate(...)`, one call per at most 100 senses, so the same code works
whether content is served from `exercises.content` or from the Storage files.
Changes are written once per sense with `store.write_sense(update_contents=...)`:
in `EXERCISE_CONTENT_WRITE=dual` mode each touched sense gets one new content
version, not one per row. A failed sense write counts every row it carried as
failed and the run goes on. Rows with no `word_sense_id` (the 10 zh collocation
rows; never served, cannot be keyed by sense) are skipped and counted as
`skipped_no_sense`; a row whose content the store cannot supply is counted as
`unavailable`.

Failures are logged and counted; they never abort the run.

Usage:
    python scripts/backfill_hant_mirrors.py --target all   [--dry-run] [--limit N] [--force]
    python scripts/backfill_hant_mirrors.py --target lemmas
    python scripts/backfill_hant_mirrors.py --target exercises --limit 20
"""

import argparse
import logging

try:
    from _common import admin_db, bootstrap, paginate
except ImportError:  # run or imported as scripts.<name>
    from scripts._common import admin_db, bootstrap, paginate

bootstrap()


from services.exercise_content import store  # noqa: E402
from services.vocabulary_ladder.script_converter import ScriptConverter  # noqa: E402

logger = logging.getLogger(__name__)

for _noisy in ('httpx', 'httpcore', 'hpack'):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

ZH = 1
PAGE_SIZE = 1000

#: Exercise columns read for the mirror pass; `{content}` is filled per read mode
#: by `store.select_columns` (ADR-049 §9).
EXERCISE_COLUMNS = 'id, exercise_type, word_sense_id, language_id, {content}'

#: Most senses one `store.hydrate` call may cover (one content file per sense).
HYDRATE_MAX_SENSES = 100
# An offline bulk run, not a request: no 3 s deadline and no 160-sense cap (ADR-049 §5
# request limits). A chunk is fetched in full; only a real miss leaves a row out.
HYDRATE_DEADLINE_S = 300.0


def backfill_lemmas(db, conv: ScriptConverter, dry_run: bool, limit: int, force: bool) -> dict:
    stats = {'updated': 0, 'skipped': 0, 'failed': 0}
    rows: list[dict] = []
    rows.extend(paginate(lambda: db.table('dim_vocabulary')
            .select('id, lemma, lemma_traditional')
            .eq('language_id', ZH)
            .order('id'), PAGE_SIZE))
    if limit:
        rows = rows[:limit]

    logger.info("lemmas: %d ZH lemma(s) loaded", len(rows))
    for r in rows:
        lemma = (r.get('lemma') or '').strip()
        if not lemma:
            stats['skipped'] += 1
            continue
        try:
            trad = conv.convert(lemma)
        except Exception as e:
            logger.warning("convert failed for lemma %r (id=%s): %s", lemma, r['id'], e)
            stats['failed'] += 1
            continue
        current = r.get('lemma_traditional')
        if not force and current == trad:
            stats['skipped'] += 1
            continue
        if dry_run:
            stats['updated'] += 1
            continue
        try:
            db.table('dim_vocabulary').update(
                {'lemma_traditional': trad}).eq('id', r['id']).execute()
            stats['updated'] += 1
        except Exception as e:
            logger.warning("update failed for lemma id=%s: %s", r['id'], e)
            stats['failed'] += 1
    logger.info("lemmas DONE. updated=%d skipped=%d failed=%d",
                stats['updated'], stats['skipped'], stats['failed'])
    return stats


def _load_exercise_rows(db, limit: int) -> list[dict]:
    """Every ZH exercise row, paged by id exactly as before (content per read mode)."""
    columns = store.select_columns(EXERCISE_COLUMNS)
    rows: list[dict] = list(paginate(lambda: db.table('exercises')
            .select(columns)
            .eq('language_id', ZH)
            .order('id'), PAGE_SIZE))
    if limit:
        rows = rows[:limit]
    return rows


def _hydrated_sense_chunks(db, by_sense: dict[int, list[dict]],
                           max_senses: int = HYDRATE_MAX_SENSES):
    """Yield ``({sense_id: rows}, unavailable)`` per chunk of at most ``max_senses`` senses,
    after one ``store.hydrate`` call over the chunk's rows.

    Hydrating by sense rather than by DB page fetches each sense's content file
    once: rows are paged by id, so one sense's rows are spread over many pages.
    Rows the store cannot supply are dropped by ``hydrate`` and counted.
    """
    sense_ids = list(by_sense)
    for start in range(0, len(sense_ids), max_senses):
        chunk_ids = sense_ids[start:start + max_senses]
        chunk = [row for sid in chunk_ids for row in by_sense[sid]]
        before = len(chunk)
        store.hydrate(chunk, db=db, max_senses=len(chunk), deadline_s=HYDRATE_DEADLINE_S)
        kept: dict[int, list[dict]] = {}
        for row in chunk:
            kept.setdefault(row['word_sense_id'], []).append(row)
        yield kept, before - len(chunk)


def _write_sense_mirrors(db, sense_id: int, updates: dict[str, dict], stats: dict,
                         expected_version: int | None = None) -> None:
    """One content write for the sense; a failure counts every row it carried.

    ``expected_version`` is the version the edited content was read at: a sense written by
    someone else meanwhile is refused (counted as ``conflicts``) instead of overwritten with
    the stale base. A re-run picks it up (rows whose mirror already matches are skipped).
    """
    try:
        store.write_sense(db, sense_id, ZH, update_contents=updates,
                          expected_version=expected_version)
        stats['updated'] += len(updates)
    except store.ContentWriteConflict as e:
        logger.warning("sense %s changed while its mirrors were built; %d exercise(s) not "
                       "written, re-run to apply: %s", sense_id, len(updates), e)
        stats['conflicts'] += len(updates)
    except Exception as e:
        logger.warning("content write failed for sense %s (%d exercise(s)): %s",
                       sense_id, len(updates), e)
        stats['failed'] += len(updates)


def backfill_exercises(db, conv: ScriptConverter, dry_run: bool, limit: int, force: bool) -> dict:
    stats = {'updated': 0, 'skipped': 0, 'failed': 0, 'skipped_no_sense': 0, 'unavailable': 0,
             'conflicts': 0}
    rows = _load_exercise_rows(db, limit)

    by_sense: dict[int, list[dict]] = {}
    for r in rows:
        sense_id = r.get('word_sense_id')
        if not sense_id:
            stats['skipped_no_sense'] += 1
            continue
        by_sense.setdefault(sense_id, []).append(r)

    logger.info("exercises: %d ZH exercise(s) loaded over %d sense(s); %d without a sense skipped",
                len(rows), len(by_sense), stats['skipped_no_sense'])
    for chunk, unavailable in _hydrated_sense_chunks(db, by_sense):
        if unavailable:
            logger.warning("exercises: content unavailable for %d row(s) in this chunk",
                           unavailable)
            stats['unavailable'] += unavailable
        for sense_id, sense_rows in chunk.items():
            updates: dict[str, dict] = {}
            for r in sense_rows:
                content = r.get('content')
                if not isinstance(content, dict):
                    stats['skipped'] += 1
                    continue
                # Mirror everything EXCEPT a pre-existing hant key (avoid nesting it).
                base = {k: v for k, v in content.items() if k != 'hant'}
                try:
                    mirror = conv.convert_content(base)
                except Exception as e:
                    logger.warning("convert failed for exercise %s: %s", r['id'], e)
                    stats['failed'] += 1
                    continue
                if not force and content.get('hant') == mirror:
                    stats['skipped'] += 1
                    continue
                if dry_run:
                    stats['updated'] += 1
                    continue
                new_content = dict(content)
                new_content['hant'] = mirror
                updates[r['id']] = new_content
            if updates:
                _write_sense_mirrors(db, sense_id, updates, stats,
                                     store.base_version(sense_rows))
            for r in sense_rows:   # done with this sense: let its content go
                r.pop('content', None)
    logger.info("exercises DONE. updated=%d skipped=%d failed=%d skipped_no_sense=%d "
                "unavailable=%d conflicts=%d", stats['updated'], stats['skipped'],
                stats['failed'], stats['skipped_no_sense'], stats['unavailable'],
                stats['conflicts'])
    return stats


def main():
    parser = argparse.ArgumentParser(description='Backfill ZH Traditional mirrors (TASK-509).')
    parser.add_argument('--target', choices=['lemmas', 'exercises', 'all'], default='all')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--force', action='store_true',
                        help='Rewrite even rows whose mirror already matches.')
    args = parser.parse_args()

    db = admin_db()
    if db is None:
        raise RuntimeError("Service role client unavailable (set SUPABASE_SERVICE_ROLE_KEY).")

    conv = ScriptConverter.from_db(db)

    if args.target in ('lemmas', 'all'):
        backfill_lemmas(db, conv, args.dry_run, args.limit, args.force)
    if args.target in ('exercises', 'all'):
        backfill_exercises(db, conv, args.dry_run, args.limit, args.force)


if __name__ == '__main__':
    main()
