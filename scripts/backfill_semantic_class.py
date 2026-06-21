#!/usr/bin/env python3
"""
Backfill dim_vocabulary.semantic_class with a cheap LLM batch (TASK-507).

Every lemma (EN + ZH + JA) is classified into the ratified 6-value enum
(concrete | abstract | action | property | function | proper) so the ladder's
active_levels routing has a stable key — without it every word gets all 9
levels (the eval's "bean" failure).

Approach (plan §4 / TASK-507):
  - ~50 lemmas per LLM call, flash-tier model resolved from prompt_templates
    (task_name='semantic_class_classification', per language_id).
  - Prompt context per lemma = part_of_speech + the primary sense definition.
  - The prompt presents a TARGET-LANGUAGE class legend and the model returns
    {id: [class_index 1-6, confidence]} — numeric only, no English words cross
    the wire for ZH/JA. The index is mapped to the English enum here (the
    dim_vocabulary.semantic_class CHECK requires the English token). Confidence is
    persisted to dim_vocabulary.semantic_class_confidence. Rows below
    --conf-threshold are DEFAULTED to 'abstract' (the conservative class) and
    flagged (their stored confidence stays < threshold, queryable for human review).
  - Cost/observability: every call is logged to llm_calls by call_llm under
    task_name='semantic_class_classification'.

Idempotent: only classifies rows with semantic_class IS NULL unless --force.
Failures are logged and counted; they never abort the run.

Usage:
    python scripts/backfill_semantic_class.py --language all [--dry-run] [--limit N]
    python scripts/backfill_semantic_class.py --language zh --limit 100        # pilot
    python scripts/backfill_semantic_class.py --language all --emit-sample 200 \
        --sample-out spot_check_semantic_class.csv   # stratified human-review sheet
"""

import argparse
import csv
import logging
import os
import random
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.llm_service import call_llm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

for _noisy in ('httpx', 'httpcore', 'hpack', 'openai'):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

LANGUAGE_CODE_TO_ID = {'zh': 1, 'cn': 1, 'en': 2, 'ja': 3, 'jp': 3}
ID_TO_NAME = {1: 'zh', 2: 'en', 3: 'ja'}

# The model returns a NUMERIC class index (1-6) — never an English word — so the
# prompt can present a target-language legend and keep English out of the model's
# I/O. The English enum token (required by the dim_vocabulary.semantic_class CHECK)
# is produced only here, at write time.
INDEX_TO_CLASS = {1: 'concrete', 2: 'abstract', 3: 'action',
                  4: 'property', 5: 'function', 6: 'proper'}
DEFAULT_CLASS = 'abstract'  # conservative default for low-confidence / unparseable rows

PAGE_SIZE = 1000
TASK_NAME = 'semantic_class_classification'


