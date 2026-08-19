#!/usr/bin/env python3
"""
Grade every generated sense's ``primary_collocate`` against a frequency source
and report how much of the collocation corpus rests on evidence (TASK-523).

Finding G6: P1 asserts a collocate for every sense and never declines. L5
(collocation gap-fill) and L8 (collocation repair) are both built on that
assertion, and nothing checked it — *advertising* shipped as the primary
collocate of **personalize**, producing an L5 item with four near-synonyms and
no correct answer.

This script is the sweep for senses generated before the pipeline started
tagging inline (``asset_pipeline`` calls ``ground_core_asset`` now). It:

  1. reads every valid ``prompt1_core`` asset for the language,
  2. grades its collocate via ``CollocationGrounder``,
  3. re-prompts ONCE for the unattested ones (with ``--repair``), asking P1 for
     a collocate it can actually justify,
  4. writes the tag back onto the asset,
  5. prints the validated share per language.

Re-prompting is capped at one attempt per sense on purpose. A second ask
produces another unverifiable guess at another model call's cost; the honest
outcome for a sense with no attested collocate is the ``llm_asserted`` tag,
which the report surfaces and an operator can act on.

Usage:
    python scripts/validate_collocates.py --language en [options]

Options:
    --language CODE   Required: zh | en | ja (or "all")
    --dry-run         Report only; write no tags and make no LLM calls
    --repair          Re-prompt P1 once per unattested collocate
    --limit N         Stop after N senses per language (0 = all)
    --only-untagged   Skip senses that already carry a grounding tag
"""

import argparse
import logging
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402
from services.vocabulary_ladder.collocation_grounding import (  # noqa: E402
    GROUNDING_ASSERTED, GROUNDING_CORPUS, GROUNDING_NO_SOURCE,
    CollocationGrounder,
)
from services.vocabulary_ladder.config import get_sentence_target  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(message)s',
)
logger = logging.getLogger('validate_collocates')

LANGUAGE_CODES = {'zh': 1, 'en': 2, 'ja': 3}

# How many flagged mismatches to print in full, for the spot-check the task
# asks for. Beyond this the report stays a summary.
SPOT_CHECK_SAMPLE = 20


