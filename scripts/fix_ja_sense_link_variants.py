#!/usr/bin/env python3
"""
Repoint ja sense links from UniDic lexeme headwords to the word as written (TASK-779).

The problem
    Tests linked before the orthBase fix (ede24bd4, 2026-08-26) carry
    vocab_sense_ids for UniDic's abstract *lexeme*, while the transcript spells a
    different headword. UniDic groups spellings — and sometimes distinct words —
    under one lemma, so 超え got linked to 越える, 抑え to 押さえる, 就く to 付く.
    Live 2026-09-16: 73 links across 32 ja tests, and 15 questions.
    The token map already points at the written word; only the id lists lag.

Two fixes, both driven by the map
    1. RELINK. For a linked sense whose word never appears in the map, take the
       sense the map uses for the token that word's lemma family resolves to, and
       swap it in tests.vocab_sense_ids and questions.sense_ids.
    2. REPARENT. Artifact headwords (classical 若し/長し/潔し/幼し, suffixed
       引く-他動詞, kana-bogus ドウジ) whose modern twin exists but has no sense of
       its own: move the senses onto the twin (dim_word_senses.vocab_id), the
       TASK-778 pattern. Sense ids do not change, so every reference — token maps,
       vocab_sense_ids, questions, user_vocabulary_knowledge — stays valid.
       Where the twin already has its own senses, this script does NOT merge; it
       reports the pair for the dictionary-duplicate audit instead.

Never touches: dim_word_senses.definition, token maps (rebuild_token_maps.py owns
those), or any sense that the map does resolve.

Usage:
    python scripts/fix_ja_sense_link_variants.py --dry-run
    python scripts/fix_ja_sense_link_variants.py
"""

import os
import sys
import argparse
import logging
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), '.env'))

from config import Config
from scripts.sense_linking_common import PAGE, get_processor
from scripts.rebuild_token_maps import map_sense_ids

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Artifact headwords: UniDic lexeme spellings that are not modern entries.
# Value is the written form a learner would look up.
ARTIFACT_HEADWORDS = {
    '若し': '若い', '長し': '長い', '潔し': '潔い', '幼し': '幼い',
    '引く-他動詞': '引く', 'ドウジ': '童子',
}


def lemma_family(word) -> set[str]:
    """Every headword spelling this token could have been linked under."""
    f = word.feature
    out = {word.surface}
    for attr in ('orthBase', 'lemma'):
        v = getattr(f, attr, None)
        if v and v != '*':
            out.add(v)
            out.add(v.split('-')[0])
    return out


def build_relink_plan(db, language_id: int, tests: list[dict], sense_vocab: dict,
                      vocab_lemma: dict) -> tuple[dict, list]:
    """{old_sense_id: new_sense_id} plus the rows we could not resolve."""
    proc = get_processor('ja')
    plan: dict[int, int] = {}
    unresolved = []

    for test in tests:
        token_map = test.get('vocab_token_map') or []
        mapped = map_sense_ids(token_map)
        missing = [s for s in (test.get('vocab_sense_ids') or []) if s not in mapped]
        if not missing:
            continue

        # lemma spelled by each mapped token -> the sense the map uses
        lemma_to_sense: dict[str, int] = {}
        for word, entry in zip(proc._get_tagger()(test['transcript']), token_map):
            sid = entry[1] if len(entry) > 1 else 0
            if sid:
                for name in lemma_family(word):
                    lemma_to_sense.setdefault(name, sid)

        for sid in missing:
            lemma = vocab_lemma.get(sense_vocab.get(sid))
            target = None
            if lemma:
                target = lemma_to_sense.get(lemma) or lemma_to_sense.get(lemma.split('-')[0])
            if target and target != sid:
                plan[sid] = target
            else:
                unresolved.append((test['slug'], sid, lemma))
    return plan, unresolved


def apply_relink(db, plan: dict, tests: list[dict], dry_run: bool) -> dict:
    counts = defaultdict(int)

    for test in tests:
        ids = test.get('vocab_sense_ids') or []
        if not any(s in plan for s in ids):
            continue
        new_ids, seen = [], set()
        for s in ids:
            t = plan.get(s, s)
            if t not in seen:
                seen.add(t)
                new_ids.append(t)
        counts['tests'] += 1
        counts['links'] += sum(1 for s in ids if s in plan)
        counts['collapsed'] += len(ids) - len(new_ids)
        if not dry_run:
            db.table('tests').update({'vocab_sense_ids': new_ids}).eq('id', test['id']).execute()

    questions = (db.table('questions')
                 .select('id, sense_ids')
                 .overlaps('sense_ids', [str(s) for s in plan])
                 .execute().data or [])
    for q in questions:
        ids = q.get('sense_ids') or []
        new_ids, seen = [], set()
        for s in ids:
            t = plan.get(s, s)
            if t not in seen:
                seen.add(t)
                new_ids.append(t)
        if new_ids != ids:
            counts['questions'] += 1
            if not dry_run:
                db.table('questions').update({'sense_ids': new_ids}).eq('id', q['id']).execute()
    return counts