def resolve_template(db, language_id: int) -> tuple[str, str, int]:
    """Return (model, template_text, version) for the classifier task + language."""
    resp = (
        db.table('prompt_templates')
        .select('model, template_text, version')
        .eq('task_name', TASK_NAME)
        .eq('language_id', language_id)
        .eq('is_active', True)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        raise RuntimeError(
            f"No active prompt_templates row for task={TASK_NAME} language_id={language_id}. "
            "Apply migrations/semantic_class_backfill.sql first."
        )
    r = rows[0]
    if not r.get('model'):
        raise RuntimeError(f"prompt_templates row for language_id={language_id} has no model.")
    return r['model'], r['template_text'], r['version']


def fetch_lemmas(db, language_id: int, force: bool, limit: int) -> list[dict]:
    """Page dim_vocabulary for the language, attaching the primary definition.

    Returns dicts: {id, lemma, pos, definition}. Skips already-classified rows
    unless --force.
    """
    rows: list[dict] = []
    start = 0
    while True:
        q = (
            db.table('dim_vocabulary')
            .select('id, lemma, part_of_speech, semantic_class, '
                    'dim_word_senses(definition, sense_rank)')
            .eq('language_id', language_id)
            .order('id')
            .range(start, start + PAGE_SIZE - 1)
        )
        batch = q.execute().data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        start += PAGE_SIZE

    if not force:
        rows = [r for r in rows if not (r.get('semantic_class') or '').strip()]

    out = []
    for r in rows:
        senses = r.get('dim_word_senses') or []
        definition = ''
        if senses:
            senses = sorted(senses, key=lambda s: (s.get('sense_rank') or 9999))
            definition = (senses[0].get('definition') or '').strip()
        out.append({
            'id': r['id'],
            'lemma': (r.get('lemma') or '').strip(),
            'pos': (r.get('part_of_speech') or '').strip(),
            'definition': definition,
        })

    if limit:
        out = out[:limit]
    return out


def build_prompt(template_text: str, batch: list[dict]) -> tuple[str, dict[str, dict]]:
    """Render the template for one batch. Returns (prompt, id_map).

    id_map maps the per-batch string index -> the lemma dict (so the model's
    keyed response can be joined back to the vocab id).
    """
    lines = []
    id_map: dict[str, dict] = {}
    for i, item in enumerate(batch, start=1):
        key = str(i)
        id_map[key] = item
        # Positional "<id>: <lemma> [<pos>] <definition>" — no English scaffolding
        # words; '—' placeholders avoid leaking English into a target-language prompt.
        definition = item['definition'] or '—'
        pos = item['pos'] or '?'
        lines.append(f'{key}: {item["lemma"]} [{pos}] {definition}')
    prompt = template_text.replace('{batch}', '\n'.join(lines))
    return prompt, id_map


def classify_batch(model: str, version: int, prompt: str) -> dict:
    """Call the LLM and return the parsed {id: {class, confidence}} mapping."""
    result = call_llm(
        prompt,
        model=model,
        temperature=0.0,
        response_format='json',
        provider='openrouter',
        timeout=60,
        pipeline='vocab_ladder',
        task_name=TASK_NAME,
        template_version=version,
    )
    return result if isinstance(result, dict) else {}


def _parse_entry(entry):
    """Extract (class_index, confidence) from one model result value.

    Canonical shape is a two-element array [class_index 1-6, confidence]. Also
    tolerates a bare int index, or a dict with numeric class/confidence, so a
    minor format wobble doesn't drop the row. Returns (None, conf) when the index
    cannot be read.
    """
    idx = None
    conf = 0.0
    if isinstance(entry, (list, tuple)):
        if entry:
            idx = entry[0]
        if len(entry) > 1:
            conf = entry[1]
    elif isinstance(entry, (int, float)):
        idx = entry
    elif isinstance(entry, dict):
        idx = entry.get('class', entry.get('c', entry.get('index')))
        conf = entry.get('confidence', entry.get('conf', 0.0))
    try:
        idx = int(idx)
    except (TypeError, ValueError):
        idx = None
    try:
        conf = float(conf)
    except (TypeError, ValueError):
        conf = 0.0
    return idx, max(0.0, min(1.0, conf))


def apply_result(stats, key_to_item, parsed, conf_threshold):
    """Validate one batch's parsed result into a list of (id, class, conf) writes."""
    writes = []
    for key, item in key_to_item.items():
        entry = parsed.get(key)
        if entry is None:
            logger.warning("No result for %r (id=%s)", item['lemma'], item['id'])
            stats['failed'] += 1
            continue
        idx, conf = _parse_entry(entry)
        cls = INDEX_TO_CLASS.get(idx)
        if cls is None:
            logger.warning("Invalid class index %r for %r (id=%s) — defaulting",
                           idx, item['lemma'], item['id'])
            cls = DEFAULT_CLASS
            conf = min(conf, conf_threshold - 0.01)
        if conf < conf_threshold:
            # Low-confidence → conservative default + flag (confidence preserved).
            cls = DEFAULT_CLASS
            stats['low_conf'] += 1
        writes.append((item['id'], cls, conf))
    return writes


def emit_sample(db, language_ids: list[int], n: int, out_path: str):
    """Write a class-stratified random sample of classified rows for human review."""
    pool: list[dict] = []
    for lid in language_ids:
        start = 0
        while True:
            batch = (
                db.table('dim_vocabulary')
                .select('id, lemma, part_of_speech, semantic_class, semantic_class_confidence, '
                        'dim_word_senses(definition, sense_rank)')
                .eq('language_id', lid)
                .not_.is_('semantic_class', 'null')
                .order('id')
                .range(start, start + PAGE_SIZE - 1)
                .execute()
            ).data or []
            for r in batch:
                senses = sorted(r.get('dim_word_senses') or [],
                                key=lambda s: (s.get('sense_rank') or 9999))
                r['_def'] = (senses[0].get('definition') if senses else '') or ''
                r['_lang'] = ID_TO_NAME.get(lid, str(lid))
            pool.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            start += PAGE_SIZE

    if not pool:
        logger.warning("No classified rows to sample.")
        return

    by_class: dict[str, list] = {}
    for r in pool:
        by_class.setdefault(r['semantic_class'], []).append(r)

    sample: list[dict] = []
    classes = list(by_class)
    per = max(1, n // max(1, len(classes)))
    for cls in classes:
        rows = by_class[cls]
        random.shuffle(rows)
        sample.extend(rows[:per])
    random.shuffle(sample)
    sample = sample[:n]

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['vocab_id', 'lang', 'lemma', 'pos', 'definition',
                    'machine_class', 'confidence', 'human_class', 'agree(Y/N)'])
        for r in sample:
            w.writerow([
                r['id'], r['_lang'], r.get('lemma', ''), r.get('part_of_speech', ''),
                r['_def'], r['semantic_class'],
                r.get('semantic_class_confidence', ''), '', '',
            ])
    logger.info("Wrote %d-row stratified spot-check sample → %s "
                "(fill human_class + agree, target >=90%% agreement)",
                len(sample), out_path)


def process_language(db, language_id: int, args) -> dict:
    model, template_text, version = resolve_template(db, language_id)
    lemmas = fetch_lemmas(db, language_id, args.force, args.limit)
    logger.info("[%s] %d lemma(s) to classify (model=%s)",
                ID_TO_NAME.get(language_id, language_id), len(lemmas), model)

    stats = {'updated': 0, 'low_conf': 0, 'failed': 0, 'batches': 0}
    bs = args.batch_size
    for i in range(0, len(lemmas), bs):
        batch = lemmas[i:i + bs]
        prompt, id_map = build_prompt(template_text, batch)
        stats['batches'] += 1
        try:
            parsed = classify_batch(model, version, prompt)
        except Exception as e:
            logger.warning("Batch %d failed (%d lemmas): %s",
                           stats['batches'], len(batch), e)
            stats['failed'] += len(batch)
            continue

        writes = apply_result(stats, id_map, parsed, args.conf_threshold)
        for vocab_id, cls, conf in writes:
            if args.dry_run:
                stats['updated'] += 1
                continue
            try:
                db.table('dim_vocabulary').update({
                    'semantic_class': cls,
                    'semantic_class_confidence': conf,
                }).eq('id', vocab_id).execute()
                stats['updated'] += 1
            except Exception as e:
                logger.warning("DB update failed for vocab %s: %s", vocab_id, e)
                stats['failed'] += 1

        logger.info("[%s] batch %d/%d done (updated=%d low_conf=%d failed=%d)",
                    ID_TO_NAME.get(language_id, language_id), stats['batches'],
                    (len(lemmas) + bs - 1) // bs,
                    stats['updated'], stats['low_conf'], stats['failed'])
    return stats


def main():
    parser = argparse.ArgumentParser(description='Backfill dim_vocabulary.semantic_class (LLM).')
    parser.add_argument('--language', required=True,
                        choices=sorted(set(LANGUAGE_CODE_TO_ID) | {'all'}))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int, default=0, help='Cap lemmas per language.')
    parser.add_argument('--batch-size', type=int, default=50)
    parser.add_argument('--force', action='store_true', help='Reclassify already-classified rows.')
    parser.add_argument('--conf-threshold', type=float, default=0.6)
    parser.add_argument('--emit-sample', type=int, default=0,
                        help='After classifying, write an N-row stratified spot-check CSV.')
    parser.add_argument('--sample-out', default='spot_check_semantic_class.csv')
    args = parser.parse_args()

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()
    if db is None:
        raise RuntimeError("Service role client unavailable (set SUPABASE_SERVICE_ROLE_KEY).")

    if args.language == 'all':
        language_ids = [1, 2, 3]
    else:
        language_ids = [LANGUAGE_CODE_TO_ID[args.language]]

    grand = {'updated': 0, 'low_conf': 0, 'failed': 0, 'batches': 0}
    for lid in language_ids:
        s = process_language(db, lid, args)
        for k in grand:
            grand[k] += s[k]

    logger.info("DONE. updated=%d low_conf=%d failed=%d batches=%d",
                grand['updated'], grand['low_conf'], grand['failed'], grand['batches'])

    if args.emit_sample and not args.dry_run:
        emit_sample(db, language_ids, args.emit_sample, args.sample_out)


if __name__ == '__main__':
    main()
