#!/usr/bin/env python3
"""
Synthesise the missing audio for L1 phonetic and listening items (TASK-531).

L1 is a *listening* exercise — the learner hears the target word and picks the
matching spelling — so an L1 item with no ``audio_url`` is not a degraded item,
it is an unanswerable one. Same for ``listening_flashcard``. The renderer
generates audio inline when a synthesizer is configured, but the batch runs
without one, so a full batch leaves a corpus of silent listening items behind.

This is the sweep that fills them.

Design notes
------------
**Deterministic slugs.** ``{type}_{sense_id}_{language_id}`` — the same slug
the renderer uses for L1. Re-running the backfill therefore overwrites the same
R2 object rather than accumulating orphans, and an interrupted run resumes
without paying twice.

**Failures ship the text variant and queue a retry.** A TTS failure must not
delete the item: the exercise still works as a reading item, and it lands in
``generation_queue`` with the reason so the drain job can retry it. Silence
about a failed synthesis is the thing to avoid (§6.10).

**A per-night cap, because this spends money and Azure quota.** The cap is a
CLI flag with an environment default, and the run stops cleanly when it is
reached rather than dying mid-item.

Usage:
    python scripts/backfill_exercise_audio.py --language ja [options]

Options:
    --language CODE   Required: zh | en | ja (or "all")
    --dry-run         Report what would be synthesised; make no TTS calls
    --cap N           Max syntheses this run (default: $AUDIO_BACKFILL_CAP or 500)
    --types T [T...]  Restrict to specific exercise types
    --report-only     Print the coverage table and exit
"""

import argparse
import logging
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402
from services.exercise_generation.audio_voice import pick_voice  # noqa: E402
from services.vocabulary_ladder import queue_drain  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(message)s',
)
logger = logging.getLogger('backfill_audio')

LANGUAGE_CODES = {'zh': 1, 'en': 2, 'ja': 3}

#: Types whose items are unanswerable without audio.
AUDIO_TYPES = ('phonetic_recognition', 'listening_flashcard')

#: Where each type keeps the text to speak, in preference order. The first
#: non-empty field wins. Kept as data rather than branches so adding a fourth
#: audio-bearing type is a one-line change.
TEXT_FIELDS: dict[str, tuple[str, ...]] = {
    'phonetic_recognition': ('word', 'correct_answer'),
    # 'word_of_interest' and 'back_sentence' are what the renderer actually
    # writes. The four names previously listed here ('audio_text',
    # 'highlight_word', 'word', 'front_sentence') appear in no
    # listening_flashcard row, so every item reported "no speakable text".
    'listening_flashcard': ('word_of_interest', 'front_sentence',
                            'back_sentence'),
}

#: Where each type keeps its audio URL. Per-type because they genuinely differ:
#: a listening flashcard plays its FRONT, and the renderer reads
#: 'front_audio_url'. Treating 'audio_url' as universal made this backfill
#: report 0% coverage over 56 fully-voiced items, and — worse — would have
#: written any newly synthesised URL to a key the renderer never reads, leaving
#: the item silent and permanently "uncovered".
AUDIO_URL_FIELDS: dict[str, str] = {
    'phonetic_recognition': 'audio_url',
    'listening_flashcard': 'front_audio_url',
}

#: Fallback for a type not listed above.
_DEFAULT_AUDIO_FIELD = 'audio_url'

#: Queue reason for an item whose synthesis failed. `generation_queue` is
#: UNIQUE (sense_id, reason), so repeated failures for one sense collapse to
#: one row rather than flooding the queue.
QUEUE_REASON = 'audio_backfill'

DEFAULT_CAP = int(os.environ.get('AUDIO_BACKFILL_CAP', '500'))

#: Coverage target from the task's acceptance criteria.
COVERAGE_TARGET = 0.95

_PAGE = 500


def audio_text(content: dict, exercise_type: str) -> str:
    """The string to speak for one item, or '' when there is nothing to say."""
    for field in TEXT_FIELDS.get(exercise_type, ()):
        value = (content or {}).get(field)
        if isinstance(value, str) and value.strip():
            # Flashcard fronts mark the target with **bold**; the synthesizer
            # would read the asterisks aloud.
            return value.replace('**', '').strip()
    return ''


def audio_url_field(exercise_type: str) -> str:
    """The content key this type keeps its audio URL under."""
    return AUDIO_URL_FIELDS.get(exercise_type, _DEFAULT_AUDIO_FIELD)


def audio_url_of(content: dict, exercise_type: str) -> str:
    """Existing audio URL for an item, or '' when it has none."""
    value = (content or {}).get(audio_url_field(exercise_type))
    return value.strip() if isinstance(value, str) else ''


