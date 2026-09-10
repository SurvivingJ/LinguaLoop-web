#!/usr/bin/env python3
"""TASK-757 — find dictionary rows whose definition does not define the headword.

The defect
----------
Some `dim_word_senses` rows carry the definition of a longer phrase but are stored
under the bare lemma. Sense 14968 is lemma `hand` defined as "Closely connected or
associated with something else" — that defines *hand in hand*. Calibration then
builds a perfectly well-formed item whose correct answer does not describe the
prompt, and no distractor picker can rescue it: the key itself is wrong.

Why this needs a model rather than a rule
-----------------------------------------
The signal is semantic. The embeddings cannot see it, because every sense is
embedded as "{lemma}: {definition}" — the lemma is *inside* the vector, so a
mis-keyed definition still sits near its own headword. A string rule cannot see it
either: nothing about the characters of "hand" and "closely connected or
associated with something else" is anomalous. What is wrong is only visible to
something that knows what the words mean.

Precision over recall, deliberately
-----------------------------------
A false positive removes a usable word from Calibration; a false negative leaves
one broken item in a pool of thousands. Neither is severe, but the screen is asked
to flag only clear cases and to say what the definition *does* define, which makes
every flag checkable by eye rather than taken on trust.

Usage::

    # validate the prompt on a small sample first, writing nothing
    PYTHONIOENCODING=utf-8 python -m scripts.screen_sense_definition_mismatch \
        --language 2 --limit 200 --dry-run

    # full English sweep, writing flags to calibration_anchor_blocklist
    PYTHONIOENCODING=utf-8 python -m scripts.screen_sense_definition_mismatch --language 2

    # rate check on the CJK languages
    PYTHONIOENCODING=utf-8 python -m scripts.screen_sense_definition_mismatch \
        --language 1 --limit 400 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

LANG_NAME = {1: 'Chinese', 2: 'English', 3: 'Japanese'}

#: gemini-flash-lite rather than a qwen slug: the qwen model ids in this project
#: have been delisted from OpenRouter more than once, and a 404 here would fail
#: the whole sweep silently at the batch level.
MODEL = 'google/gemini-3.5-flash-lite'

#: Items per call. Large enough that the ~6.5k English sweep is a few hundred
#: calls, small enough that one malformed response loses little work.
BATCH = 20

SYSTEM = (
    "You audit bilingual dictionary entries. You are precise, conservative, and "
    "you never flag an entry merely for being loosely or informally worded."
)

PROMPT_TEMPLATE = """Each item below is a dictionary entry: a HEADWORD and the DEFINITION stored against it.

Decide, for each item, whether the definition actually defines that headword.

Verdicts:
  "ok"      - the definition defines the headword, even if loosely or informally worded.
  "phrase"  - the definition defines a LONGER PHRASE OR IDIOM that contains the headword,
              not the headword on its own.
  "other"   - the definition defines a different word entirely, or the wrong part of speech.

Worked example of "phrase":
  HEADWORD: hand
  DEFINITION: Closely connected or associated with something else.
  -> This defines the idiom "hand in hand", not "hand". verdict "phrase",
     actually_defines "hand in hand".

Be conservative. A broad, vague or simplified definition is still "ok" if it fits the
headword. Only flag an entry when the definition clearly belongs to something else.
A definition that lists several senses of the headword is "ok".

CRITICAL - these are all "ok", not mismatches:
  - A different INFLECTION or PART OF SPEECH of the headword. "tending" defined as
    "likely to behave in a particular way" is "ok" (that is the verb "tend").
    "dry" defined as "removing water from something" is "ok" (the verb sense).
  - A definition of the headword's noun sense when the headword could also be a verb,
    or vice versa. "associate" defined as "a person you work with" is "ok".
  If the thing the definition really defines IS the headword in another form, the
  verdict is "ok" and actually_defines must be empty.

Use "phrase" only when the definition belongs to a MULTI-WORD expression containing
the headword. Use "other" only when it belongs to a genuinely DIFFERENT word.

The headwords are in {language}.

Return ONLY a JSON object, one key per item, no commentary:
{{"item_1": {{"verdict": "ok|phrase|other", "actually_defines": "<the thing it really defines, or empty if ok>"}}, ...}}

