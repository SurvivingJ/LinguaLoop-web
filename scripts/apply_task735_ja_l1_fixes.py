"""TASK-735: stop the ja L1 generator fabricating words, and stop the ja L1
judge killing true minimal pairs.

Two ``prompt_templates`` rows, both Japanese, both LF:

    vocab_prompt2_exercises      [ja]  v1 -> v2 -> v3   (id 184)
    ladder_l1_distractor_judge   [ja]  v2 -> v3         (id 370)

Applied in two rounds. Round 1 (both rows) fixed the prompts; the smoke run
in ``scripts/smoke_task735_ja_l1.py`` then showed the generator scoring 2 of
3 clean distractors per variant — no fabrication left, but still short of the
3 the renderer demands. Round 2 (the vocab row only) added over-generation.
The judge row is final at v3 and is no longer in ROWS.

What was broken (measured, 2026-08-22 canary run ``ja-20260822-232552``)
------------------------------------------------------------------------
Six ``judge_ladder_l1_distractor`` calls, 18 distractors, **17 rejected**.
``exercise_renderer._render_phonetic`` drops the whole variant when fewer than
three distractors survive, so the ja ladder produced **zero** L1 exercises.

Two independent causes, one per row:

1. **The generator invented words.** Sense 34997 (昔/むかし) variant B emitted
   ``向こうし`` and ``無蚊地`` — neither is a word; the model even asserted
   ``無蚊地`` was "an existing word (a place name etc.)". Variant A, which
   happened to answer in kana, invented nothing. The mechanism is orthographic:
   the incumbent prompt says nothing about how to *write* an option, so when the
   model committed to a kanji surface it composed kanji until the reading fitted.
   The incumbent's one anti-fabrication clause ("ディストラクターはすべて実在する
   語で…") is a passive aside in a list of eight bullets, and it did not hold.

2. **The generator and the judge disagreed about pitch accent.** The incumbent
   generator *preferred* ``高低アクセントのみが異なる同音語`` (with 「はし(箸)」↔
   「はし(橋)」 as the model example); the judge rejects exactly those as
   ``完全同音で区別不能``. It is the judge that is right — L1 audio is a single
   TTS rendering, so an accent-only contrast is undecidable for the learner.
   Sense 35001 (機械) lost 機会 to this. The category is now a hard REJECT on
   both sides.

3. **The judge's keep-list was a closed set of four contrast types** — 長短母音,
   清濁, 促音撥音, 高低アクセント — which has no room for the ordinary one-mora
   minimal pair. むかし/むかえ is as clean a minimal pair as Japanese offers and
   the judge killed it with ``最小対立の条件を満たさず``, correctly by its own
   rules. Compare the en row (id 173), whose taxonomy is open: "a homophone /
   near-homophone, a minimal pair differing by one phoneme, or a same-stress
   rhyme". v3 restores the general case and re-points the "when unsure, reject"
   instruction at the question that deserves the doubt — whether the word
   *exists* — rather than at whether one mora of difference counts.

Both rows now state the same doctrine, so a distractor the generator is told to
produce is a distractor the judge is told to keep:

    KEEP   real dictionary headword, differs from the target in exactly one
           mora (vowel, consonant, voicing, length, or gemination)
    REJECT coined, synonym, accent-only, spelling-only, inflection of the
           target, or two-or-more mora away

Why this file rather than a .sql migration
------------------------------------------
Same reason as ``apply_task733_cefr_tier_rewrites.py``: there is no psql in this
environment, so a .sql file records intent that nothing executes. Rows are
versioned, never overwritten — the incumbent is deactivated and a new
``max(version)+1`` row is inserted, so rollback is one ``is_active`` flip.

Three checks run before anything is written and again afterwards:

1. **Substitution fired.** Each row carries ``must_go`` / ``must_have`` token
   lists. A ``must_go`` still present in the incumbent but absent from the draft
   proves the rewrite targeted the live text; a ``must_go`` that was never in the
   incumbent means the row drifted since it was read, and we abort rather than
   write a no-op version bump.
2. **Parser contract intact.** The two rows are rendered by *different* engines
   and only one of them treats braces as syntax — see ``RENDERERS`` below. Each
   draft is checked against its own engine.
3. **Line endings preserved.** Both incumbents are LF today; the convention is
   detected per row and reapplied rather than assumed.

Usage::

    python scripts/apply_task735_ja_l1_fixes.py --dry-run   # show the plan
    python scripts/apply_task735_ja_l1_fixes.py             # write, verify
    python scripts/apply_task735_ja_l1_fixes.py --verify    # verify only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFTS = os.path.join(ROOT, 'data', 'eval', 'task735')

LANG_ID = {'zh': 1, 'en': 2, 'ja': 3}

# How each row's template is turned into a prompt. This is not cosmetic: it
# decides whether a literal JSON brace in the text is data or syntax.
#
#   'renderer' -> asset_generators/_renderer.render_template, which substitutes
#                 only {bare_identifier} and leaves every other brace alone. A
#                 JSON example must therefore use SINGLE braces; doubling them
#                 would put literal {{ }} in the prompt.
#   'format'   -> str.format at judges/l1_distractor.py:79. Every literal brace
#                 must be DOUBLED or the call raises. This is the trap that
#                 killed ja exercise_sentence_generation under TASK-733.
RENDERERS = {
    'vocab_prompt2_exercises': 'renderer',
    'ladder_l1_distractor_judge': 'format',
}

# Placeholders each caller actually supplies. A draft may use a subset; anything
# outside the set raises at generation time (KeyError from either engine).
CALLER_ARGS = {
    # asset_generators/prompt2_exercises.py:_build_prompt
    'vocab_prompt2_exercises': {
        'word', 'pos', 'semantic_class', 'complexity_tier', 'definition',
        'primary_collocate', 'register', 'sense_fingerprint', 'sentences_json',
        'active_levels_json', 'used_distractors_json',
        'level_3_sentence_index', 'level_5_sentence_index',
        'level_6_sentence_index',
    },
    # judges/l1_distractor.py:79
    'ladder_l1_distractor_judge': {'target', 'distractors_numbered'},
}

# A CEFR band token, CJK-safe. Do NOT use \b: CJK codepoints are \w in Python,
# so \bCEFR\b never matches "CEFRレベル". Carried over from TASK-733 so a
# reintroduction cannot slip in through these rows.
CEFR_RE = re.compile(r'(?<![A-Za-z0-9])(?:CEFR|[ABC][12])(?![A-Za-z0-9])')

# (draft_file, task_name, lang, model, provider, must_go, must_have, description)
ROWS = [
    ('vocab_prompt2_exercises_ja.txt', 'vocab_prompt2_exercises', 'ja',
     'qwen/qwen3.7-plus', 'openrouter',
     # Present in live v1, must be gone from the draft.
     ['高低アクセントのみが異なる同音語',
      '「はし(箸)」↔「はし(橋)」',
      '「かす」↔「がす」',
      'ディストラクターはすべて実在する語で、対象語の同義語であってはならない。',
      '4 つの選択肢を返す。1 つが正解 = 対象語、3 つがディストラクター。',
      'L1 / L3 / L5 の値は 4 つの選択肢オブジェクト配列：',
      '6 つの選択肢を返す',
      'L1 の値は 6 つの選択肢オブジェクト配列：'],
     # Must be present in the draft.
     ['関門 1（実在性）',
      '国語辞典に見出し語として載っている語だけを使う',
      '「向こうし」「無蚊地」「無蚊」「むかけ」「むかっ」のような造語はすべて禁止',
      '関門 2（表記）',
      '対象語の字種（漢字／かな）に揃えるために表記を作り替えてはならない',
      'モーラ単位で「一箇所だけ」異なる',
      '「むかし」↔「むかえ」',
      '高低アクセントだけが異なる語も、同じ理由で不可',
      '対象語の活用形',
      '出力前の最終点検',
      'ディストラクターは 3 つ以上 5 つ以下',
      'ディストラクターの探し方（この手順で探すこと）',
      '数を満たすために語を作ることは、最も重い違反である',
      'L1 の値は 4〜6 個の選択肢オブジェクト配列：'],
     'v2 (TASK-735): L1 section only — L3/L5/L6 and the shared rules are byte '
     'identical to v1. Adds an explicit attestation gate (dictionary headword; '
     'state the reading and meaning before writing the explanation; no coined '
     'kanji compounds, naming 向こうし/無蚊地 as the observed failures), an '
     'orthography rule (never manufacture a spelling to match the target script '
     '— the mechanism behind both fabrications), and a one-mora contrast rule. '
     'Pitch-accent-only pairs move from PREFERRED to FORBIDDEN, matching the '
     'judge: L1 audio is one TTS rendering, so accent alone is undecidable. '
     'Finally, L1 over-generates: 6 options (1 correct + 5 distractors) instead '
     'of 4, because the renderer drops the whole variant below 3 surviving '
     'distractors and 3-for-3 is not a rate an LLM holds. Paired with '
     'validators.OPTION_COUNTS[1] = (4, 8); the learner still sees 4.'),

    # ROUND 1 also rewrote ladder_l1_distractor_judge [ja] v2 -> v3
    # (md5 f6f1eef85addbd42b6acdafe8c0a3a2f, draft
    # data/eval/task735/ladder_l1_distractor_judge_ja.txt). v3 is final: it
    # opened the keep-list to the general one-mora minimal pair (v2 rejected
    # むかし/むかえ as 最小対立の条件を満たさず, correctly by its own closed set of
    # four contrast types), made pitch-accent-only pairs an explicit reject
    # (v2 listed them as keep AND as reject, and the model settled that by
    # killing 機会/機械), and re-pointed the blanket "when unsure, reject" at
    # whether the word EXISTS. Round 2 does not touch it, so it is out of
    # ROWS — re-adding it would fail pre-flight as a no-op, which is correct.
]


def md5(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def read_draft(filename: str) -> str:
    """Read a draft as LF-normalised text; EOL is reapplied per row later."""
    with open(os.path.join(DRAFTS, filename), encoding='utf-8', newline='') as handle:
        return handle.read().replace('\r\n', '\n')


def detect_eol(text: str) -> str:
    """Return the incumbent row's line-ending convention (LF if none)."""
    return '\r\n' if '\r\n' in text else '\n'


