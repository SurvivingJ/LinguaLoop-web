# Handoff brief — CEFR removal, cloze enum convergence, qwen review loop

Copy everything below the line into a fresh session. All findings below are **verified live**
against project `kpfqrjtfxmujzolwsvdq` on 2026-08-21 — do not re-derive them.

Source audit: `.claude/reviews/prompt-quality-audit-2026-08-21.md`
Auditor (read-only, re-runnable): `python scripts/audit_prompt_conventions.py [--check cefr]`

---

## Decisions already made by the user — do not re-ask

1. **Scope: all four CEFR groups are in.** Relabel group, `prose_generation`/`title_generation`,
   `scenario_batch_generation` (including its caller), and `collocation_sentence_generation` [zh].
2. **Tier naming in prompts: localised display name + age.** e.g. zh `小学生（8-9岁）`,
   ja `小学生（8-9歳）`, en `The Primary Schooler (Age 8-9)`. Not bare `T2`, not `T2 (gloss)`.
3. **`cloze_distractor_generation`: full port of the en v2 doctrine** into zh/ja — all five
   failure dimensions, the substitution audit step, and the two-distinct-dimensions rule. Not an
   enum-value swap.
4. **qwen 3.8 max reviews, it does not author.** Draft the zh/ja text yourself, send it to
   `qwen/qwen3.8-max` for a native-quality critique (naturalness, terminology, whether the
   grammar categories transfer), then apply its corrections. You stay accountable for contract
   tokens surviving intact.
5. **`vocab_phrase_detection` (the `phrasal_verb` finding, H1) is OUT of scope** for this pass.
   It remains open in the audit as a HIGH finding.

`qwen/qwen3.8-max` is confirmed live on OpenRouter: $2.00/M in, $6.00/M out, 1M context
(verified via `services.model_arena.pricing.fetch_model_list`).

---

## Canonical references — use these, do not invent

**Age tiers** — `wiki/features/exercises.md:47-52`, `wiki/features/exercise-generation-prompts.md:168-173`,
[ADR-003](../../wiki/decisions/ADR-003-age-tiers.md):

| Tier | Display name | Age | Vocab | Character |
|---|---|---|---|---|
| T1 | The Toddler | 4–5 | ~500 | Basic verbs, concrete nouns, one idea per sentence |
| T2 | The Primary Schooler | 8–9 | ~2,000 | Compound sentences, literal topics, no idioms |
| T3 | The Young Teen | 13–14 | ~5,000 | Colloquialisms, conditionals, everyday conversation |
| T4 | The High Schooler | 16–17 | ~10,000 | Standard adult structures, moderate jargon |
| T5 | The Uni Student | 19–21 | ~15,000+ | Complex clauses, cultural idioms, rich description |
| T6 | The Educated Professional | 30+ | ~25,000+ | High register, domain jargon, advanced rhetoric |

**Localised display names already exist in code** — `TIER_DISPLAY_NAMES`
(`services/conversation_generation/categorical_maps.py:170-176`), with a resolver
`get_tier_display(tier, language_id)` at line 276 and a full legend builder
`build_tier_legend(language_id)` at line 282. **Use these; do not hardcode tier strings.**
`services/conversation_generation/agents/conversation_writer.py:176,203` is the existing
precedent for passing a display name into a prompt.

**Distractor failure taxonomy** — `wiki/features/exercise-generation-prompts.md:570-582`.
Five dimensions, closed set:

| tag | meaning |
|---|---|
| `semantic` | wrong referent class / wrong concept |
| `collocational` | does not co-occur naturally with the surrounding lexis |
| `aspectual` | wrong lexical aspect / event structure |
| `register` | wrong formality / domain / social fit |
| `valency` | wrong argument structure / wrong complement |

Plus two rules the zh/ja rows are missing entirely: a **substitution audit** (swap in a common
synonym of the key; if the distractor becomes valid, reject it) and **at least TWO distinct
dimensions across the three distractors**. `wiki/features/exercise-generation-v2.md:175` adds
that a generic `"semantic"` tag on everything is itself a defect.

---

## Group A — the relabel (9 rows) — START HERE, but it is NOT prompt-only

`prompt_templates` rows, one CEFR line each, **CRLF line endings — preserve them**:

| id | task | lang | line | current text |
|---|---|---|---|---|
| 53 | conversation_persona_design | en | L4 | `CEFR Level: {complexity_tier}\r` |
| 54 | conversation_persona_design | zh | L4 | `CEFR等级：{complexity_tier}\r` |
| 55 | conversation_persona_design | ja | L4 | `CEFRレベル：{complexity_tier}\r` |
| 56 | conversation_scenario_plan | en | L7 | `CEFR Level: {complexity_tier}\r` |
| 57 | conversation_scenario_plan | zh | L7 | `CEFR等级：{complexity_tier}\r` |
| 58 | conversation_scenario_plan | ja | L7 | `CEFRレベル：{complexity_tier}\r` |
| 78 | mystery_plot | en | L2 | `- CEFR Level: {complexity_tier}\r` |
| 83 | mystery_plot | zh | L2 | `- CEFR等级：{complexity_tier}\r` |
| 88 | mystery_plot | ja | L2 | `- CEFRレベル：{complexity_tier}\r` |

**What is actually injected — verified:**

* `conversation_generation` passes a bare tier **code** (`'T3'` default) from
  `orchestrator.py:188,229,262`, `batch_processor.py:287,340,367`,
  `persona_designer.py:63,94`, `scenario_planner.py:75`.
* `mystery_generation` passes a code too, via `config.py:56-59`
  (`{1:'T1', 2:'T1', 3:'T2', 4:'T3', 5:'T3', 6:'T4', 7:'T5', 8:'T6', 9:'T6'}`).

So today the model literally reads **"CEFR Level: T4"** — a value that is not a CEFR level, under
a label claiming it is. Both halves are wrong.

**Because the user chose display names, the prompt edit alone is not enough** — the callers must
resolve the code to a localised display name before formatting. `conversation_writer.py` already
does this; `persona_designer.py`, `scenario_planner.py` and the mystery agents do not.

### BONUS BUG found while tracing — fix this too

`services/mystery_generation/orchestrator.py:77`:

```python
complexity_tier = mystery_gen_config.difficulty_to_tier.get(difficulty, 'B1')
```

The map yields T-codes but the **fallback default is the CEFR band `'B1'`**. Any difficulty
outside 1–9 injects a CEFR band into a prompt that otherwise receives tier codes. Change the
default to `'T3'` (matching every other caller in the codebase).

Note also `services/mystery_generation/database_client.py:74` reads `dim_complexity_tiers` from
the DB, and `mystery_generation` does not import `conversation_generation.categorical_maps`.
Decide deliberately whether to cross-import `get_tier_display` or source the display name from
`dim_complexity_tiers` — do not create a second hardcoded tier table.

---

## Group B — `prose_generation` + `title_generation` (6 rows)

Highest content impact: `prose_generation` shapes every generated passage.

* **`prose_generation`** [en, zh, ja] v1 — carries a full `【A1-A2 (Beginner)】` /
  `【B1-B2 (Intermediate)】` / `【C1-C2】` ladder with per-band target-audience definitions. The zh
  row anchors bands to HSK levels and the ja row to JLPT; those are legitimate *within* their
  language, but the CEFR spine must go. Six age tiers replace six CEFR bands 1:1
  (`CEFR_TO_TIER` at `categorical_maps.py:166` documents the intended mapping:
  A1→T1, A2→T2, B1→T3, B2→T4, C1→T5, C2→T6).
* **`title_generation`** [en, zh, ja] v1 — maps difficulty integers to CEFR
  (`Difficulty 1-2 (A1)` … through C2). A difficulty→tier map already exists at
  `categorical_maps.py:263`; use it rather than writing a new one. **These three rows also have
  NULL `model`/`provider`** (see Group E) — decide whether to populate while you are in there.

zh/ja text here needs the qwen 3.8 max review pass.

---

## Group C — `scenario_batch_generation` (needs a code change first)

Rows: en v2 and v3, zh v3, ja v2/v3. Contains `Target CEFR difficulty: {cefr_level}`.

Unlike Group A the **placeholder is itself named `cefr_level`**, so the caller may genuinely be
passing a real CEFR band — meaning CEFR could still be live in this pipeline rather than merely
stale wording. **Trace the caller before touching the prompt.** If it passes a band, the fix is a
code change plus a prompt change, in that order.

---

## Group D — `collocation_sentence_generation` [zh] (changes stored data)