Items:
{items}"""


def _norm(text: str) -> str:
    """Lowercase, drop parentheticals and punctuation, collapse whitespace."""
    cleaned = re.sub(r'\(.*?\)', ' ', text or '')
    cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
    return ' '.join(cleaned.lower().split())


def _shared_prefix(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def is_self_reference(lemma: str, actually_defines: str) -> bool:
    """True when the model says the definition defines the headword itself.

    The first sweep's false positives all had this shape: `associate` flagged as
    defining "associate (noun)", `tending` as defining "tend", `dry` as defining
    "drying". Every one is an inflection or part-of-speech reading of the same
    word, which is not the defect being hunted, and the model's own
    `actually_defines` gives it away — so the check is exact rather than a guess.

    Compares whole normalised strings, NOT leading tokens. A first-token
    comparison suppressed `hand` -> "hand in hand", which is precisely the TRUE
    positive this screen exists to find, and `call export` -> "call", which is a
    genuine mismatch in the other direction. A multi-word target is therefore
    never self-reference: more words than the headword is the phrase case, fewer
    is a different word.
    """
    lemma_norm = _norm(lemma)
    target = _norm(actually_defines)
    if not target or not lemma_norm:
        return False
    if target == lemma_norm:
        return True
    # Single-word headword and single-word target: an inflectional variant shares
    # a stem covering most of the shorter form (tend/tending, dry/drying).
    if ' ' not in lemma_norm and ' ' not in target:
        shortest = min(len(target), len(lemma_norm))
        if shortest >= 3:
            common = _shared_prefix(target, lemma_norm)
            return common >= 3 and common >= 0.6 * shortest
    return False


def blocklist_tokenizer_artifacts(db, language_id: int, dry_run: bool) -> int:
    """Blocklist CJK lemmas that are morpheme sequences rather than words.

    Found while rate-checking Japanese: 91 of 3,607 ja lemmas (2.5%) contain a
    SPACE — `作る れる ます`, `啄む ます た`, `びっくり 為る ます た`. These are
    MeCab tokenizer output stored as a lemma: a verb plus its inflectional
    suffixes, split into morphemes and rejoined with spaces. The definitions are
    usually fine; the headword is garbage, so the item is unanswerable no matter
    how good the distractors are.

    This is a RULE, not a model call, and the rule is exact rather than heuristic:
    Japanese and Chinese orthography do not use spaces between words, so a space
    in a zh/ja lemma cannot be part of the word. Measured: zh has 0 such lemmas,
    ja has 91. English is excluded because multi-word English lemmas are ordinary
    ("go on"), not artifacts.

    Fixing `dim_vocabulary.lemma` upstream is the real repair; this only keeps the
    rows out of Calibration.
    """
    if language_id not in (1, 3):
        print('tokenizer-artifact rule applies to zh/ja only '
              '(spaces are meaningful in English lemmas)')
        return 0

    rows, offset = [], 0
    while True:
        page = (db.table('dim_word_senses')
                .select('id, dim_vocabulary!inner(lemma)')
                .eq('word_language_id', language_id)
                .eq('definition_level', 'standard')
                .order('id')
                .range(offset, offset + 999)
                .execute().data) or []
        rows += page
        if len(page) < 1000:
            break
        offset += 1000

    bad = [r for r in rows
           if ' ' in ((r.get('dim_vocabulary') or {}).get('lemma') or '').strip()]
    lemmas = sorted({r['dim_vocabulary']['lemma'] for r in bad})
    print(f'{LANG_NAME[language_id]}: {len(bad)} senses across {len(lemmas)} '
          f'space-containing lemmas (of {len(rows)} senses)')
    for lemma in lemmas[:12]:
        print(f'    {lemma!r}')

    if dry_run or not bad:
        print('Nothing written (dry run or nothing found).')
        return 0

    payload = [{
        'sense_id': r['id'],
        'reason': ("TASK-757 tokenizer-artifact rule: lemma "
                   f"{r['dim_vocabulary']['lemma']!r} contains a space, which is "
                   "impossible in a real zh/ja word - it is MeCab morpheme output "
                   "stored as a lemma, so the prompt word itself is malformed."),
    } for r in bad]

    written = 0
    for i in range(0, len(payload), 200):
        chunk = payload[i:i + 200]
        try:
            db.table('calibration_anchor_blocklist')               .upsert(chunk, on_conflict='sense_id').execute()
            written += len(chunk)
        except Exception as exc:
            print(f'  write failed at {i}: {str(exc)[:120]}')
    print(f'blocklisted {written} senses')
    return written


def fetch_senses(db, language_id: int, limit: int | None):
    """Standard-level senses of one language, paged past PostgREST's 1000 cap."""
    rows, offset = [], 0
    while True:
        page = (db.table('dim_word_senses')
                .select('id, definition, dim_vocabulary!inner(lemma)')
                .eq('word_language_id', language_id)
                .eq('definition_language_id', language_id)
                .eq('definition_level', 'standard')
                .order('id')
                .range(offset, offset + 999)
                .execute().data) or []
        rows += page
        if len(page) < 1000 or (limit and len(rows) >= limit):
            break
        offset += 1000
    if limit:
        rows = rows[:limit]
    return [r for r in rows
            if (r.get('definition') or '').strip()
            and ((r.get('dim_vocabulary') or {}).get('lemma') or '').strip()]


