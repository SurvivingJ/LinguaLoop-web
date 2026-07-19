---
title: "ADR-020: Late symbolic resolution across independently versioned artifacts must fail safe"
status: accepted
date: 2026-07-15
---

# ADR-020: Late symbolic resolution across independently versioned artifacts must fail safe

> Written as an analysis of the TASK-637 JA exemplar bug after it became clear the bug is
> an instance of a class, not a one-off. Prompted by review of TASK-636.
>
> **Accepted 2026-07-15.** The decision is implemented (`prompts._slug_index` returns `None`;
> `_exemplar_text` drops and logs) and the diagnostic below was run against production — it came
> back **positive**. This ADR is no longer a hypothesis about a class of bug; the instance it was
> written about had already shipped. See the 2026-07-15 incident entry in [[log]].

## Context

### The concrete instance

`migrations/dt_rubric_v4_seed.sql`'s JA exemplar carried `"subtype_slug": "particle"`.
Taxonomy v5 (`dt_taxonomy_v5_seed.sql`, TASK-626) **split** that slug into
`particle_wa_ga` / `particle_case` / `particle_other` and deliberately removed `particle`
from every `pairs` list. `prompts._exemplar_text` resolves the slug with
`subtypes.index(slug)`; it missed, and the handler was:

```python
except (ValueError, AttributeError):
    error["subtype"] = 0
```

Index 0 is `omission` in every v5 pairs list. So every JA tier1/tier2 system prompt
carried a worked example whose は/が swap was labelled *omission, severity major* — a
well-formed, confident, wrong few-shot example. No log, no error, no test failure.

### Where it stems from — three compounding causes

**1. A foreign key with no referential integrity.** `dt_rubric_version.config` and
`dt_taxonomy_version.taxonomy` are independently versioned `jsonb` blobs in different
tables. `rubric.exemplars[l2].error.subtype_slug` *is* a foreign key into
`taxonomy.pairs[l2].subtypes` — but it lives inside JSON, so Postgres cannot enforce it.
The join is deferred to Python, at prompt-build time, in a `try/except`.

**2. The two artifacts version independently.** TASK-626 bumped the taxonomy 4 → 5 and
stated in its own header: *"WHAT'S NEW vs v4 (rubric stays v4 - this is a TAXONOMY-ONLY
bump)"*. That sentence is the exact moment the reference broke. Nothing in the system
relates the two version numbers, so "taxonomy-only" was structurally unverifiable.

**3. The fallback chose a value inside the value space.** This is the actual defect.
`0` is not a sentinel — it is a real subtype. A `None` or `-1` would have been noisy
somewhere downstream; `0` renders as a valid exemplar. Failing *open into the value
space* is what converted a detectable error into silent corruption.

Cause 3 is the damning one, because **the codebase already had the right pattern**:

```python
# grader_cascade.py:729 — same index resolution, reverse direction
def _enum_lookup(enum_values, index) -> Optional[str]:
    ...
    if 0 <= idx < len(enum_values):
        return enum_values[idx]
    return None          # <- out of range fails to None, not to enum_values[0]
```

Same module family, ~150 lines away, doing the mirror-image operation, correctly.
`_exemplar_text` did not reuse it and invented a worse convention.

### Why the tests missed it — the seam

The taxonomy's **internal** cross-references are tested thoroughly:

- `test_subtype_meta_totality_over_every_pair_subtype`
- `test_live_historical_subtypes_all_resolve_in_meta`
- `test_ja_particle_split_present_and_old_name_gone_from_pairs`

The rubric → taxonomy cross-reference is tested **nowhere**.
`test_v4_exemplars_are_well_formed_for_all_three_l2s` asserts only
`assert err.get("subtype_slug")` — that a string is non-empty.

The reason is structural: **the test-file boundary follows the table boundary.**
`test_dual_translation_taxonomy_v5.py` owns the taxonomy. `test_dual_translation_rubric_v2.py`
owns the rubric. The reference crosses both, so it is owned by neither. The result is two
test files asserting contradictory facts — one that `particle` is gone from pairs, one that
the JA exemplar's slug is fine — **both green**.

Generalizable: *defects concentrate at the seam between two well-tested artifacts.*

### When it was introduced

**It is not committed.** `git log -S 'error["subtype"] = 0' -- services/dual_translation/prompts.py`
returns nothing; `dt_rubric_v4_seed.sql` and `dt_taxonomy_v5_seed.sql` are both untracked (`??`).
The fallback and both seeds are in-flight working-tree work. TASK-624 authored the exemplar
mechanism; TASK-626 broke the reference. This was caught pre-merge.

