#!/usr/bin/env python3
"""Dual Translation passage builder — batch runner (TASK-603).

Off-hot-path runner that (a) extracts 2-4 sentence L2 gold passages from the
existing `tests.transcript` corpus into `dt_passage`, and (b) generates one L1
reference per supported L1 (!= the passage's L2) into `dt_passage_reference`
via OpenRouter. All the pure logic lives in
`services.dual_translation.passage_builder`; this file is just the DB + corpus
wiring around it.

Idempotent: re-running inserts no duplicate passages (in-app dedupe on
(source_ref_id, normalized l2_text)) and no duplicate references (skips any
(passage, L1) that already exists — also enforced by the
dt_passage_reference UNIQUE(passage_id, l1_language_id) as a backstop).

Corpus scope: only `is_active` tests with a non-empty transcript, in a
supported study language (zh/en/ja). `--limit` caps tests *per language* so a
first run is a cheap smoke (default 4/lang ~= 12 tests). Each new passage costs
one OpenRouter call per L1 reference, so mind the cap before a full run.

Usage:
    python scripts/build_dt_passages.py [--limit N] [--languages zh,en,ja]
                                        [--tests-per-lang N] [--dry-run]

Options:
    --limit N            Alias for --tests-per-lang. Max source tests per
                         language (default 4). 0 = no cap (full corpus).
    --languages CSV      Comma-separated L2 codes to source (default zh,en,ja).
    --dry-run            Build + report counts, but write nothing and make no
                         OpenRouter calls.
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.dual_translation import passage_builder as pb

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('build_dt_passages')

DEFAULT_TESTS_PER_LANG = 4


class PassageBuildRunner:
    def __init__(self, db, tests_per_lang: int, dry_run: bool, test_ids: list[str] | None = None):
        self.db = db
        self.tests_per_lang = tests_per_lang
        self.dry_run = dry_run
        # Optional explicit source-test allowlist (e.g. a completed-test fixture
        # for the live smoke). When set, the per-language newest cap is ignored
        # and only these tests are sourced (still filtered to active + transcript
        # + the target language).
        self.test_ids = test_ids or None
        self.stats = {
            'tests_seen': 0, 'passages_candidate': 0, 'passages_inserted': 0,
            'passages_skipped_dupe': 0, 'refs_generated': 0, 'refs_skipped_existing': 0,
            'refs_failed': 0,
        }

    # -- corpus ------------------------------------------------------------

    def _fetch_tests(self, language_id: int) -> list[dict]:
        """Active tests with a transcript in this L2, newest first, capped."""
        query = (
            self.db.table('tests')
            .select('id, transcript, difficulty, language_id')
            .eq('language_id', language_id)
            .eq('is_active', True)
            .not_.is_('transcript', 'null')
            .order('created_at', desc=True)
        )
        if self.test_ids:
            query = query.in_('id', self.test_ids)
        elif self.tests_per_lang:
            query = query.limit(self.tests_per_lang)
        return query.execute().data or []

    def _existing_passage_keys(self, language_id: int, language_code: str) -> set:
        """dedupe_keys of dt_passage rows already present for this L2."""
        rows = (
            self.db.table('dt_passage')
            .select('source_ref_id, l2_text')
            .eq('l2_language_id', language_id)
            .execute()
        ).data or []
        return {pb.dedupe_key(r['source_ref_id'], r['l2_text'], language_code) for r in rows}

    def _existing_reference_l1s(self, passage_id) -> set:
        """l1_language_ids that already have a reference for this passage."""
        rows = (
            self.db.table('dt_passage_reference')
            .select('l1_language_id')
            .eq('passage_id', passage_id)
            .execute()
        ).data or []
        return {r['l1_language_id'] for r in rows}

    # -- build -------------------------------------------------------------

    def run_language(self, language_id: int, language_code: str) -> None:
        logger.info("=== L2=%s (id=%s) ===", language_code, language_id)
        tests = self._fetch_tests(language_id)
        self.stats['tests_seen'] += len(tests)
        logger.info("  %d source test(s)", len(tests))

        sourced_ids = [str(t['id']) for t in tests]
        candidates: list[dict] = []
        for test in tests:
            candidates.extend(pb.build_passages_for_test(test, language_code))
        self.stats['passages_candidate'] += len(candidates)

        existing_keys = self._existing_passage_keys(language_id, language_code)
        fresh = pb.select_new_passages(candidates, existing_keys, language_code)
        self.stats['passages_skipped_dupe'] += len(candidates) - len(fresh)
        logger.info("  %d candidate span(s); %d new after dedupe", len(candidates), len(fresh))

        if self.dry_run:
            for row in fresh:
                n_refs = len(pb.reference_l1_ids(row['l2_language_id']))
                self.stats['passages_inserted'] += 1
                self.stats['refs_generated'] += n_refs
                logger.info("  [dry-run] would insert passage (%d L1 refs): %s",
                            n_refs, _preview(row['l2_text']))
            return

        for row in fresh:
            self._insert_passage(row)

        # Reconcile references against ALL in-scope passages — newly inserted *and*
        # pre-existing ones whose references are missing (e.g. an earlier run inserted
        # the passage but the router had no slug, so refs failed). This decouples
        # reference idempotency from passage insertion: a re-run backfills any gaps.
        if not sourced_ids:
            return
        for passage in self._fetch_passages_for_sources(language_id, sourced_ids):
            self._reconcile_references(passage)

    def _insert_passage(self, row: dict) -> None:
        insert_resp = self.db.table('dt_passage').insert(row).execute()
        if not insert_resp.data:
            logger.error("  passage insert returned no row: %s", _preview(row['l2_text']))
            return
        self.stats['passages_inserted'] += 1

    def _fetch_passages_for_sources(self, language_id: int, sourced_ids: list[str]) -> list[dict]:
        """All active passages sourced from these tests (for reference reconciliation)."""
        return (
            self.db.table('dt_passage')
            .select('id, l2_text, l2_language_id')
            .eq('l2_language_id', language_id)
            .eq('status', 'active')
            .in_('source_ref_id', sourced_ids)
            .execute()
        ).data or []

    def _reconcile_references(self, passage: dict) -> None:
        already = self._existing_reference_l1s(passage['id'])
        for l1_id in pb.reference_l1_ids(passage['l2_language_id']):
            if l1_id in already:
                self.stats['refs_skipped_existing'] += 1
                continue
            self._persist_reference(passage['id'], passage, l1_id)

    def _persist_reference(self, passage_id, passage_row: dict, l1_id: int) -> None:
        l1_code = Config.LANGUAGES.get(l1_id, {}).get('code', str(l1_id))
        ref = pb.generate_l1_reference(
            self.db,
            l2_text=passage_row['l2_text'],
            l2_language_id=passage_row['l2_language_id'],
            l1_language_id=l1_id,
            l1_code=l1_code,
        )
        if not ref:
            self.stats['refs_failed'] += 1
            return
        self.db.table('dt_passage_reference').insert({'passage_id': passage_id, **ref}).execute()
        self.stats['refs_generated'] += 1
        logger.info("    + L1=%s ref via %s", l1_code, ref['generator_slug'])


def _preview(text: str, n: int = 48) -> str:
    text = (text or '').replace('\n', ' ')
    return text if len(text) <= n else text[:n] + '…'


def _resolve_languages(csv: str) -> list[tuple[int, str]]:
    out = []
    for code in [c.strip().lower() for c in csv.split(',') if c.strip()]:
        lang_id = Config.LANGUAGE_CODE_TO_ID.get(code)
        if lang_id is None or lang_id not in pb.SUPPORTED_LANGUAGE_IDS:
            logger.warning("Skipping unsupported language code: %s", code)
            continue
        out.append((lang_id, code))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Build dt_passage + dt_passage_reference rows.")
    parser.add_argument('--limit', '--tests-per-lang', dest='tests_per_lang', type=int,
                        default=DEFAULT_TESTS_PER_LANG,
                        help="Max source tests per language (0 = no cap). Default 4.")
    parser.add_argument('--languages', default='zh,en,ja',
                        help="Comma-separated L2 codes to source. Default zh,en,ja.")
    parser.add_argument('--dry-run', action='store_true',
                        help="Report counts without writing or calling OpenRouter.")
    parser.add_argument('--test-ids', default='',
                        help="Comma-separated tests.id allowlist (overrides the newest-per-lang "
                             "cap). Use for a targeted fixture/smoke build.")
    args = parser.parse_args()

    test_ids = [t.strip() for t in args.test_ids.split(',') if t.strip()] or None

    languages = _resolve_languages(args.languages)
    if not languages:
        logger.error("No supported languages to process.")
        return 1

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()
    if db is None:
        logger.error("No Supabase admin client (check SUPABASE_SERVICE_ROLE_KEY env).")
        return 1

    runner = PassageBuildRunner(db, tests_per_lang=args.tests_per_lang, dry_run=args.dry_run,
                                test_ids=test_ids)
    for language_id, language_code in languages:
        runner.run_language(language_id, language_code)

    logger.info("Done%s. Stats: %s", " (dry-run)" if args.dry_run else "", runner.stats)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
