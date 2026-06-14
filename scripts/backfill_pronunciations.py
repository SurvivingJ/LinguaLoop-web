#!/usr/bin/env python3
"""
Backfill dim_word_senses.pronunciation deterministically (no LLM cost).

TASK-506 (Exercise Generation v2, Phase 0). dim_word_senses.pronunciation is a
hard requirement for reading / tone exercise types but is ~0% populated
(finding G3). This script fills it deterministically:

  ZH (language_id=1): pypinyin with jieba word-context + the existing sandhi
      engine (services/pinyin_service.process_passage). Stored as
      "<tone-marked pinyin> (<machine-readable tone digits, sandhi applied>)",
      e.g. 你好 -> "nǐ hǎo (ni2 hao3)". The diacritics carry the dictionary
      (base) tones; the digit string carries the spoken (context) tones after
      third-tone / 一 / 不 sandhi.
  JA (language_id=3): fugashi + UniDic (unidic-lite) kana reading, normalised to
      hiragana. NOTE: as of 2026-06-14 there are 0 JA senses (the TASK-505 JA
      extraction batch is deferred for cost), so --language ja is currently a
      no-op; the code path is ready for when JA senses exist.

Idempotent: skips senses whose pronunciation is already populated unless --force.
Failures are logged with a reason and counted; they never abort the run.

Usage:
    python scripts/backfill_pronunciations.py --language zh [--dry-run] [--limit N] [--force]
    python scripts/backfill_pronunciations.py --language ja [--dry-run] [--limit N] [--force]
"""

import argparse
import logging
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Quiet per-request HTTP / segmentation chatter (thousands of rows otherwise).
for _noisy in ('httpx', 'httpcore', 'hpack', 'jieba'):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

LANGUAGE_CODE_TO_ID = {'zh': 1, 'cn': 1, 'en': 2, 'ja': 3, 'jp': 3}

PAGE_SIZE = 1000

# Tone-mark vowel tables (tones 1-4; neutral tone 5 = no mark).
_TONE_MARKS = {
    'a': 'āáǎà', 'e': 'ēéěè', 'i': 'īíǐì',
    'o': 'ōóǒò', 'u': 'ūúǔù', 'ü': 'ǖǘǚǜ',
}


def _add_diacritic(syllable: str, tone: int) -> str:
    """Place the tone diacritic on the correct vowel of a toneless syllable.

    Standard placement: a/e always take the mark; in 'ou' the o takes it;
    otherwise the last vowel of i/o/u/ü takes it. Tone 5 (neutral) / out of
    range -> returned unchanged.
    """
    if not syllable or tone < 1 or tone > 4:
        return syllable

    if 'a' in syllable:
        v, idx = 'a', syllable.index('a')
    elif 'e' in syllable:
        v, idx = 'e', syllable.index('e')
    elif 'ou' in syllable:
        v, idx = 'o', syllable.index('ou')
    else:
        idx = -1
        v = None
        for i in range(len(syllable) - 1, -1, -1):
            if syllable[i] in 'iouü':
                v, idx = syllable[i], i
                break
        if v is None:
            return syllable

    marked = _TONE_MARKS[v][tone - 1]
    return syllable[:idx] + marked + syllable[idx + 1:]


def zh_pronunciation(lemma: str) -> str | None:
    """Compute "<tone-marked pinyin> (<tone digits w/ sandhi>)" for a ZH lemma."""
    from services.pinyin_service import process_passage

    tokens = [t for t in process_passage(lemma) if not t['is_punctuation']]
    if not tokens:
        return None

    marked_parts = []
    digit_parts = []
    for t in tokens:
        syl = t['pinyin_text']
        if not syl:
            continue
        base = t['base_tone']
        ctx = t['context_tone']
        marked_parts.append(_add_diacritic(syl, base))
        digit_parts.append(f"{syl}{ctx}")

    if not marked_parts:
        return None

    return f"{' '.join(marked_parts)} ({' '.join(digit_parts)})"


