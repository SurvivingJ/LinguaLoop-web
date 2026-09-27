#!/usr/bin/env python3
"""
Build the FROZEN reference set for scoring future changes to vocabulary-ladder
exercise generation (Phase 0, 2026-09-24).

Every future change to exercise-generation cost/quality must be judged
non-inferior against this set. It is built once, snapshotted into
``data/eval/exercise_gen_reference_set_2026-09.json``, and never silently
regenerated -- if the DB changes underneath it, the JSON file does not, by
design (see module docstring on ``build()``  below).

Usage::

    PYTHONPATH=. python -m scripts.build_exercise_gen_reference_set
    PYTHONPATH=. python -m scripts.build_exercise_gen_reference_set --dry-run
    PYTHONPATH=. python -m scripts.build_exercise_gen_reference_set --out data/eval/other.json

Read-only. Issues nothing but ``select`` through the Supabase client -- no
writes, no LLM calls.

Selection logic
----------------
For each of zh / en / ja:

1. **Benchmark pool** -- senses with at least one *valid* ``word_assets`` row
   whose ``model_used = 'claude-code:batch-exercise-generation'`` (the
   Sep 6-19 2026 batch-exercise-generation run), that are NOT in
   ``calibration_anchor_blocklist``, and that have rendered ``exercises``
   rows. Each such sense's rendered exercises carry a single
   ``complexity_tier`` (T1..T6); judges skip difficulty <= 2, i.e. tier T1
   (see ``dim_complexity_tiers.difficulty_min/max`` -- T1 is difficulty 1-2,
   T2+ is difficulty >= 3), so T1 senses are dropped from the benchmark pool.
2. From the eligible pool, up to 50 senses are chosen by a deterministic
   round-robin over (POS bucket x Zipf bucket) strata, so the selection is
   spread across parts of speech and frequency bands rather than clustered.
3. If a language has fewer than 50 eligible benchmark senses, the shortfall
   (50 - selected) is filled from a *separate* ``top_up_candidates`` list:
   native-language senses with NO rendered exercises yet (not blocklisted),
   stratified the same way. These are NOT part of the frozen benchmark --
   they are a to-do list for future authoring via the
   ``batch-exercise-authoring`` staged chain.

POS tags are stored under at least three different tagging conventions per
language in this DB (short codes, spelled-out English, native-script tags)
-- ``_POS_BUCKETS`` below is an explicit, auditable mapping of every value
observed in the live DB as of 2026-09-24 into 4 broad buckets
(noun/verb/adj/adv) plus 'other'; anything not listed falls into 'other'
rather than raising, so a genuinely new tag degrades stratification instead
of crashing the build.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger('build_exercise_gen_reference_set')

BENCHMARK_MODEL = 'claude-code:batch-exercise-generation'
LANGUAGES = {'zh': 1, 'en': 2, 'ja': 3}
TARGET_PER_LANGUAGE = 50
BLOCKLIST_TABLE = 'calibration_anchor_blocklist'
_PAGE = 1000

# Every part-of-speech string observed in dim_vocabulary as of 2026-09-24,
# mapped to a broad bucket for stratified sampling. See module docstring.
_POS_BUCKETS: dict[str, str] = {
    # noun
    'n': 'noun', 'noun': 'noun', 'NOUN': 'noun',
    'nr': 'noun', 'ns': 'noun', 'nt': 'noun', 'nz': 'noun', 'nrt': 'noun', 'ng': 'noun',
    '名词': 'noun', '名詞': 'noun',
    # verb
    'v': 'verb', 'verb': 'verb', 'VERB': 'verb',
    'vn': 'verb', 'vg': 'verb', 'vd': 'verb', '情态动词': 'verb',
    '动词': 'verb', '動詞': 'verb',
    # adjective
    'a': 'adj', 'adj': 'adj', 'adjective': 'adj', 'ADJ': 'adj', 'an': 'adj',
    '形容词': 'adj', '形容詞': 'adj', '形状詞': 'adj',
    # adverb
    'd': 'adv', 'adv': 'adv', 'adverb': 'adv', 'ADV': 'adv', 'ad': 'adv',
    '副词': 'adv', '副詞': 'adv',
    # everything else -> 'other' (idiom, phrase, numeral, conjunction,
    # preposition, auxiliary, pronoun, suffix, locality words, ...)
    'l': 'other', 'i': 'other', 'idiom': 'other', 'conjunction': 'other',
    '介词': 'other', 'preposition': 'other', 'phrase': 'other', 'numeral': 'other',
    '接尾辞': 'other', 'auxiliary': 'other', '代名詞': 'other',
}


def normalize_pos(pos: str | None) -> str:
    if not pos:
        return 'other'
    return _POS_BUCKETS.get(pos, 'other')


def zipf_bucket(zipf: float | None) -> str:
    """Fixed bins (not sample-quantiles) so the bucket of a given Zipf value
    never shifts as the underlying candidate pool changes."""
    if zipf is None:
        return 'unknown'
    if zipf < 3.5:
        return 'low'
    if zipf < 5.5:
        return 'mid'
    return 'high'


def _paginate(query_builder, page: int = _PAGE):
    """Yield all rows of a supabase-py query via .range() pagination."""
    start = 0
    while True:
        resp = query_builder().range(start, start + page - 1).execute()
        rows = resp.data or []
        if not rows:
            break
        yield from rows
        if len(rows) < page:
            break
        start += page


def fetch_tier_difficulty(db) -> dict[str, tuple[int, int]]:
    """tier_code -> (difficulty_min, difficulty_max), from dim_complexity_tiers."""
    resp = db.table('dim_complexity_tiers').select('tier_code,difficulty_min,difficulty_max').execute()
    return {row['tier_code']: (row['difficulty_min'], row['difficulty_max']) for row in (resp.data or [])}


def fetch_blocklisted_sense_ids(db) -> set[int]:
    ids: set[int] = set()
    for row in _paginate(lambda: db.table(BLOCKLIST_TABLE).select('sense_id')):
        ids.add(row['sense_id'])
    return ids


def fetch_benchmark_sense_ids(db, language_id: int) -> set[int]:
    ids: set[int] = set()
    for row in _paginate(
        lambda: db.table('word_assets')
        .select('sense_id')
        .eq('model_used', BENCHMARK_MODEL)
        .eq('is_valid', True)
        .eq('language_id', language_id)
    ):
        ids.add(row['sense_id'])
    return ids


def fetch_exercise_tiers_by_sense(db, sense_ids: list[int]) -> dict[int, list[str]]:
    """sense_id -> list of complexity_tier values seen across its exercise rows."""
    tiers: dict[int, list[str]] = defaultdict(list)
    for start in range(0, len(sense_ids), 200):
        chunk = sense_ids[start:start + 200]
        for row in _paginate(
            lambda chunk=chunk: db.table('exercises')
            .select('word_sense_id,complexity_tier')
            .in_('word_sense_id', chunk)
        ):
            tiers[row['word_sense_id']].append(row['complexity_tier'])
    return tiers


def modal_tier(tier_list: list[str]) -> str | None:
    """The most common tier for a sense; ties broken by first occurrence.
    Logs a warning if a sense's exercises disagree on tier (data-quality
    signal -- should not happen if tier is assigned once at generation time)."""
    if not tier_list:
        return None
    counts: dict[str, int] = defaultdict(int)
    for t in tier_list:
        counts[t] += 1
    if len(counts) > 1:
        logger.warning('sense has mixed complexity_tier values across exercises: %s', counts)
    return max(counts.items(), key=lambda kv: (kv[1], -tier_list.index(kv[0])))[0]


def fetch_native_sense_rows(db, language_id: int, sense_ids: list[int] | None = None,
                             exclude_ids: set[int] | None = None,
                             require_no_exercises: bool = False) -> list[dict]:
    """Native-language dim_word_senses rows (word_language_id == definition_language_id)
    joined to dim_vocabulary for lemma/pos/zipf.

    If ``sense_ids`` is given, restricts to those ids (chunked .in_()).
    If ``require_no_exercises`` is True, additionally restricts to senses with
    zero rows in ``exercises`` (used for the top-up candidate pool) -- this is
    done by fetching all word_sense_ids that DO have exercises and excluding
    them in Python, since supabase-py has no NOT IN (subquery) primitive.
    """
    exclude_ids = set(exclude_ids or ())

    have_exercises: set[int] = set()
    if require_no_exercises:
        for row in _paginate(lambda: db.table('exercises').select('word_sense_id')):
            wsid = row.get('word_sense_id')
            if wsid is not None:
                have_exercises.add(wsid)

    out: list[dict] = []

    def _handle_batch(rows: list[dict]):
        for ws in rows:
            if ws['word_language_id'] != ws['definition_language_id']:
                continue
            if ws['id'] in exclude_ids:
                continue
            if require_no_exercises and ws['id'] in have_exercises:
                continue
            out.append(ws)

    select_cols = ('id,vocab_id,word_language_id,definition_language_id,definition,'
                   'dim_vocabulary(lemma,part_of_speech,frequency_rank)')

    if sense_ids is not None:
        for start in range(0, len(sense_ids), 200):
            chunk = sense_ids[start:start + 200]
            resp = (db.table('dim_word_senses')
                    .select(select_cols)
                    .in_('id', chunk)
                    .execute())
            _handle_batch(resp.data or [])
    else:
        for row in _paginate(
            lambda: db.table('dim_word_senses')
            .select(select_cols)
            .eq('word_language_id', language_id)
        ):
            _handle_batch([row])

    return out


def flatten_sense_row(ws: dict) -> dict:
    vocab = ws.get('dim_vocabulary') or {}
    if isinstance(vocab, list):
        vocab = vocab[0] if vocab else {}
    return {
        'sense_id': ws['id'],
        'lemma': vocab.get('lemma'),
        'pos_raw': vocab.get('part_of_speech'),
        'pos_bucket': normalize_pos(vocab.get('part_of_speech')),
        'zipf': vocab.get('frequency_rank'),
        'zipf_bucket': zipf_bucket(vocab.get('frequency_rank')),
        'definition': ws.get('definition'),
    }


def stratified_select(candidates: list[dict], n: int) -> list[dict]:
    """Deterministic round-robin over (pos_bucket, zipf_bucket) cells, so the
    selection spreads across POS and frequency instead of clustering on
    whatever happens to sort first. Cells and within-cell order are both
    sorted by sense_id for full reproducibility."""
    cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for c in candidates:
        cells[(c['pos_bucket'], c['zipf_bucket'])].append(c)
    for key in cells:
        cells[key].sort(key=lambda c: c['sense_id'])

    cell_keys = sorted(cells.keys())
    selected: list[dict] = []
    while len(selected) < n and any(cells[k] for k in cell_keys):
        for key in cell_keys:
            if not cells[key]:
                continue
            selected.append(cells[key].pop(0))
            if len(selected) >= n:
                break
    return selected


def fetch_word_asset_snapshot(db, sense_id: int, language_id: int) -> list[dict]:
    resp = (db.table('word_assets')
            .select('asset_type,model_used,is_valid,content,generation_batch_id,created_at')
            .eq('sense_id', sense_id)
            .eq('language_id', language_id)
            .eq('model_used', BENCHMARK_MODEL)
            .eq('is_valid', True)
            .order('asset_type')
            .execute())
    return resp.data or []


def fetch_exercise_snapshot(db, sense_id: int) -> list[dict]:
    resp = (db.table('exercises')
            .select('exercise_type,ladder_level,complexity_tier,tags,content')
            .eq('word_sense_id', sense_id)
            .order('ladder_level')
            .execute())
    rows = []
    for row in (resp.data or []):
        tags = row.get('tags') or {}
        rows.append({
            'type': row['exercise_type'],
            'level': row['ladder_level'],
            'variant': tags.get('variant'),
            'complexity_tier': row['complexity_tier'],
            'payload': row['content'],
        })
    return rows


def build(db, lang_code: str, language_id: int, tier_difficulty: dict[str, tuple[int, int]],
          blocklisted: set[int]) -> tuple[list[dict], list[dict], dict]:
    """Returns (reference_set_entries, top_up_candidates, stats) for one language."""
    raw_benchmark_ids = fetch_benchmark_sense_ids(db, language_id)
    benchmark_ids = sorted(raw_benchmark_ids - blocklisted)

    tiers_by_sense = fetch_exercise_tiers_by_sense(db, benchmark_ids)
    eligible_ids = []
    dropped_no_exercises = 0
    dropped_low_difficulty = 0
    for sid in benchmark_ids:
        tier = modal_tier(tiers_by_sense.get(sid, []))
        if tier is None:
            dropped_no_exercises += 1
            continue
        dmin, _ = tier_difficulty.get(tier, (0, 0))
        if dmin < 3:
            dropped_low_difficulty += 1
            continue
        eligible_ids.append((sid, tier, dmin))

    sense_info = {ws['id']: flatten_sense_row(ws)
                  for ws in fetch_native_sense_rows(db, language_id, sense_ids=[s for s, _, _ in eligible_ids])}

    candidates = []
    for sid, tier, dmin in eligible_ids:
        info = sense_info.get(sid)
        if info is None:
            # Sense row wasn't native (word_language_id != definition_language_id)
            # or otherwise missing -- exclude rather than guess.
            continue
        info = dict(info)
        info['tier'] = tier
        info['difficulty'] = dmin
        candidates.append(info)

    candidates.sort(key=lambda c: c['sense_id'])
    selected = stratified_select(candidates, TARGET_PER_LANGUAGE)

    reference_entries = []
    for c in selected:
        reference_entries.append({
            'sense_id': c['sense_id'],
            'language': lang_code,
            'lemma': c['lemma'],
            'pos': c['pos_raw'],
            'pos_bucket': c['pos_bucket'],
            'definition': c['definition'],
            'tier': c['tier'],
            'difficulty': c['difficulty'],
            'zipf': c['zipf'],
            'word_assets': fetch_word_asset_snapshot(db, c['sense_id'], language_id),
            'exercises': fetch_exercise_snapshot(db, c['sense_id']),
        })

    top_up_needed = max(0, TARGET_PER_LANGUAGE - len(selected))
    top_up_candidates: list[dict] = []
    if top_up_needed:
        pool_rows = fetch_native_sense_rows(
            db, language_id, exclude_ids=blocklisted, require_no_exercises=True,
        )
        pool = [flatten_sense_row(ws) for ws in pool_rows]
        pool.sort(key=lambda c: c['sense_id'])
        top_up_selected = stratified_select(pool, top_up_needed)
        for c in top_up_selected:
            top_up_candidates.append({
                'sense_id': c['sense_id'],
                'language': lang_code,
                'lemma': c['lemma'],
                'pos': c['pos_raw'],
                'pos_bucket': c['pos_bucket'],
                'definition': c['definition'],
                'zipf': c['zipf'],
                'note': 'no exercises yet -- candidate for future authoring via '
                        'batch-exercise-authoring to backfill the benchmark set',
            })

    stats = {
        'raw_benchmark_senses': len(raw_benchmark_ids),
        'blocklisted_excluded': len(raw_benchmark_ids & blocklisted),
        'dropped_no_rendered_exercises': dropped_no_exercises,
        'dropped_difficulty_lt_3': dropped_low_difficulty,
        'eligible_pool': len(candidates),
        'benchmark_selected': len(selected),
        'top_up_needed': top_up_needed,
        'top_up_selected': len(top_up_candidates),
    }
    return reference_entries, top_up_candidates, stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default='data/eval/exercise_gen_reference_set_2026-09.json')
    parser.add_argument('--dry-run', action='store_true', help='compute and print stats only')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        stream=sys.stdout)
    for noisy in ('httpx', 'httpcore'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    tier_difficulty = fetch_tier_difficulty(db)
    blocklisted = fetch_blocklisted_sense_ids(db)

    reference_set: list[dict] = []
    top_up_candidates: list[dict] = []
    per_language_stats: dict[str, dict] = {}

    for lang_code, language_id in LANGUAGES.items():
        entries, top_up, stats = build(db, lang_code, language_id, tier_difficulty, blocklisted)
        reference_set.extend(entries)
        top_up_candidates.extend(top_up)
        per_language_stats[lang_code] = stats
        logger.info('%s: %s', lang_code, stats)

    if args.dry_run:
        logger.info('dry run -- not writing %s', args.out)
        return

    output = {
        'metadata': {
            'created': '2026-09-24',
            'purpose': (
                'Frozen reference set for scoring future changes to vocabulary-ladder '
                'exercise generation. Any cost optimisation to the generation pipeline '
                'must be quality non-inferior against this set.'
            ),
            'benchmark_model': BENCHMARK_MODEL,
            'benchmark_batch_window': '2026-09-06 to 2026-09-19',
            'target_per_language': TARGET_PER_LANGUAGE,
            'selection_criteria': {
                'benchmark': (
                    'senses with >=1 valid word_assets row from the benchmark model, '
                    'not in calibration_anchor_blocklist, with rendered exercises at '
                    'complexity_tier != T1 (judges skip difficulty <= 2, i.e. T1; '
                    'see dim_complexity_tiers.difficulty_min), stratified by a '
                    '(POS bucket x fixed Zipf bucket) round-robin, up to '
                    f'{TARGET_PER_LANGUAGE} per language'
                ),
                'top_up_candidates': (
                    'when a language has fewer than the target benchmark senses, the '
                    'shortfall is filled from native-language senses with NO rendered '
                    'exercises yet, not blocklisted, stratified the same way. These are '
                    'NOT part of the frozen benchmark -- they are unauthored and must be '
                    'built via the batch-exercise-authoring staged chain before they can '
                    'serve as benchmark items.'
                ),
                'pos_buckets': 'noun / verb / adj / adv / other -- see _POS_BUCKETS in this script',
                'zipf_buckets': 'low <3.5, mid 3.5-5.5, high >=5.5 (fixed bins, not sample quantiles)',
                'definition_filter': 'word_language_id == definition_language_id (native gloss only; '
                                      'cross-language glosses share the same vocab_id/keys and are excluded)',
            },
            'counts': per_language_stats,
            'reference_set_size': len(reference_set),
            'top_up_candidates_size': len(top_up_candidates),
        },
        'reference_set': reference_set,
        'top_up_candidates': top_up_candidates,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, sort_keys=False)

    size_kb = os.path.getsize(args.out) / 1024
    logger.info('wrote %s (%.1f KB): %d reference senses, %d top-up candidates',
                args.out, size_kb, len(reference_set), len(top_up_candidates))


if __name__ == '__main__':
    main()