**Caveat — pre-merge does not mean not-live.** Seeds here are applied by hand to Supabase,
and this repo is known to drift from the live DB (precedent: the `process_test_submission`
CR-04 drift, where the live RPC never matched the repo). Whether JA prompts are currently
poisoned depends on whether both seeds were applied. Check:

```sql
SELECT (SELECT version FROM dt_taxonomy_version WHERE is_active) AS tax_version,
       (SELECT config->'exemplars'->'ja'->'error'->>'subtype_slug'
          FROM dt_rubric_version WHERE is_active)                AS ja_slug;
-- tax_version = 5 AND ja_slug = 'particle'  ->  live and poisoned
```

**RUN 2026-07-15 — result: `tax_version=5, ja_slug='particle'`. Live and poisoned.** Fixed by
applying `migrations/dt_rubric_v4_seed.sql` to production the same day.

The reasoning that delayed this query is itself a finding. The argument was: `git log -S` shows the
`= 0` fallback was never committed, so this is probably a near-miss. That inference is invalid —
these seeds are untracked *because* they are hand-applied, so git could never testify about live
state. The correct move was to spend one read-only query instead of one paragraph of speculation.
**Add to the warning-signal list: reasoning about live state from repo history, in a repo already
known to drift from live.**

TASK-637's own wording — *"in every JA prompt now that v5 is active"* — suggests its author
believed v5 was already applied. **Run the query before assuming this was a near-miss.**

### Is it recurring? Yes — this is the fourth instance of one class

**The class:** *a symbolic reference stored in one artifact, resolved late against a second,
independently-updated artifact, with a fail-open default.*

| Instance | Reference | Resolved against | Silent failure mode |
|---|---|---|---|
| **This one** | rubric exemplar `subtype_slug` | taxonomy `pairs[l2].subtypes` | → index 0, a *real* subtype |
| Prompt-template model slug rot | model slug in DB `prompt_templates` | OpenRouter model catalog | delisted → 404 → judges fail open |
| i18n `applyToDOM` | `data-i18n` key in template | `static/i18n/*.json` (×4) | renders the raw key string |
| Resolver hydration skill gap | scheduled slot type | `get_recommended_tests` output | slot silently dropped |

Every row: a reference, resolved late, against something on a **separate release cadence**,
degrading **silently**. Three of the four shipped before being caught. This is not a
Dual-Translation problem; it is an architecture-wide one, and it is why this ADR exists
rather than a one-line fix.

### What this costs 12 months out

1. **The surface grows superlinearly.** Every new versioned key is another reference.
   TASK-627 adds rubric `severity_weights`/`thresholds` keyed by severity slug → resolved
   against `SEVERITY_ENUM` **in code**, meaning a *code deploy* will then be able to break a
   *DB row*. `subtype_meta` (v5) is keyed by subtype. TASK-637 proposes `severity_slug` in
   exemplars. Each new L2 multiplies it. Roughly O(keys × languages × versioned artifacts),
   with no inventory of where the references are.

2. **The ordinal contract is load-bearing and unenforced.** Taxonomy v5's header states:
   *"Order IS the `_decode_error` index contract."* The model emits integers; list order
   assigns meaning. A future **insertion mid-list** — not just a rename — silently remaps
   meaning for every prompt, and **no slug-existence check would catch it**. The fix below
   protects against renames; it does not protect against reordering.

3. **Silent wrongness contaminates the eval loop.** The exemplar is few-shot training signal.
   A poisoned exemplar biases model output → biases `dt_error_instance` rows → biases the
   gold/eval sets (`scripts/run_dt_grading_eval.py`) → the eval that should have caught it is
   scored against data it corrupted. Twelve months of that is not recoverable by later fixing
   the slug; you would have to identify and discard the affected window.

4. **The fix gets more expensive.** Today it is one string and one `except`. After a year of
   `exemplars` + `severity_weights` + `subtype_meta` all cross-referencing, introducing a
   compatibility contract becomes a migration touching every versioned row.

5. **Confident-but-wrong documentation erodes review.** The v4 header asserted
   *"band_descriptors and weights are BYTE-IDENTICAL to v2 by construction"* in the same file
   whose JA exemplar was broken. Headers that are authoritative and wrong train reviewers to
   skim headers.

### What a post-mortem would flag as the warning signals

Ranked by how early each was visible:

1. **A contract asserted in prose.** *"Order IS the `_decode_error` index contract"* — a
   contract in a comment has no enforcement. Prose contracts are aspirations.
