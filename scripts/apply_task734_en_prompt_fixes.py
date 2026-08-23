"""TASK-734: fix the remaining English ``prompt_templates`` rows.

Two defect families, both English-only. No OpenRouter calls are made — English
needs no native-review loop, so the drafts in ``data/eval/task734/`` are
authored and accepted directly.

1. **The "reads naturally" inversion** (``cloze_distractor_generation`` en v2).
   The row's own hard rule 2 requires every distractor to be *grammatically
   valid in the blank slot* — which is exactly what makes it read naturally.
   The closing self-check then said "If any reads naturally, replace it",
   telling the model to discard the distractors that satisfy rules 1-2 and keep
   the surface-clunky ones a learner eliminates on sight. The property that
   should disqualify a distractor is reading *correctly*, not reading
   *smoothly*. zh/ja were corrected under TASK-733 (「文脈上で正解として自然に
   読める」/「在该语境中读起来正确或可接用」); en was out of that pass's scope.

2. **CEFR labels over tier codes** (Group A of the TASK-733 brief). Three rows
   print ``CEFR Level: {complexity_tier}`` while every caller injects a T-code
   (``persona_designer``/``scenario_planner`` via the conversation orchestrator,
   ``plot_architect`` via the mystery orchestrator). The model literally reads
   "CEFR Level: T4" — a label that is wrong and a value it cannot interpret.
   Each row gets the age-tier label plus an inline legend, so the injected
   T-code resolves. The legend text is ``build_tier_legend(2)`` verbatim, so
   there is exactly one English tier legend in the estate and these rows can
   later switch to a ``{tier_legend}`` placeholder without the text changing.

Plus one deactivation and one code fix, both recorded here so the task is
auditable from a single file:

* ``scenario_batch_generation`` en **v2** (id 117) is still ``is_active`` next to
  a v3 that is already CEFR-free and tier-based. Both loaders on this path
  (``prompt_service.get_template_text`` and ``conversation_generation.
  database_client.get_prompt_template``) order by ``version`` desc and take one
  row, so v3 already wins and deactivating v2 changes no behaviour — it only
  stops a dead CEFR row being served if a future loader filters on
  ``is_active`` alone. Handled as DEACTIVATE, not a rewrite.
* ``services/mystery_generation/orchestrator.py`` defaulted ``complexity_tier``
  to the CEFR band ``'B1'`` when a difficulty fell outside 1-9, which would
  inject a value the new legend cannot resolve. Changed to ``'T3'`` by hand;
  ``--verify`` asserts it.

Conventions carried over from ``apply_task733_cefr_tier_rewrites.py`` and
``apply_prompt_rewrites.py``:

* **Version, never overwrite.** The incumbent is deactivated and a new
  ``max(version)+1`` row inserted, so rollback is one ``is_active`` flip.
* **Assert each substitution fired.** Every row carries ``must_go`` /
  ``must_have`` tokens. A ``must_go`` string missing from the incumbent means
  the row drifted since it was read and the edit's premise no longer holds —
  abort rather than write a no-op version bump.
* **Parser contract intact.** ``str.format`` placeholders in the draft are
  checked against what the caller actually supplies; anything outside that set
  is a ``KeyError`` at generation time. JSON keys and the five distractor enum
  values stay verbatim English (``validators.py:149`` parses them).
* **Line endings and trailing newline are per-row.** All four incumbents here
  are CRLF with no trailing newline; the drafts on disk are LF. Each row's
  incumbent convention is detected and reapplied rather than assumed.

Usage::

    python scripts/apply_task734_en_prompt_fixes.py --dry-run   # show the plan
    python scripts/apply_task734_en_prompt_fixes.py             # write, verify
    python scripts/apply_task734_en_prompt_fixes.py --verify    # verify only
"""

from __future__ import annotations

import argparse
import os
import re
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFTS = os.path.join(ROOT, 'data', 'eval', 'task734')

EN = 2  # language_id

# A CEFR band token. Same CJK-safe form as task733 so the two scripts agree.
CEFR_RE = re.compile(r'(?<![A-Za-z0-9])(?:CEFR|[ABC][12])(?![A-Za-z0-9])')