def reparent_artifacts(db, language_id: int, vocab_by_lemma: dict, dry_run: bool) -> dict:
    """Move an artifact headword's senses onto its modern twin, when the twin is
    empty. A twin that already has senses is reported, not merged."""
    counts = defaultdict(int)
    for bad_lemma, good_lemma in ARTIFACT_HEADWORDS.items():
        bad, good = vocab_by_lemma.get(bad_lemma), vocab_by_lemma.get(good_lemma)
        if not bad or not good:
            logger.info("  %s -> %s: skipped (missing row)", bad_lemma, good_lemma)
            continue
        bad_senses = (db.table('dim_word_senses').select('id')
                      .eq('vocab_id', bad).execute().data or [])
        good_senses = (db.table('dim_word_senses').select('id')
                       .eq('vocab_id', good).execute().data or [])
        if good_senses:
            logger.info("  %s (%d senses) -> %s: twin already has %d senses; left for the "
                        "duplicate audit", bad_lemma, len(bad_senses), good_lemma,
                        len(good_senses))
            counts['deferred'] += 1
            continue
        logger.info("  %s -> %s: re-parent %d senses onto vocab %d",
                    bad_lemma, good_lemma, len(bad_senses), good)
        counts['reparented_words'] += 1
        counts['reparented_senses'] += len(bad_senses)
        if not dry_run:
            db.table('dim_word_senses').update({'vocab_id': good}) \
                .eq('vocab_id', bad).execute()
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()
    language_id = Config.LANGUAGE_CODE_TO_ID['ja']

    vocab, off = [], 0
    while True:
        page = (db.table('dim_vocabulary').select('id, lemma')
                .eq('language_id', language_id).range(off, off + PAGE - 1).execute().data or [])
        vocab += page
        if len(page) < PAGE:
            break
        off += PAGE
    vocab_lemma = {r['id']: r['lemma'] for r in vocab}
    vocab_by_lemma = {r['lemma']: r['id'] for r in vocab}

    logger.info("Artifact headwords:")
    rep = reparent_artifacts(db, language_id, vocab_by_lemma, args.dry_run)

    tests = (db.table('tests')
             .select('id, slug, transcript, vocab_sense_ids, vocab_token_map')
             .eq('language_id', language_id).eq('is_active', True).execute().data or [])
    sense_ids = sorted({s for t in tests for s in (t.get('vocab_sense_ids') or [])})
    sense_vocab = {}
    for i in range(0, len(sense_ids), 500):
        rows = (db.table('dim_word_senses').select('id, vocab_id')
                .in_('id', sense_ids[i:i + 500]).execute().data or [])
        sense_vocab.update({r['id']: r['vocab_id'] for r in rows})

    plan, unresolved = build_relink_plan(db, language_id, tests, sense_vocab, vocab_lemma)

    # Targets come from the token maps, so they are not in sense_vocab yet — and
    # the headword each one lands on is exactly what a reviewer must check.
    targets = sorted(set(plan.values()) - set(sense_vocab))
    for i in range(0, len(targets), 500):
        rows = (db.table('dim_word_senses').select('id, vocab_id')
                .in_('id', targets[i:i + 500]).execute().data or [])
        sense_vocab.update({r['id']: r['vocab_id'] for r in rows})

    logger.info("Relink plan: %d sense(s)", len(plan))
    for old, new in list(plan.items())[:80]:
        logger.info("  %s (%s) -> %s (%s)", old, vocab_lemma.get(sense_vocab.get(old)),
                    new, vocab_lemma.get(sense_vocab.get(new), '?'))
    for slug, sid, lemma in unresolved:
        logger.info("  UNRESOLVED %s: sense %s (%s) — left as is", slug, sid, lemma)

    counts = apply_relink(db, plan, tests, args.dry_run)
    logger.info("%s: %d link(s) across %d test(s), %d question(s); %d duplicate id(s) "
                "collapsed; %d word(s)/%d sense(s) re-parented, %d deferred",
                'DRY RUN' if args.dry_run else 'APPLIED',
                counts['links'], counts['tests'], counts['questions'], counts['collapsed'],
                rep['reparented_words'], rep['reparented_senses'], rep['deferred'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