def screen_batch(call_llm, batch, language_id: int) -> dict:
    """One LLM call over up to BATCH entries. Returns {index: verdict dict}."""
    lines = []
    for i, row in enumerate(batch, start=1):
        lemma = row['dim_vocabulary']['lemma'].strip()
        definition = ' '.join((row['definition'] or '').split())
        lines.append(f'item_{i}:\n  HEADWORD: {lemma}\n  DEFINITION: {definition}')

    prompt = PROMPT_TEMPLATE.format(
        language=LANG_NAME.get(language_id, 'the target language'),
        items='\n'.join(lines))

    result = call_llm(
        prompt,
        model=MODEL,
        system_prompt=SYSTEM,
        temperature=0.0,
        response_format='json',
        max_tokens=4000,
        pipeline='calibration',
        task_name='screen_sense_definition_mismatch',
        language_code={1: 'zh', 2: 'en', 3: 'ja'}.get(language_id),
    )
    return result if isinstance(result, dict) else {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--language', type=int, required=True, choices=[1, 2, 3])
    ap.add_argument('--limit', type=int, default=None)
    ap.add_argument('--batch', type=int, default=BATCH)
    ap.add_argument('--dry-run', action='store_true',
                    help='screen and report, but write no blocklist rows')
    ap.add_argument('--out', default=None)
    ap.add_argument('--tokenizer-artifacts', action='store_true',
                    help='rule-based pass for zh/ja lemmas containing a space '
                         '(MeCab morpheme sequences); no LLM calls')
    args = ap.parse_args()

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    from services.llm_service import call_llm
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    if args.tokenizer_artifacts:
        blocklist_tokenizer_artifacts(db, args.language, args.dry_run)
        return

    senses = fetch_senses(db, args.language, args.limit)
    print(f'{LANG_NAME[args.language]}: screening {len(senses)} senses '
          f'in {(len(senses) + args.batch - 1) // args.batch} calls'
          + (' (dry run)' if args.dry_run else ''))

    flagged, errors, checked, self_refs = [], 0, 0, 0
    started = time.time()

    for start in range(0, len(senses), args.batch):
        batch = senses[start:start + args.batch]
        try:
            verdicts = screen_batch(call_llm, batch, args.language)
        except Exception as exc:
            errors += 1
            print(f'  batch at {start}: FAILED ({str(exc)[:90]})')
            continue

        for i, row in enumerate(batch, start=1):
            v = verdicts.get(f'item_{i}')
            if not isinstance(v, dict):
                continue
            checked += 1
            verdict = str(v.get('verdict', 'ok')).strip().lower()
            defines = str(v.get('actually_defines', '') or '')
            if verdict in ('phrase', 'other') and is_self_reference(
                    row['dim_vocabulary']['lemma'], defines):
                self_refs += 1
                continue
            if verdict in ('phrase', 'other'):
                flagged.append({
                    'sense_id': row['id'],
                    'lemma': row['dim_vocabulary']['lemma'],
                    'definition': row['definition'],
                    'verdict': verdict,
                    'actually_defines': str(v.get('actually_defines', ''))[:200],
                })

        done = start + len(batch)
        if done % (args.batch * 25) == 0 or done >= len(senses):
            rate = len(flagged) / checked if checked else 0
            print(f'  {done}/{len(senses)}  flagged={len(flagged)} ({rate:.1%})  '
                  f'{time.time() - started:.0f}s')

    rate = len(flagged) / checked if checked else 0.0
    print(f'\nchecked={checked}  flagged={len(flagged)} ({rate:.2%})  '
          f'suppressed_self_reference={self_refs}  failed_batches={errors}')

    # data/calibration/, not the repo root: these are the input to an upstream
    # dictionary repair, not scratch output.
    code = {1: 'zh', 2: 'en', 3: 'ja'}[args.language]
    default_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data', 'calibration')
    os.makedirs(default_dir, exist_ok=True)
    out = args.out or os.path.join(default_dir, f'sense_mismatch_{code}.json')
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(flagged, fh, ensure_ascii=False, indent=2)
    print(f'wrote {out}')

    for f in flagged[:15]:
        print(f"  [{f['sense_id']}] {f['lemma']} ({f['verdict']}) "
              f"-> {f['actually_defines']}\n      {f['definition'][:110]}")

    if args.dry_run or not flagged:
        print('\nNothing written (dry run or no flags).')
        return

    # Blocklist rows keep these out of Calibration immediately. It is NOT a fix:
    # the dictionary is still wrong for every other consumer (flashcards,
    # practice, exercise generation), which is why the flags are also written to
    # the JSON file above for an upstream repair pass.
    payload = [{
        'sense_id': f['sense_id'],
        'reason': (f"TASK-757 automated screen ({MODEL}): definition does not define "
                   f"the headword; verdict={f['verdict']}"
                   + (f", actually defines {f['actually_defines']!r}"
                      if f['actually_defines'] else '')),
    } for f in flagged]

    written = 0
    for i in range(0, len(payload), 200):
        chunk = payload[i:i + 200]
        try:
            db.table('calibration_anchor_blocklist') \
              .upsert(chunk, on_conflict='sense_id').execute()
            written += len(chunk)
        except Exception as exc:
            print(f'  blocklist write failed at {i}: {str(exc)[:120]}')
    print(f'blocklisted {written} senses')


if __name__ == '__main__':
    main()