# Placeholders each caller actually supplies. A draft may use a subset; using
# anything outside the set raises KeyError at generation time.
CALLER_ARGS = {
    # services/exercise_generation/generators/cloze.py:_generate_distractors
    'cloze_distractor_generation': {'original_sentence', 'sentence_with_blank',
                                    'correct_answer', 'complexity_tier'},
    # services/conversation_generation/agents/persona_designer.py:design_persona
    'conversation_persona_design': {'language_name', 'domain_name', 'register',
                                    'complexity_tier'},
    # services/conversation_generation/agents/scenario_planner.py:plan_scenario
    'conversation_scenario_plan': {'language_name', 'domain_name',
                                   'domain_description', 'persona_a_summary',
                                   'persona_b_summary', 'relationship_type',
                                   'register', 'complexity_tier'},
    # services/mystery_generation/agents/plot_architect.py:121
    'mystery_plot': {'language_name', 'complexity_tier', 'archetype',
                     'target_vocab'},
}

# The five-dimension closed taxonomy — wiki/features/exercise-generation-prompts.md:570.
# Parser contract: services/exercise_generation/validators.py:149.
CLOZE_TAGS = ('semantic', 'collocational', 'aspectual', 'register', 'valency')

# The canonical English tier legend, from build_tier_legend(2). Every rewritten
# row must carry the T1 and T6 anchors so a partial paste fails the check.
TIER_ANCHORS = ['T1 = The Toddler (Age 4-5)',
                'T6 = The Educated Professional (Age 30+)']

# (draft_file, task_name, model, provider, must_go, must_have, description)
ROWS = [
    ('cloze_distractor_generation_en.txt', 'cloze_distractor_generation',
     'google/gemini-3.5-flash-lite', 'openrouter',
     ['If any reads naturally, replace it before emitting.',
      'Put the correct answer first in any option lists',
      'assign exactly one reason it fails here',
      'no near-identical wrong-but-similar set'],
     ['Reading smoothly is EXPECTED',
      'reads as a correct or acceptable answer in this context',
      'If you produce an option list separately',
      'T1 = The Toddler (Age 4-5)',
      '"distractors"', '"distractor_tags"', '"explanation"'],
     'v3 (TASK-734): the closing self-check no longer tells the model to '
     'discard distractors for reading smoothly — only for reading as a '
     'correct answer. Option-list line made conditional (the JSON schema '
     'emits distractors only). Learner tier legend added so the injected '
     'T-code resolves.'),

    ('conversation_persona_design_en.txt', 'conversation_persona_design',
     'google/gemini-3.5-flash-lite', 'openrouter',
     ['CEFR Level: {complexity_tier}'],
     ['Learner level: {complexity_tier}', 'Complexity tier reference:',
      "The persona's speaking_style and system_prompt must be consistent"],
     'v2 (TASK-734): CEFR label replaced by the age-tier label the caller '
     'actually injects, plus the canonical English tier legend and an '
     'instruction making the tier load-bearing on speaking_style.'),

    ('conversation_scenario_plan_en.txt', 'conversation_scenario_plan',
     'google/gemini-3.5-flash-lite', 'openrouter',
     ['CEFR Level: {complexity_tier}'],
     ['Learner level: {complexity_tier}', 'Complexity tier reference:',
      'The keywords and the context_description must sit at the learner level'],
     'v2 (TASK-734): CEFR label replaced by the age-tier label plus legend; '
     'keywords/context_description explicitly bound to the tier.'),

    ('mystery_plot_en.txt', 'mystery_plot',
     'anthropic/claude-sonnet-5', 'openrouter',
     ['- CEFR Level: {complexity_tier}'],
     ['- Complexity tier: {complexity_tier}', 'Complexity tier reference:',
      "Every scene's prose must sit at the complexity tier above."],
     'v2 (TASK-734): CEFR label replaced by "Complexity tier", matching the '
     "code fallback plot_architect.DEFAULT_USER_PROMPT, plus the legend."),
]

# (task_name, version, reason) — rows to deactivate without rewriting.
DEACTIVATE = [
    ('scenario_batch_generation', 2,
     'superseded by the CEFR-free v3; both loaders already serve v3 by '
     'version desc, so this is stale metadata, not live text'),
]

MYSTERY_ORCH = os.path.join(ROOT, 'services', 'mystery_generation', 'orchestrator.py')


# ── helpers ────────────────────────────────────────────────────────────────