def placeholders(text: str, engine: str) -> set[str]:
    """Placeholder names the given engine would try to substitute."""
    if engine == 'renderer':
        # Mirrors _renderer._PLACEHOLDER_RE exactly.
        return set(re.findall(r'\{([A-Za-z_][A-Za-z0-9_]*)\}', text))
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


def fetch(db, task: str, lang_id: int) -> list[dict]:
    return (db.table('prompt_templates')
              .select('id, version, is_active, template_text, model, provider')
              .eq('task_name', task)
              .eq('language_id', lang_id)
              .order('version')
              .execute().data)


def check_row(task, draft_lf, incumbent, must_go, must_have,
              for_write: bool = True) -> list[str]:
    """Assertions on a draft. Returns a list of problems; empty means go.

    ``for_write`` gates the drift check only. Before writing, every ``must_go``
    token must still be present in the incumbent — that is what proves the
    rewrite targets the live text rather than bumping a version that already
    changed. After writing the incumbent IS the new row, so those tokens are
    legitimately gone; --verify passes for_write=False. Everything else applies
    in both modes.
    """
    problems = []
    inc = incumbent['template_text']
    engine = RENDERERS[task]

    # 1. The substitution must actually fire against the LIVE text.
    #
    # ``must_go`` records everything this task has had to remove across ALL its
    # rounds, so after round 1 lands some entries are legitimately already gone.
    # Requiring every one of them to still be present would make the script
    # un-rerunnable; requiring none of them would let a blind no-op version bump
    # through. The guarantee that actually matters is that this draft edits the
    # row as it stands now, so: at least one must_go token must still be live.
    still_live = [t for t in must_go if t in inc]
    if for_write and must_go and not still_live:
        problems.append(
            f'NO-OP: not one must_go token is present in the live v'
            f'{incumbent["version"]} row — this draft changes nothing that is '
            f'actually there. Re-read the row before writing.')
    for token in must_go:
        if token in draft_lf:
            problems.append(f'NO-OP: must_go token {token!r} survives in the draft.')
    for token in must_have:
        if token not in draft_lf:
            problems.append(f'MISSING: must_have token {token!r} absent from the draft.')

    # 2. No CEFR token may reappear (TASK-733 removed them project-wide).
    leftover = CEFR_RE.findall(draft_lf)
    if leftover:
        problems.append(f'CEFR tokens in the draft: {sorted(set(leftover))}')

    # 3. Parser contract: no placeholder the caller does not supply.
    allowed = CALLER_ARGS[task]
    unknown = placeholders(draft_lf, engine) - allowed
    if unknown:
        problems.append(
            f'placeholder(s) {sorted(unknown)} are not supplied by the caller '
            f'(allowed: {sorted(allowed)}) — a KeyError at generation time.')

    # 4. Render the draft the way its own engine will, with dummy args. For the
    #    'format' row this is also the brace-balance check; for the 'renderer'
    #    row single braces are data and must survive untouched.
    #    Counting braces in the output cannot work — a nested JSON example ends
    #    in a legitimate '}}'. Parse the rendered examples instead: that is the
    #    contract the model is being shown.
    dummy = {k: f'<{k}>' for k in allowed}
    try:
        if engine == 'format':
            rendered = draft_lf.format(**dummy)
            examples = [ln.strip() for ln in rendered.splitlines()
                        if ln.strip().startswith('{') and ln.strip().endswith('}')]
            if not examples:
                problems.append('no JSON example line survives rendering — the '
                                'judge prompt must show its output shape.')
            for line in examples:
                try:
                    json.loads(line)
                except ValueError as exc:
                    problems.append(f'rendered JSON example is not parseable '
                                    f'({exc}): {line[:80]}')
        else:
            from services.vocabulary_ladder.asset_generators._renderer import (
                render_template,
            )
            rendered = render_template(draft_lf, **dummy)
            if '{{' in rendered:
                problems.append(
                    'draft contains {{ }} but render_template does not unescape '
                    'them — the model would see literal doubled braces.')
    except Exception as exc:  # noqa: BLE001 - any render failure is fatal here
        problems.append(f'draft fails to render ({engine}): '
                        f'{type(exc).__name__}: {exc}')

    # 5. Row-specific: the ja L1 doctrine must agree across the two rows.
    #    Both must forbid accent-only pairs, or the generator will keep emitting
    #    what the judge keeps killing — the 機会/機械 failure.
    if 'アクセント' in draft_lf and 'アクセントだけが異なる' not in draft_lf:
        problems.append(
            'draft mentions アクセント but never forbids accent-only pairs — '
            'that is the generator/judge contradiction this task closes.')

    return problems