def slug_for(exercise_type: str, sense_id, language_id: int) -> str:
    """Deterministic R2 object name.

    L1 keeps the renderer's existing ``l1_{sense}_{lang}`` shape so a
    previously-rendered object is reused rather than duplicated.
    """
    if exercise_type == 'phonetic_recognition':
        return f'l1_{sense_id}_{language_id}'
    return f'{exercise_type}_{sense_id}_{language_id}'


class AudioBackfillRun:
    """One pass over a language's audio-bearing items."""

    def __init__(self, db, language_id: int, *, dry_run: bool, cap: int,
                 types: tuple[str, ...], synthesizer=None):
        self.db = db
        self.language_id = language_id
        self.dry_run = dry_run
        self.cap = cap
        self.types = types
        self._synthesizer = synthesizer

        self.stats = defaultdict(int)
        self.failures: list[dict] = []

    # ------------------------------------------------------------------

    @property
    def synthesizer(self):
        """Built lazily so ``--dry-run`` and ``--report-only`` need no Azure key."""
        if self._synthesizer is None:
            from services.test_generation.agents.audio_synthesizer import AudioSynthesizer
            self._synthesizer = AudioSynthesizer()
        return self._synthesizer

    def run(self) -> bool:
        pending = self.fetch_pending()
        if not pending:
            logger.info('language_id=%s: nothing to synthesise', self.language_id)
            self.report_coverage()
            return True

        voice, speed = pick_voice(self.db, self.language_id)
        if voice is None:
            # Not fatal — AudioSynthesizer falls back to its Azure default —
            # but for a non-English language that default is the wrong voice,
            # so say so loudly rather than shipping English-accented Japanese.
            logger.warning(
                'language_id=%s has no tts_voice_ids configured; the synthesizer '
                'default will be used. Populate dim_languages.tts_voice_ids first '
                'if that is not what you want.', self.language_id,
            )

        logger.info(
            'language_id=%s: %d item(s) missing audio, cap %d, voice %s',
            self.language_id, len(pending), self.cap, voice or '(default)',
        )

        for row in pending:
            if self.stats['synthesised'] >= self.cap:
                logger.warning(
                    'cap of %d reached — stopping cleanly with %d item(s) still '
                    'missing audio. Re-run to continue.',
                    self.cap, len(pending) - self.stats['attempted'],
                )
                self.stats['capped'] = len(pending) - self.stats['attempted']
                break
            self._synthesise_one(row, voice, speed)

        self.report()
        self.report_coverage()
        return True

    # ------------------------------------------------------------------

    def fetch_pending(self) -> list[dict]:
        """Active audio-bearing items whose content has no ``audio_url``.

        Filtered in Python rather than in the query: ``audio_url`` lives inside
        a jsonb column and may be absent, null, or an empty string, and
        expressing "any of those three" in PostgREST is less legible than the
        one-line check here.
        """
        out: list[dict] = []
        offset = 0
        while True:
            try:
                rows = (
                    self.db.table('exercises')
                    .select('id, exercise_type, content, word_sense_id')
                    .eq('language_id', self.language_id)
                    .eq('is_active', True)
                    .in_('exercise_type', list(self.types))
                    .range(offset, offset + _PAGE - 1)
                    .execute()
                ).data or []
            except Exception as exc:
                logger.error('could not read exercises: %s', exc)
                return out

            for row in rows:
                if not audio_url_of(row.get('content') or {},
                                    row.get('exercise_type')):
                    out.append(row)
            if len(rows) < _PAGE:
                return out
            offset += _PAGE

    def _synthesise_one(self, row: dict, voice, speed) -> None:
        self.stats['attempted'] += 1
        exercise_type = row.get('exercise_type')
        content = row.get('content') or {}
        text = audio_text(content, exercise_type)

        if not text:
            # Nothing to speak is a content defect, not a TTS failure — record
            # it separately so the two do not blur in the report.
            self.stats['no_text'] += 1
            self.failures.append({
                'exercise_id': row.get('id'),
                'sense_id': row.get('word_sense_id'),
                'reason': f'no speakable text in a {exercise_type} item',
            })
            return

        if self.dry_run:
            self.stats['would_synthesise'] += 1
            return

        slug = slug_for(exercise_type, row.get('word_sense_id'), self.language_id)
        try:
            url = self.synthesizer.generate_and_upload(
                text=text, file_id=slug, voice=voice, speed=speed,
            )
        except Exception as exc:
            self.stats['failed'] += 1
            self.failures.append({
                'exercise_id': row.get('id'),
                'sense_id': row.get('word_sense_id'),
                'reason': f'tts failed: {exc}',
            })
            self._queue_retry(row, str(exc))
            return

        if not url:
            self.stats['failed'] += 1
            self.failures.append({
                'exercise_id': row.get('id'),
                'sense_id': row.get('word_sense_id'),
                'reason': 'tts returned no url',
            })
            self._queue_retry(row, 'tts returned no url')
            return

        # Per-type key: writing 'audio_url' on a listening_flashcard would
        # upload real audio the renderer never looks at.
        content[audio_url_field(exercise_type)] = url
        try:
            self.db.table('exercises').update(
                {'content': content}
            ).eq('id', row['id']).execute()
            self.stats['synthesised'] += 1
        except Exception as exc:
            # The audio exists in R2 but the row does not point at it. Count it
            # as a failure: from a learner's side, the item is still silent.
            self.stats['failed'] += 1
            self.failures.append({
                'exercise_id': row.get('id'),
                'sense_id': row.get('word_sense_id'),
                'reason': f'audio uploaded but row update failed: {exc}',
            })

    def _queue_retry(self, row: dict, reason: str) -> None:
        """Queue the sense so the drain job retries it. Never raises."""
        sense_id = row.get('word_sense_id')
        if not sense_id:
            return
        try:
            queue_drain.enqueue(
                self.db, sense_id, self.language_id, QUEUE_REASON,
                {'exercise_id': row.get('id'), 'reason': reason},
            )
        except Exception as exc:
            logger.warning('could not queue sense %s: %s', sense_id, exc)

    # ------------------------------------------------------------------

    def report(self) -> None:
        logger.info('-' * 64)
        logger.info('language_id=%s', self.language_id)
        for key in ('attempted', 'synthesised', 'would_synthesise',
                    'failed', 'no_text', 'capped'):
            if self.stats[key]:
                logger.info('  %-17s: %d', key, self.stats[key])
        if self.failures:
            logger.info('  first %d failure(s):', min(10, len(self.failures)))
            for item in self.failures[:10]:
                logger.info('    exercise %s (sense %s): %s',
                            item['exercise_id'], item['sense_id'], item['reason'])

    def report_coverage(self) -> None:
        """The acceptance-criteria check: >=95% of items carry an audio_url."""
        totals: dict[str, list[int]] = {t: [0, 0] for t in self.types}
        offset = 0
        while True:
            try:
                rows = (
                    self.db.table('exercises')
                    .select('exercise_type, content')
                    .eq('language_id', self.language_id)
                    .eq('is_active', True)
                    .in_('exercise_type', list(self.types))
                    .range(offset, offset + _PAGE - 1)
                    .execute()
                ).data or []
            except Exception as exc:
                logger.error('coverage query failed: %s', exc)
                return
            for row in rows:
                exercise_type = row.get('exercise_type')
                bucket = totals.setdefault(exercise_type, [0, 0])
                bucket[1] += 1
                if audio_url_of(row.get('content') or {}, exercise_type):
                    bucket[0] += 1
            if len(rows) < _PAGE:
                break
            offset += _PAGE

        logger.info('  coverage (language_id=%s):', self.language_id)
        for exercise_type, (have, total) in sorted(totals.items()):
            if not total:
                continue
            share = have / total
            flag = 'OK ' if share >= COVERAGE_TARGET else '** '
            logger.info('    %s%-22s %d/%d  %.1f%%',
                        flag, exercise_type, have, total, 100 * share)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Synthesise missing audio for L1 and listening items',
    )
    parser.add_argument('--language', required=True,
                        choices=[*LANGUAGE_CODES, 'all'])
    parser.add_argument('--dry-run', action='store_true',
                        help='Report what would be synthesised; make no TTS calls')
    parser.add_argument('--cap', type=int, default=DEFAULT_CAP,
                        help=f'Max syntheses this run (default {DEFAULT_CAP})')
    parser.add_argument('--types', nargs='*', choices=list(AUDIO_TYPES),
                        default=list(AUDIO_TYPES),
                        help='Restrict to specific exercise types')
    parser.add_argument('--report-only', action='store_true',
                        help='Print the coverage table and exit')
    args = parser.parse_args()

    if args.dry_run:
        logger.info('DRY RUN — no TTS calls, no writes')

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    codes = list(LANGUAGE_CODES) if args.language == 'all' else [args.language]
    ok = True
    for code in codes:
        run = AudioBackfillRun(
            db, LANGUAGE_CODES[code],
            dry_run=args.dry_run, cap=args.cap, types=tuple(args.types),
        )
        if args.report_only:
            run.report_coverage()
        else:
            ok = run.run() and ok

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
