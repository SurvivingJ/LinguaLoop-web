#!/usr/bin/env python3
"""Dual Translation — one-off backfill: realign stale ``dt_error_instance`` spans.

Why this exists
---------------
``_reconcile_span_form`` (TASK-624/634, ``services/dual_translation/grader_cascade.py``)
repairs a model-reported ``(span, form)`` pair before persistence: a span that does
not actually cover its form is relocated to where the form really sits, and a pair
that cannot be located at all is dropped. It landed on **2026-07-19**.

Every ``dt_error_instance`` row written *before* that date went through the
un-reconciled decoder, so its ``span_reference``/``span_reproduction`` can point at
text that has nothing to do with its ``corrected_form``/``learner_form``. Those rows
are the input to synthesis, profile entries and cards — a drifted span produces a
cloze card whose prompt blanks one clause while asking for a different one, i.e. a
prompt containing its own answer.

This script re-runs the *current* reconciler over persisted rows and rewrites the
spans (and, where a normalization-folded match changes it, the form) in place. It
fixes the data at the source rather than leaning on the card-level guard in
``services/dual_translation/cards.py`` (``_blank_span_for`` / the drop-if-leaking
check), which remains as defence-in-depth.

Idempotent: a row already consistent with the reconciler is left untouched, so a
second run reports 0 repairs.

Usage:
    python scripts/dt_backfill_error_spans.py             # dry run (default)
    python scripts/dt_backfill_error_spans.py --apply
    python scripts/dt_backfill_error_spans.py --ids 3,5,9 --apply
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.dual_translation.grader_cascade import _reconcile_span_form

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('dt_backfill_error_spans')

_CHUNK = 500

# Row outcomes.
OK = 'ok'                      # span already covers its form — nothing to do
REPAIRED = 'repaired'          # span (and possibly form) realigned
UNREPAIRABLE = 'unrepairable'  # form absent from its text even folded — the
                               # reconciler would have dropped this error entirely
NO_TEXT = 'no_text'            # submission/passage no longer resolvable


def _get_db():
    """Initialise the factory before asking for the admin client.

    ``get_supabase_admin()`` raises ``SupabaseFactory not initialized`` when called
    from a bare CLI process (only the Flask app's ``_initialize_services`` does it
    for you) — the same trap that had never let ``dt_nightly_synthesis`` run from
    the command line.
    """
    SupabaseFactory.initialize()
    return get_supabase_admin()


def _chunks(seq, size=_CHUNK):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def _load_rows(db, ids=None):
    """All ``dt_error_instance`` rows joined to the texts their spans index into.

    Explicit id-set lookups rather than embedded selects, matching the convention
    in ``scripts/dt_nightly_synthesis.py`` (no dependence on PostgREST FK
    auto-detection).
    """
    q = db.table('dt_error_instance').select(
        'id, submission_id, span_reference, span_reproduction, '
        'corrected_form, learner_form, subtype, created_at'
    )
    if ids:
        q = q.in_('id', ids)
    errors = q.order('id').execute().data or []
    if not errors:
        return []

    submission_ids = sorted({e['submission_id'] for e in errors})
    subs = {}
    for chunk in _chunks(submission_ids):
        rows = (
            db.table('dt_submission')
            .select('id, passage_id, reproduction')
            .in_('id', chunk)
            .execute()
            .data
            or []
        )
        subs.update({r['id']: r for r in rows})

    passage_ids = sorted({s['passage_id'] for s in subs.values()})
    passages = {}
    for chunk in _chunks(passage_ids):
        rows = (
            db.table('dt_passage')
            .select('id, l2_text, l2_language_id')
            .in_('id', chunk)
            .execute()
            .data
            or []
        )
        passages.update({r['id']: r for r in rows})

    lang_ids = sorted({p['l2_language_id'] for p in passages.values()})
    langs = {}
    for chunk in _chunks(lang_ids):
        rows = (
            db.table('dim_languages')
            .select('id, language_code')
            .in_('id', chunk)
            .execute()
            .data
            or []
        )
        langs.update({r['id']: r['language_code'] for r in rows})

    for e in errors:
        sub = subs.get(e['submission_id'])
        passage = passages.get(sub['passage_id']) if sub else None
        e['_reproduction'] = (sub or {}).get('reproduction')
        e['_reference'] = (passage or {}).get('l2_text')
        e['_l2_code'] = langs.get((passage or {}).get('l2_language_id'), '')
    return errors


def _plan_row(row):
    """``(outcome, patch, notes)`` for one row. ``patch`` is the dict of columns to
    write (empty when nothing changes); ``notes`` are human-readable one-liners."""
    reference = row.get('_reference')
    reproduction = row.get('_reproduction')
    if reference is None or reproduction is None:
        return NO_TEXT, {}, ['submission or passage no longer resolvable']

    l2_code = row.get('_l2_code') or ''
    patch, notes = {}, []
    unrepairable = False

    pairs = (
        ('reference', reference, 'span_reference', 'corrected_form'),
        ('reproduction', reproduction, 'span_reproduction', 'learner_form'),
    )
    for label, text, span_col, form_col in pairs:
        old_span = row.get(span_col)
        old_form = row.get(form_col) or ''
        new_span, new_form = _reconcile_span_form(text, old_span, old_form, l2_code)

        if new_span is None:
            unrepairable = True
            notes.append(f'{label}: {form_col}={old_form!a} not locatable in text')
            continue
        if list(new_span) != list(old_span or []):
            patch[span_col] = list(new_span)
            notes.append(f'{label}: {span_col} {old_span} -> {list(new_span)}')
        if new_form != old_form:
            patch[form_col] = new_form
            notes.append(f'{label}: {form_col} {old_form!a} -> {new_form!a}')

    if unrepairable:
        # Never half-write a row the reconciler would have refused outright.
        return UNREPAIRABLE, {}, notes
    return (REPAIRED if patch else OK), patch, notes


def run(db, ids=None, apply=False):
    rows = _load_rows(db, ids=ids)
    if not rows:
        logger.info('No dt_error_instance rows matched.')
        return {}

    tally = {OK: 0, REPAIRED: 0, UNREPAIRABLE: 0, NO_TEXT: 0}
    for row in rows:
        outcome, patch, notes = _plan_row(row)
        tally[outcome] += 1
        if outcome == OK:
            continue
        logger.info('error id=%s subtype=%s -> %s', row['id'], row['subtype'], outcome.upper())
        for note in notes:
            logger.info('    %s', note)
        if apply and patch:
            db.table('dt_error_instance').update(patch).eq('id', row['id']).execute()
            logger.info('    written')

    logger.info(
        '%s: %d rows | ok=%d repaired=%d unrepairable=%d no_text=%d',
        'APPLIED' if apply else 'DRY RUN',
        len(rows), tally[OK], tally[REPAIRED], tally[UNREPAIRABLE], tally[NO_TEXT],
    )
    if tally[UNREPAIRABLE]:
        logger.warning(
            'FLAGGED: %d row(s) hold a form that does not occur in their own text. The '
            'current grader would have dropped these outright; they are left untouched '
            'for a human call (delete, or re-grade the submission).',
            tally[UNREPAIRABLE],
        )
    return tally


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--apply', action='store_true', help='write the repairs (default: dry run)')
    parser.add_argument('--ids', help='comma-separated dt_error_instance ids (default: all rows)')
    args = parser.parse_args()

    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    ids = [int(x) for x in args.ids.split(',')] if args.ids else None
    run(_get_db(), ids=ids, apply=args.apply)


if __name__ == '__main__':
    main()