def plan(db, for_write: bool = True):
    """Build the plan, running every check. Aborts on any problem.

    With for_write False (--verify) the target version is the row active NOW
    rather than max(version)+1, so verification reads back what was written
    instead of proposing a further bump.
    """
    jobs, problems = [], []
    for (fname, task, lang, model, provider, must_go, must_have, desc) in ROWS:
        lang_id = LANG_ID[lang]
        rows = fetch(db, task, lang_id)
        if not rows:
            problems.append(f'{task} [{lang}]: no rows at all.')
            continue
        active = [r for r in rows if r['is_active']]
        if len(active) != 1:
            problems.append(f'{task} [{lang}]: {len(active)} active rows, expected 1.')
            continue
        incumbent = active[0]

        draft_lf = read_draft(fname)
        problems.extend(
            f'{task} [{lang}]: {p}' for p in
            check_row(task, draft_lf, incumbent, must_go, must_have, for_write)
        )

        eol = detect_eol(incumbent['template_text'])
        body = draft_lf.replace('\n', eol) if eol == '\r\n' else draft_lf
        new_version = (max(r['version'] for r in rows) + 1) if for_write \
            else incumbent['version']

        jobs.append({
            'task': task, 'lang': lang, 'lang_id': lang_id,
            'incumbent_id': incumbent['id'],
            'incumbent_version': incumbent['version'],
            'version': new_version, 'model': model, 'provider': provider,
            'body': body, 'description': desc,
            'eol': 'CRLF' if eol == '\r\n' else 'LF',
            'model_was': incumbent['model'],
        })
    return jobs, problems