_KATA_TO_HIRA_OFFSET = 0x30A1 - 0x3041


def _kata_to_hira(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        # Katakana block ァ(0x30A1)–ヶ(0x30F6) -> Hiragana
        if 0x30A1 <= code <= 0x30F6:
            out.append(chr(code - _KATA_TO_HIRA_OFFSET))
        else:
            out.append(ch)
    return ''.join(out)


def ja_pronunciation(lemma: str, tagger) -> str | None:
    """Compute the hiragana reading for a JA lemma via fugashi + UniDic."""
    readings = []
    for word in tagger(lemma):
        feat = word.feature
        # unidic-lite exposes `kana` (katakana surface reading); fall back to
        # `pron` (pronunciation) then the surface itself.
        kana = getattr(feat, 'kana', None) or getattr(feat, 'pron', None)
        readings.append(_kata_to_hira(kana) if kana else word.surface)
    reading = ''.join(readings).strip()
    return reading or None


def fetch_senses(db, language_id: int, force: bool, limit: int) -> list[dict]:
    """Page through dim_word_senses for the given language."""
    rows: list[dict] = []
    start = 0
    while True:
        q = (
            db.table('dim_word_senses')
            .select('id, pronunciation, dim_vocabulary!inner(lemma, language_id)')
            .eq('dim_vocabulary.language_id', language_id)
            .range(start, start + PAGE_SIZE - 1)
        )
        resp = q.execute()
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        start += PAGE_SIZE
        if limit and len(rows) >= limit:
            break

    if not force:
        rows = [r for r in rows if not (r.get('pronunciation') or '').strip()]
    if limit:
        rows = rows[:limit]
    return rows


def main():
    parser = argparse.ArgumentParser(description='Backfill dim_word_senses.pronunciation (deterministic).')
    parser.add_argument('--language', required=True, choices=sorted(LANGUAGE_CODE_TO_ID))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--force', action='store_true', help='Overwrite already-populated rows.')
    args = parser.parse_args()

    language_id = LANGUAGE_CODE_TO_ID[args.language]
    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()
    if db is None:
        raise RuntimeError("Service role client unavailable (set SUPABASE_SERVICE_ROLE_KEY).")

    tagger = None
    if language_id == 3:
        import fugashi
        tagger = fugashi.Tagger()

    senses = fetch_senses(db, language_id, args.force, args.limit)
    logger.info("Fetched %d sense(s) to process (language_id=%d, force=%s)",
                len(senses), language_id, args.force)

    stats = {'updated': 0, 'skipped_empty': 0, 'failed': 0}
    for row in senses:
        sense_id = row['id']
        vocab = row.get('dim_vocabulary') or {}
        lemma = (vocab.get('lemma') or '').strip()
        if not lemma:
            stats['skipped_empty'] += 1
            continue
        try:
            if language_id == 1:
                pron = zh_pronunciation(lemma)
            else:
                pron = ja_pronunciation(lemma, tagger)
        except Exception as e:
            logger.warning("Pronunciation failed for sense %s (%r): %s", sense_id, lemma, e)
            stats['failed'] += 1
            continue

        if not pron:
            logger.warning("Empty pronunciation for sense %s (%r)", sense_id, lemma)
            stats['failed'] += 1
            continue

        if args.dry_run:
            logger.info("[dry-run] sense %s %r -> %s", sense_id, lemma, pron)
            stats['updated'] += 1
            continue

        try:
            db.table('dim_word_senses').update({'pronunciation': pron}).eq('id', sense_id).execute()
            stats['updated'] += 1
        except Exception as e:
            logger.warning("DB update failed for sense %s: %s", sense_id, e)
            stats['failed'] += 1

    logger.info("Done. updated=%d skipped_empty=%d failed=%d",
                stats['updated'], stats['skipped_empty'], stats['failed'])


if __name__ == '__main__':
    main()
