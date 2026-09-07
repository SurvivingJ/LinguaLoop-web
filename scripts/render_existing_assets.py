#!/usr/bin/env python
"""Render exercises for senses that already have valid word_assets.

Companion to upload_exercises.py --no-render: that script stores the
hand-authored assets fast (no judges). This script does the slow part
(LadderExerciseRenderer.render_all, which fires the L1/L3/L6/L7 judges)
as a separate, resumable pass so authoring isn't blocked on judge latency.

Usage:
    python scripts/render_existing_assets.py --language ja --sense-ids 36089,35093,...
"""
import argparse
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

_LANG_ID = {'zh': 1, 'en': 2, 'ja': 3}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', required=True, choices=['zh', 'en', 'ja'])
    parser.add_argument('--sense-ids', required=True, help='comma-separated sense ids')
    args = parser.parse_args()

    db = get_supabase_admin()
    language_id = _LANG_ID[args.language]
    renderer = LadderExerciseRenderer(db)

    sense_ids = [int(s) for s in args.sense_ids.split(',') if s.strip()]
    logger.info("Rendering %d sense(s): %s", len(sense_ids), sense_ids)

    total = 0
    for i, sid in enumerate(sense_ids, 1):
        # Skip senses that already have exercise rows (idempotent re-runs).
        existing = db.table('exercises').select('id').eq('word_sense_id', sid).limit(1).execute()
        if existing.data:
            logger.info("[%d/%d] sense %s already has exercises — skipping", i, len(sense_ids), sid)
            continue
        logger.info("[%d/%d] rendering sense %s", i, len(sense_ids), sid)
        ids = renderer.render_all(sid, language_id)
        total += len(ids)
        if not ids:
            logger.warning("    rendered 0 exercises for sense %s — check the core asset", sid)
        else:
            logger.info("    rendered %d exercises", len(ids))

    logger.info("Done. Rendered %d exercises total.", total)
    return 0


if __name__ == '__main__':
    sys.exit(main())