class CollocateValidationRun:
    """One pass over a language's generated senses."""

    def __init__(self, db, language_id: int, *, dry_run: bool,
                 repair: bool, limit: int, only_untagged: bool):
        self.db = db
        self.language_id = language_id
        self.dry_run = dry_run
        self.repair = repair and not dry_run
        self.limit = limit
        self.only_untagged = only_untagged
        self.grounder = CollocationGrounder(db)

        self.counts: Counter = Counter()
        self.flagged: list[dict] = []
        self.repaired: list[dict] = []

    # ------------------------------------------------------------------

    def run(self) -> bool:
        assets = self._load_assets()
        if not assets:
            logger.warning('No valid prompt1_core assets for language_id=%s',
                           self.language_id)
            return True

        logger.info('Grading %d sense(s) for language_id=%s',
                    len(assets), self.language_id)

        for row in assets:
            try:
                self._grade_one(row)
            except Exception as exc:
                logger.error('sense %s failed: %s', row.get('sense_id'), exc)
                self.counts['error'] += 1

        self._report()
        return True

    # ------------------------------------------------------------------

    def _load_assets(self) -> list[dict]:
        query = (
            self.db.table('word_assets')
            .select('id, sense_id, content')
            .eq('asset_type', 'prompt1_core')
            .eq('language_id', self.language_id)
            .eq('is_valid', True)
            .order('sense_id')
        )
        if self.limit:
            query = query.limit(self.limit)
        try:
            return (query.execute().data or [])
        except Exception as exc:
            logger.error('Could not load assets: %s', exc)
            return []

    def _grade_one(self, row: dict) -> None:
        content = row.get('content') or {}
        if self.only_untagged and content.get('collocate_grounding'):
            self.counts['skipped_tagged'] += 1
            return

        sentences = content.get('sentences') or []
        lemma = get_sentence_target(sentences[0]) if sentences else ''
        collocate = (content.get('primary_collocate') or '').strip()

        grounding = self.grounder.validate(lemma, collocate, self.language_id)
        self.counts[grounding.status] += 1

        if grounding.status == GROUNDING_ASSERTED:
            record = {
                'sense_id': row.get('sense_id'),
                'lemma': lemma,
                'collocate': collocate,
                'reason': grounding.reason,
            }
            self.flagged.append(record)
            if self.repair:
                grounding = self._reprompt_once(row, content, lemma, record) or grounding

        content['collocate_grounding'] = grounding.to_tag()
        if not self.dry_run:
            self._write_tag(row['id'], content)

    def _reprompt_once(self, row, content, lemma, record):
        """Ask P1 for a collocate it can justify. One attempt, then give up.

        Returns the new Grounding when the replacement validates, else None so
        the caller keeps the original ``llm_asserted`` verdict — a repair that
        produces a second unattested guess must not be recorded as a success.
        """
        from services.vocabulary_ladder.asset_generators.prompt1_core import (
            CoreAssetGenerator,
        )

        generator = CoreAssetGenerator(self.db, self.language_id)
        # Prime the template config the repair path reads.
        try:
            _ = generator.model
        except Exception as exc:
            logger.warning('P1 template unavailable, skipping repair: %s', exc)
            return None

        errors = [
            f"primary_collocate {record['collocate']!r} is not attested as a "
            f"collocation of {lemma!r} in any frequency source. Replace it with a "
            f"genuinely fixed partner of this sense, or set it to null if the "
            f"sense has no fixed collocate. Change no other field."
        ]
        repaired = generator.repair(content, errors, row.get('sense_id'))
        if not repaired:
            return None

        new_collocate = (repaired.get('primary_collocate') or '').strip()
        if not new_collocate or new_collocate == record['collocate']:
            return None

        grounding = self.grounder.validate(lemma, new_collocate, self.language_id)
        if not grounding.validated:
            logger.info(
                'sense %s: repair proposed %r, still unattested — keeping the flag',
                row.get('sense_id'), new_collocate,
            )
            return None

        content['primary_collocate'] = new_collocate
        record['repaired_to'] = new_collocate
        self.repaired.append(record)
        self.counts[GROUNDING_ASSERTED] -= 1
        self.counts[GROUNDING_CORPUS] += 1
        return grounding

    def _write_tag(self, asset_id, content: dict) -> None:
        try:
            self.db.table('word_assets').update(
                {'content': content}
            ).eq('id', asset_id).execute()
        except Exception as exc:
            logger.error('Could not write tag for asset %s: %s', asset_id, exc)

    # ------------------------------------------------------------------

    def _report(self) -> None:
        validated = self.counts[GROUNDING_CORPUS]
        asserted = self.counts[GROUNDING_ASSERTED]
        no_source = self.counts[GROUNDING_NO_SOURCE]
        checked = validated + asserted

        logger.info('=' * 64)
        logger.info('language_id=%s', self.language_id)
        logger.info('  corpus_validated : %d', validated)
        logger.info('  llm_asserted     : %d', asserted)
        # Reported apart from the percentage on purpose: a language with no
        # frequency source is unmeasured, not 0% validated.
        logger.info('  no_source        : %d (excluded from the rate)', no_source)
        if checked:
            logger.info('  validated share  : %.1f%% of %d checkable senses',
                        100.0 * validated / checked, checked)
        else:
            logger.info('  validated share  : unmeasured — no checkable senses')
        if self.counts['skipped_tagged']:
            logger.info('  skipped (tagged) : %d', self.counts['skipped_tagged'])
        if self.counts['error']:
            logger.info('  errors           : %d', self.counts['error'])
        if self.repaired:
            logger.info('  repaired         : %d', len(self.repaired))

        still_flagged = [f for f in self.flagged if 'repaired_to' not in f]
        if still_flagged:
            shown = still_flagged[:SPOT_CHECK_SAMPLE]
            logger.info('-' * 64)
            logger.info('Spot-check sample (%d of %d still flagged):',
                        len(shown), len(still_flagged))
            for item in shown:
                logger.info('  sense %-7s %-20s + %-20s  %s',
                            item['sense_id'], item['lemma'],
                            item['collocate'], item['reason'])
        logger.info('=' * 64)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Grade generated collocates against a frequency source',
    )
    parser.add_argument('--language', required=True,
                        choices=[*LANGUAGE_CODES, 'all'],
                        help='Language code to process')
    parser.add_argument('--dry-run', action='store_true',
                        help='Report only: write no tags and make no LLM calls')
    parser.add_argument('--repair', action='store_true',
                        help='Re-prompt P1 once per unattested collocate')
    parser.add_argument('--limit', type=int, default=0,
                        help='Max senses per language (0 = all)')
    parser.add_argument('--only-untagged', action='store_true',
                        help='Skip senses that already carry a grounding tag')
    args = parser.parse_args()

    if args.dry_run:
        logger.info('DRY RUN — no tags written, no repair calls made')

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    codes = list(LANGUAGE_CODES) if args.language == 'all' else [args.language]
    ok = True
    for code in codes:
        run = CollocateValidationRun(
            db,
            LANGUAGE_CODES[code],
            dry_run=args.dry_run,
            repair=args.repair,
            limit=args.limit,
            only_untagged=args.only_untagged,
        )
        ok = run.run() and ok

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