2. **A version bump that explicitly declares the other artifact unchanged.**
   *"rubric stays v4 — this is a TAXONOMY-ONLY bump"* is the breakage, written down, in the
   change that caused it. **A declared non-change to a coupled artifact is a review trigger.**
3. **A deliberate deletion with a partial alias.** v5 removed `particle` from pairs and kept
   it in `subtype_meta` as `historical_alias` *for stored rows*. The author reasoned carefully
   about the **stored** reference and never considered the **seeded** one. Migrating some
   references but not others proves the reference inventory is implicit.
4. **`except → constant`, where the constant is a legal value.** Greppable today.
   `except: x = 0` where `0` *means something* is the signature.
5. **Truthiness assertions on symbolic references.** `assert err.get("subtype_slug")` cannot
   fail for any realistic bug. It asserts *shape* where the risk is *reference*.
6. **Two test files asserting contradictory facts, both green.** Nothing detects this
   automatically; it requires a cross-artifact test to exist at all.
7. **Confident small scoping on a file with a known defect.** TASK-636 was scoped XS and
   hardened this file against a *hypothetical* environment while a *live* bug sat 76 lines away.

## Decision (proposed)

Four parts, ordered by payoff:

1. **Fail safe, never into the value space.** `_exemplar_text` logs a warning and **omits the
   exemplar** (`return ""` — the already-documented degradation path at `prompts.py:575`)
   rather than substituting `0`. Mirrors `_enum_lookup`'s `None`. Runtime degrades to a prompt
   without a worked example; **CI is the tripwire, not production.** This resolves the
   raise-vs-skip question in TASK-637's favour.
2. **Make cross-artifact references a tested inventory.** One test that enumerates *every*
   symbolic reference from rubric → taxonomy and asserts each resolves against the seeds as
   committed. Explicitly owns the seam that neither test file owned.
3. **Pin compatibility, not just existence.** Rubric config declares
   `requires_taxonomy_version: 5`; the seed's guard `RAISE`s if the active taxonomy row does
   not satisfy it; `get_active_rubric` asserts the pair at load. This makes a "TAXONOMY-ONLY
   bump" fail loudly at apply time instead of succeeding into a silent lie.
4. **Retire the ordinal contract at its next breaking change.** Have the model emit slugs
   rather than indices. Costs prompt tokens and cache churn; removes an entire failure class
   (including reordering, which 1–3 do not address).

Items 1–3 are cheap and should land with TASK-637. Item 4 is deliberately deferred, not
rejected — see Consequences.

## Consequences

**Easier:** taxonomy can be re-versioned without silent rubric rot; drift fails at apply-time
or CI rather than in a prompt; the reference set becomes explicit, enumerable, and greppable.

**Harder:** rubric and taxonomy seeds now carry a declared compatibility contract that must be
maintained; a taxonomy bump may now force a rubric re-seed. That is the intended cost — it
converts an invisible coupling into a visible one.

**Constrained:** no resolution failure anywhere in DT may fall back to a value inside the
value space. `None`, omission, or a raise — never `enum[0]`.

**Left open:** the ordinal contract (item 4) survives. Until it is retired, **reordering any
`pairs` list is a silent data-meaning change** that none of items 1–3 detect. This is the
largest known residual risk and should be stated in the taxonomy seed header.

## Alternatives Considered

- **Raise on an unresolvable slug** (the original Phase-2 plan, and the instruction this ADR
  argues against). Rejected: it converts a degraded prompt into a **hard grading outage** for
  that L2 — reintroducing precisely the outage class that TASK-636's guards exist to remove.
  Once the cross-artifact test (item 2) exists, CI catches drift before deploy, so runtime
  does not need to be the tripwire. Loud in CI beats loud in prod.
- **Keep the fallback, add logging.** Rejected: still ships a wrong exemplar. Logs are not
  read until an incident, and this failure produces no incident.
- **Normalize subtypes out of `jsonb` into a real table with a real FK.** Rejected for now:
  a large migration across every versioned row, and the blob-per-version design is deliberate
  (prompt-cache prefix stability — see `prompts.py` module docstring). Revisit if a fifth
  instance of the class appears.
- **Do nothing until it recurs.** Rejected: it already recurred. This is instance four.

## Related Pages

- [[tasklist/archive/evidence-first-grading.tasks]] — TASK-636 (seed guards), TASK-637 (this bug)
- [[algorithms/evidence-first-grading.tech]] — §3 severity triad, §4/5 derived scoring
- [[decisions/ADR-016-per-pair-error-taxonomy]] — the per-pair subtype tables this depends on
- [[decisions/ADR-019-evidence-first-scoring]] — the scoring layer that consumes these slugs