def placeholders(text: str) -> set[str]:
    """Field names in a str.format template. '{{' / '}}' yield no field."""
    return {
        name.split('.')[0].split('[')[0]
        for _, name, _, _ in string.Formatter().parse(text)
        if name
    }


def match_conventions(draft: str, incumbent: str) -> str:
    """Reapply the incumbent's line-ending and trailing-newline conventions."""
    body = draft.replace('\r\n', '\n')
    if not incumbent.endswith('\n'):
        body = body.rstrip('\n')
    if '\r\n' in incumbent:
        body = body.replace('\n', '\r\n')
    return body


def fetch(db, task_name: str, version: int | None = None) -> dict | None:
    q = (db.table('prompt_templates')
           .select('id, task_name, version, is_active, model, provider, template_text')
           .eq('task_name', task_name).eq('language_id', EN))
    if version is not None:
        q = q.eq('version', version)
    else:
        q = q.eq('is_active', True)
    resp = q.order('version', desc=True).limit(1).execute()
    return resp.data[0] if resp.data else None


def check_row(row_spec, incumbent: dict) -> tuple[str, list[str]]:
    """Build the new text and return (text, problems)."""
    draft_file, task_name, _model, _provider, must_go, must_have, _desc = row_spec
    problems: list[str] = []

    with open(os.path.join(DRAFTS, draft_file), encoding='utf-8') as fh:
        draft = fh.read()
    old = incumbent['template_text']
    new = match_conventions(draft, old)

    # 1. Substitution fired: every must_go was really in the incumbent, and is
    #    really gone from the draft.
    for token in must_go:
        if token not in old:
            problems.append(
                f'must_go token absent from incumbent (row drifted since it '
                f'was read — do NOT write): {token!r}')
        if token in new:
            problems.append(f'must_go token survives in draft: {token!r}')
    for token in must_have:
        if token not in new:
            problems.append(f'must_have token missing from draft: {token!r}')

    # 2. Parser contract: placeholders must be a subset of what the caller gives.
    supplied = CALLER_ARGS[task_name]
    used = placeholders(new)
    unknown = used - supplied
    if unknown:
        problems.append(f'draft uses placeholders the caller does not supply '
                        f'(KeyError at generation time): {sorted(unknown)}')

    # 3. CEFR must be gone.
    hits = CEFR_RE.findall(new)
    if hits:
        problems.append(f'CEFR tokens survive in draft: {sorted(set(hits))}')

    # 4. Tier legend anchors present wherever a legend is claimed.
    if 'Complexity tier reference:' in new or 'on this scale:' in new:
        for anchor in TIER_ANCHORS:
            if anchor not in new:
                problems.append(f'tier legend incomplete, missing: {anchor!r}')

    # 5. Cloze-only: the five enum values and the JSON keys stay verbatim.
    if task_name == 'cloze_distractor_generation':
        for tag in CLOZE_TAGS:
            if f'"{tag}"' not in new:
                problems.append(f'distractor enum value missing: {tag!r}')

    return new, problems


# ── actions ────────────────────────────────────────────────────────────────

def plan(db) -> tuple[list[tuple], list[str]]:
    """Resolve every row and validate. Returns (writes, problems)."""
    writes: list[tuple] = []
    problems: list[str] = []

    for spec in ROWS:
        draft_file, task_name, model, provider, _mg, _mh, desc = spec
        incumbent = fetch(db, task_name)
        if incumbent is None:
            problems.append(f'{task_name}: no active en row to supersede')
            continue
        new, row_problems = check_row(spec, incumbent)
        problems.extend(f'{task_name}: {p}' for p in row_problems)
        if not row_problems:
            writes.append((task_name, incumbent, new, model, provider, desc))

    for task_name, version, reason in DEACTIVATE:
        row = fetch(db, task_name, version)
        if row is None:
            problems.append(f'{task_name} v{version}: row not found')
        elif not row['is_active']:
            print(f'  SKIP  {task_name} v{version} already inactive')
        else:
            newer = (db.table('prompt_templates').select('version, is_active')
                       .eq('task_name', task_name).eq('language_id', EN)
                       .gt('version', version).eq('is_active', True)
                       .execute().data)
            if not newer:
                problems.append(
                    f'{task_name} v{version}: refusing to deactivate — no '
                    f'active higher version exists to serve this task')

    return writes, problems