Its **output** schema is `{"sentence": "...", "cefr_level": "B1"}` — the only row in the estate
that asks the model to *emit* CEFR, so it lands in stored rows. Changing the field name/values
changes the data shape: check what consumes it and whether existing rows need a backfill before
rewriting.

---

## Group E — `cloze_distractor_generation` zh/ja: full doctrine port

Current divergence:

| lang | ver | model | `distractor_tags` values |
|---|---|---|---|
| en | v2 | `google/gemini-3.5-flash-lite` | `semantic`, `collocational`, `valency` |
| zh | v1 | `qwen/qwen3.7-plus` | `semantic`, `form_error`, `learner_error` |
| ja | v1 | `qwen/qwen3.7-plus` | `semantic`, `form_error`, `learner_error` |

Root cause: `migrations/exercise_generation_schema.sql:237` seeded the old
`form_error`/`learner_error` set; `migrations/cloze_distractor_quality.sql:246` later updated
**English only**. zh/ja were never migrated.

Port the whole en v2 structure (5 dimensions + substitution audit + two-dimension rule) natively
into zh/ja, then qwen-review. Keep every JSON key and every enum **value** verbatim in English —
they are parser contract (`services/exercise_generation/validators.py:149`). Only the surrounding
instruction prose is translated.

Minor, same file: the ja row localises its example keys to `語1`/`語2`/`語3` where zh/en use
`word1`/`word2`/`word3`. The map is self-keyed at runtime so nothing breaks, but align them.

---

## Other things the audit turned up, not yet assigned

* **23 active rows have NULL `model` and `provider`.** `services/prompt_service.py:44-58` raises
  `RuntimeError` on a NULL model by design. But `services/topic_generation/database_client.py:549`
  selects only `template_text` and never reads `model`, so NULL is harmless on that path. This is
  "unusable on one of two access paths", **not** "23 broken features" — confirm per task before
  mass-populating. Affected: `cloze_target_selection`, `context_spectrum_generation`,
  `explorer_ideation_t1..t6`, `gatekeeper_check`, `semantic_discrimination_from_context`,
  `title_generation`, `vocab_definition_generation`, `vocab_sense_selection`.
* **Silent English fallback.** `services/topic_generation/database_client.py:562-575` retries with
  `language_id = 2` when a zh/ja row is missing and returns the English prompt, logging at
  `debug`. This is a live mechanism for manufacturing language-mixing at runtime. Raise it to
  `warning` or remove it.
* **`cloze_distractor_judge` zh/ja are byte-identical English copies** of the en row (1,492 chars
  each). The ja row is on `qwen/qwen-2.5-72b-instruct`, the only row in the estate on that slug,
  and memory records ja judges being moved off qwen for quality artefacts.

---

## Rules that must hold throughout

* **Do not "de-anglicise" parser contract.** JSON keys, enum values (`antonym`, `no_relation`,
  `corpus_validated`, `sentence_index`, the persona archetype ids, the
  `plain/polite/honorific/humble/formal/casual` register list) and `str.format` placeholders must
  stay verbatim in every language. `scripts/sweep_prompt_metalanguage.py` documents each
  exclusion and why. Two judges fail **silently** if a rewrite inverts them.
* **Version, do not overwrite.** Follow the existing pattern in `scripts/apply_prompt_rewrites.py`
  — insert a new version row and flip `is_active`, so a rollback is a flag change.
* **Assert each substitution fires.** A rule that matches nothing means the row drifted and the
  assumption behind the edit no longer holds; fail the run rather than writing a no-op version
  bump (the convention `sweep_prompt_metalanguage.py` already follows).
* **Numeric-index convention is already met** — do not "fix" it. 64 rows use numeric keys, 24 use
  index-valued enums; the rows emitting spelled-out labels are writing persisted column values
  (`phrase_type`, `question_type`), not choosing among options. Ladder maps are 0-based, P1/P2
  maps are 1-based, and **both are correct** — do not unify them.
* **Re-run `scripts/audit_prompt_conventions.py --check cefr` at the end.** It should report
  0 CEFR rows. That is the acceptance test for Groups A–D.

## Cost note

The audit session that produced this brief ran to ~$53. The rewrite work is larger. Budget for it
deliberately, and prefer batching the zh/ja qwen reviews over one-at-a-time calls.