def apply(db, jobs, dry_run: bool) -> None:
    for job in jobs:
        note = f'  [model {job["model_was"]} -> {job["model"]}]' \
            if job['model_was'] != job['model'] else ''
        print(f'  {job["task"]:<28} {job["lang"]} '
              f'v{job["incumbent_version"]} -> v{job["version"]}  '
              f'{job["eol"]:<4} {len(job["body"]):>5} chars  '
              f'md5 {md5(job["body"])}{note}')
        if dry_run:
            continue

        (db.table('prompt_templates')
           .update({'is_active': False})
           .eq('task_name', job['task'])
           .eq('language_id', job['lang_id'])
           .execute())

        (db.table('prompt_templates')
           .upsert({
               'task_name': job['task'],
               'language_id': job['lang_id'],
               'version': job['version'],
               'is_active': True,
               'model': job['model'],
               'provider': job['provider'],
               'template_text': job['body'],
               'description': job['description'],
           }, on_conflict='task_name,language_id,version')
           .execute())


def verify(db, jobs) -> int:
    problems = 0
    print(f'\n{"task_name":<28} {"lg":<3} {"v":<4} {"active":<7} {"md5":<6} {"eol":<5} rows')
    print('-' * 78)
    for job in jobs:
        rows = fetch(db, job['task'], job['lang_id'])
        target = next((r for r in rows if r['version'] == job['version']), None)
        if target is None:
            print(f'{job["task"]:<28} {job["lang"]:<3} MISSING v{job["version"]}')
            problems += 1
            continue

        stored = target['template_text']
        matches = md5(stored) == md5(job['body'])
        eol_ok = detect_eol(stored) == ('\r\n' if job['eol'] == 'CRLF' else '\n')
        active_count = sum(1 for r in rows if r['is_active'])

        flags = []
        if not matches:
            flags.append('MD5-MISMATCH')
        if not eol_ok:
            flags.append('EOL-DRIFT')
        if not target['is_active']:
            flags.append('NOT-ACTIVE')
        if active_count != 1:
            flags.append(f'{active_count}-ACTIVE')
        if not target['model'] or not target['provider']:
            flags.append('NULL-MODEL')
        problems += len(flags)

        print(f'{job["task"]:<28} {job["lang"]:<3} v{job["version"]:<3} '
              f'{str(target["is_active"]):<7} '
              f'{"ok" if matches else "BAD":<6} '
              f'{job["eol"]:<5} {len(rows)}  {" ".join(flags)}')
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true',
                        help='show the plan, write nothing')
    parser.add_argument('--verify', action='store_true',
                        help='verify only, write nothing')
    args = parser.parse_args()

    # Every line this script prints carries CJK or box-drawing characters, and
    # the default Windows console codepage is cp1252 — printing the plan would
    # die on UnicodeEncodeError before writing anything.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    jobs, problems = plan(db, for_write=not args.verify)
    if problems:
        print('PRE-FLIGHT FAILED — nothing written:\n')
        for p in problems:
            print(f'  ! {p}')
        return 1

    print(f'\n── plan ({len(jobs)} rows) ' + '─' * 40)
    if not args.verify:
        apply(db, jobs, dry_run=args.dry_run)
    if args.dry_run:
        print('\ndry run — nothing written.')
        return 0

    failures = verify(db, jobs)
    if failures:
        print(f'\nVERIFY FAILED: {failures} problem(s).')
        return 1
    print('\nverified: every row stored byte-for-byte, exactly one active per task.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