def apply(db, writes) -> None:
    for task_name, incumbent, new, model, provider, desc in writes:
        maxv = (db.table('prompt_templates').select('version')
                  .eq('task_name', task_name).eq('language_id', EN)
                  .order('version', desc=True).limit(1).execute().data[0]['version'])
        nextv = maxv + 1

        db.table('prompt_templates').insert({
            'task_name': task_name,
            'language_id': EN,
            'version': nextv,
            'template_text': new,
            'is_active': True,
            'model': model,
            'provider': provider,
        }).execute()

        db.table('prompt_templates').update({'is_active': False}) \
          .eq('id', incumbent['id']).execute()

        print(f'  WROTE {task_name} v{incumbent["version"]} -> v{nextv}  '
              f'(id {incumbent["id"]} deactivated)')
        print(f'        {desc}')

    for task_name, version, reason in DEACTIVATE:
        row = fetch(db, task_name, version)
        if row and row['is_active']:
            db.table('prompt_templates').update({'is_active': False}) \
              .eq('id', row['id']).execute()
            print(f'  DEACT {task_name} v{version} (id {row["id"]}) — {reason}')


def verify(db) -> int:
    """Re-read live state and assert every intended change landed."""
    failures = 0

    for spec in ROWS:
        draft_file, task_name, model, provider, must_go, must_have, _d = spec
        row = fetch(db, task_name)
        if row is None:
            print(f'  FAIL  {task_name}: no active en row'); failures += 1
            continue
        text = row['template_text']
        bad = [t for t in must_go if t in text]
        missing = [t for t in must_have if t not in text]
        cefr = sorted(set(CEFR_RE.findall(text)))
        unknown = placeholders(text) - CALLER_ARGS[task_name]
        if bad or missing or cefr or unknown:
            failures += 1
            print(f'  FAIL  {task_name} v{row["version"]}')
            if bad:      print(f'          must_go survives: {bad}')
            if missing:  print(f'          must_have missing: {missing}')
            if cefr:     print(f'          CEFR survives: {cefr}')
            if unknown:  print(f'          unknown placeholders: {sorted(unknown)}')
        else:
            print(f'  OK    {task_name} v{row["version"]} '
                  f'({row["model"]}, {len(text)} chars)')

    for task_name, version, _r in DEACTIVATE:
        row = fetch(db, task_name, version)
        if row is None:
            print(f'  FAIL  {task_name} v{version}: not found'); failures += 1
        elif row['is_active']:
            print(f'  FAIL  {task_name} v{version} still active'); failures += 1
        else:
            print(f'  OK    {task_name} v{version} inactive (id {row["id"]})')

    # The mystery orchestrator default that would inject a CEFR band.
    with open(MYSTERY_ORCH, encoding='utf-8') as fh:
        src = fh.read()
    if "difficulty_to_tier.get(difficulty, 'B1')" in src:
        print("  FAIL  mystery_generation/orchestrator.py still defaults to 'B1'")
        failures += 1
    elif "difficulty_to_tier.get(difficulty, 'T3')" in src:
        print("  OK    mystery_generation/orchestrator.py defaults to 'T3'")
    else:
        print('  FAIL  mystery_generation/orchestrator.py: tier default not '
              'found in either form — check the file'); failures += 1

    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='validate, write nothing')
    ap.add_argument('--verify', action='store_true', help='verify live state only')
    args = ap.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    if args.verify:
        print('TASK-734 verify:')
        return 1 if verify(db) else 0

    print('TASK-734 plan:')
    writes, problems = plan(db)

    for task_name, incumbent, new, model, provider, desc in writes:
        print(f'  READY {task_name} v{incumbent["version"]} '
              f'({len(incumbent["template_text"])} -> {len(new)} chars, '
              f'{"CRLF" if chr(13) in new else "LF"})')

    if problems:
        print('\nABORT — validation failed, nothing written:')
        for p in problems:
            print(f'  ! {p}')
        return 1

    if args.dry_run:
        print('\nDry run: validation passed, nothing written.')
        return 0

    print('\nApplying:')
    apply(db, writes)
    print('\nVerifying:')
    return 1 if verify(db) else 0


if __name__ == '__main__':
    raise SystemExit(main())
