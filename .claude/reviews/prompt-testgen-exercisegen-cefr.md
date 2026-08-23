# Handoff prompt — CEFR removal + cloze enum convergence (test-gen & exercise-gen only)

Copy everything below the line into a fresh session.

---

Fix the CEFR contamination in the **test generation** and **exercise generation** prompt families,
and converge the `cloze_distractor_generation` enum across languages. 14 rows in
`prompt_templates`, live project `kpfqrjtfxmujzolwsvdq`.

Ignore the conversation/mystery/scenario rows for now — they are a separate, lower-impact group
tracked in `.claude/reviews/prompt-cefr-and-cloze-fixes-brief.md`.

## Background (verified live 2026-08-21 — do not re-derive)

CEFR was replaced project-wide by six age tiers T1–T6 (`VALID_TIERS`,
`services/conversation_generation/categorical_maps.py:163`; `CEFR_TO_TIER` at :166 survives only
as a migration map). 24 active prompt rows still reference CEFR. 14 of them are in the two core
content pipelines and are the subject of this task.

Audit: `.claude/reviews/prompt-quality-audit-2026-08-21.md`
Re-runnable checker: `python scripts/audit_prompt_conventions.py --check cefr`

**Known auditor caveat, already fixed:** the CEFR word pattern used to be `\bCEFR\b`, which never
matched `CEFR等级` / `CEFRレベル` because CJK codepoints are `\w` in Python and there is no word
boundary after the `R`. It now uses `(?<![A-Za-z0-9])CEFR(?![A-Za-z0-9])`. If you write any new
CJK-aware regex, do not use `\b`.

## The real defect is not wording — it is an unbridged mismatch

Every one of these prompts receives `{complexity_tier}`, and the callers inject a **T-code**
(`'T1'`..`'T6'`; conversation callers default `'T3'`, mystery maps difficulty via
`services/mystery_generation/config.py:56-59`). But the prompts express their difficulty ladders
in **CEFR bands**. Nothing bridges the two. So the model is handed `T3` and a rubric keyed by
`A1-A2 / B1-B2 / C1-C2`, and has to guess the mapping. That is a live content-quality bug, not a
cosmetic one.

## Decisions already made — do not re-litigate

1. **Tier naming in prompts: localised display name + age.** zh `小学生（8-9岁）`,
   ja `小学生（8-9歳）`, en `The Primary Schooler (Age 8-9)`. Not bare `T2`.
2. **Use the existing helpers.** `TIER_DISPLAY_NAMES` (`categorical_maps.py:170`),
   `get_tier_display(tier, language_id)` (:276), `build_tier_legend(language_id)` (:282).
   `services/conversation_generation/agents/conversation_writer.py:176,203` is the working
   precedent. **Do not hardcode a second tier table.**
3. **`cloze_distractor_generation`: full port of the en v2 doctrine into zh/ja**, not an enum swap.
4. **qwen 3.8 max reviews, it does not author.** Draft zh/ja yourself, send to
   `qwen/qwen3.8-max` for native-quality critique, apply corrections. Confirmed live on
   OpenRouter: $2.00/M in, $6.00/M out, 1M context.
5. `vocab_phrase_detection` (the `phrasal_verb` finding) is **out of scope**.

## Canonical age-tier table

`wiki/features/exercises.md:47-52`, `wiki/features/exercise-generation-prompts.md:168-173`,
ADR-003.

| Tier | Display name | Age | Vocab | Character | (was) |
|---|---|---|---|---|---|
| T1 | The Toddler | 4–5 | ~500 | Basic verbs, concrete nouns, one idea per sentence | A1 |
| T2 | The Primary Schooler | 8–9 | ~2,000 | Compound sentences, literal topics, no idioms | A2 |
| T3 | The Young Teen | 13–14 | ~5,000 | Colloquialisms, conditionals, everyday conversation | B1 |
| T4 | The High Schooler | 16–17 | ~10,000 | Standard adult structures, moderate jargon | B2 |
| T5 | The Uni Student | 19–21 | ~15,000+ | Complex clauses, cultural idioms, rich description | C1 |
| T6 | The Educated Professional | 30+ | ~25,000+ | High register, domain jargon, advanced rhetoric | C2 |

Difficulty-integer → tier map already exists at `categorical_maps.py:263`. Use it; do not invent
a second one.

---

# TEST GENERATION — 7 rows

## T1. `prose_generation` — ids 6 (en), 13 (zh), 20 (ja), all v1

**Highest impact in the whole estate: this generates every passage.**

Receives `{complexity_tier}` (a T-code) but defines its ladder in CEFR bands:

| line | en (id 6) | zh (id 13) | ja (id 20) |
|---|---|---|---|
| L8 | `**【A1-A2 (Beginner)】**` | `**【A1-A2 (初学者)】**` | `**【A1-A2 (初心者)】**` |
| L17 | `**【B1-B2 (Intermediate)】**` | `**【B1-B2 (中级)】**` | `**【B1-B2 (中級)】**` |
| L23/24 | `**【C1-C2 (Advanced)】**` | `**【C1-C2 (高级)】**` | `**【C1-C2 (上級)】**` |

Plus band-conditional rules further down that will break if the headings change without them:

* en L42 `**Deconstruct Topic (Critical for A1/A2):** If the level is A1-A2, strip the topic of abstract nouns…`
* en L47 `**A1-A2 Check:** Scan for and remove any words with 3+ syllables…`
* zh L43 `**概念简化 (A1/A2专用):**…如果是 A1/A2 等级…`
* zh L47 `*   检查 A1/A2 段落中是否含有成语（必须移除）。`
* ja L41 `**トピックの簡略化:** 指定レベルがA1-A2の場合…`
* ja L45 `*   A1-A2の場合、専門用語が含まれていないか再確認する。`

**Fix:** replace the three 2-band groupings with **six single-tier sections** (the current
structure collapses two bands per heading; six tiers map 1:1 and remove the collapsing). Rewrite
each conditional rule to name its tiers. Keep the existing per-band target-audience and
constraint content, re-keyed — the zh row's HSK anchors and the ja row's JLPT anchors are
legitimate within their language and should be **kept**, just re-hung off tiers.

The prompt is 55/56/54 lines — read each in full before editing; the hit list above is not
exhaustive of the surrounding logic.

## T2. `title_generation` — ids 27 (en), 28 (zh), 29 (ja), all v1

**Two independent defects in each row.**

(a) Label mislabel, L7 — value is a T-code:

* en `CEFR LEVEL: {complexity_tier}`
* zh `CEFR级别：{complexity_tier}`
* ja `CEFRレベル：{complexity_tier}`

(b) A difficulty→CEFR ladder, L13–L18 (six lines each), e.g. en:

```
* Difficulty 1-2 (A1): Very simple, 3-6 words, basic vocabulary
* Difficulty 3-4 (A2): Simple, 4-8 words, straightforward language
* Difficulty 5 (B1): Clear, 5-10 words, everyday vocabulary
* Difficulty 6 (B2): Moderately descriptive, 6-12 words, varied vocabulary
* Difficulty 7 (C1): Sophisticated, 8-15 words, nuanced expressions
* Difficulty 8-9 (C2): Complex, 10-18 words, advanced vocabulary and structures
```

zh and ja carry the identical structure with their own word/character counts — **preserve the
per-language length figures**, they differ deliberately (en counts words, zh/ja count characters).

**Fix:** relabel L7 to a localised tier label, and re-key L13–18 from CEFR bands to tiers using
`categorical_maps.py:263`. Note the row already receives **both** `{difficulty}` and
`{complexity_tier}` — decide which drives the ladder and say so explicitly rather than leaving
two competing scales in one prompt.

**Also:** all three rows have `model = NULL` and `provider = NULL`.
`services/prompt_service.py:44-58` raises `RuntimeError` on a NULL model. Check whether the
title path goes through `get_active_prompt` (if so these are already broken) or through
`services/test_generation/agents/title_generator.py` with its own accessor. Populate or document.

## T3. `question_vocabulary_context` — id 8 (en) v1 only

Single cosmetic hit, L54: `**Advanced Example (C2):**`. Retitle to the tier.

The zh (id 326) and ja (id 327) rows are **v3 and already clean** — do not touch them.

---

# EXERCISE GENERATION — 7 rows

## E1. `exercise_sentence_generation` — ids 180 (en), 39 (zh), 190 (ja), all v1

**Worse than a label: CEFR is in the OUTPUT schema.**

* en L5 `Return a JSON array of objects: [{{"sentence": "...", "cefr_level": "{complexity_tier}"}}]`
* zh L6 `返回一个 JSON 对象数组：[{{"sentence": "...", "cefr_level": "{complexity_tier}"}}]`
* ja L6 `JSON オブジェクトの配列を返す：[{"sentence": "...", "cefr_level": "{complexity_tier}"}]`

The model is told to emit a field **named** `cefr_level` whose **value is a T-code**. So every
generated row carries `cefr_level: "T3"` — a CEFR-named field holding a non-CEFR value.

**Fix:** rename the field to `complexity_tier` (or `tier`) in all three prompts.

**Before you do:** grep for consumers of `cefr_level` across `services/exercise_generation/` and
the DB. If anything reads that key, the rename is a coordinated code+prompt change, and existing
stored rows may need a backfill. **Do not rename the prompt field alone.**

Note the ja row's JSON uses single braces `{"sentence"…}` while en/zh use doubled `{{…}}`. Doubled
braces are `str.format` escaping. **Verify which is correct for this call path before touching it**
— if ja is genuinely single-braced it will either raise `KeyError` on format or silently consume
the literal. This may be a live bug independent of CEFR.

## E2. `vocab_sentence_generation` — id 50 (zh) v1

Identical defect to E1, L5:
`返回一个 JSON 对象数组：[{{"sentence": "...", "cefr_level": "{complexity_tier}"}}]`

Same fix, same consumer check. zh-only — there is no en/ja row.

## E3. `collocation_sentence_generation` — id 51 (zh) v1

L5: `返回一个 JSON 对象数组：[{{"sentence": "...", "cefr_level": "B1"}}]`

**This one is hardcoded.** No placeholder — the prompt asks the model to emit the literal string
`"B1"` on every call, regardless of the requested difficulty. Its placeholder list is
`['collocation_text', 'count', 'pos_pattern']` — it does not receive `complexity_tier` at all.

**Fix:** decide whether this generator should be tier-aware. If yes, the caller must start passing
`complexity_tier` (code change) and the field becomes `"complexity_tier": "{complexity_tier}"`.
If no, drop the field entirely rather than emitting a constant. **Do not simply swap `B1` for
`T3`** — that preserves the bug in new clothes.

## E4. `cloze_distractor_generation` zh + ja — enum divergence

Ids not captured; look them up by `task_name` + `is_active`.

| lang | ver | model | `distractor_tags` values |
|---|---|---|---|
| en | v2 | `google/gemini-3.5-flash-lite` | `semantic`, `collocational`, `valency` |
| zh | v1 | `qwen/qwen3.7-plus` | `semantic`, `form_error`, `learner_error` |
| ja | v1 | `qwen/qwen3.7-plus` | `semantic`, `form_error`, `learner_error` |

Root cause: `migrations/exercise_generation_schema.sql:237` seeded the old set;
`migrations/cloze_distractor_quality.sql:246` later updated **English only**. zh/ja were never
migrated.

Canonical taxonomy — `wiki/features/exercise-generation-prompts.md:570-582`, five dimensions,
closed set:

| tag | meaning |
|---|---|
| `semantic` | wrong referent class / wrong concept |
| `collocational` | does not co-occur naturally with the surrounding lexis |
| `aspectual` | wrong lexical aspect / event structure |
| `register` | wrong formality / domain / social fit |
| `valency` | wrong argument structure / wrong complement |

zh/ja are also missing two rules the en row has: a **substitution audit** (swap in a common
synonym of the key; if the distractor becomes valid, reject it) and **at least TWO distinct
dimensions across the three distractors**. `wiki/features/exercise-generation-v2.md:175` adds that
a generic `"semantic"` tag on everything is itself a defect.

**Fix:** port the whole en v2 structure natively into zh/ja. Translate only the instruction prose
— every JSON key and every enum **value** stays verbatim English (parser contract,
`services/exercise_generation/validators.py:149`). Then qwen-review.

Minor, same rows: the ja row localises its example keys to `語1`/`語2`/`語3` where en/zh use
`word1`/`word2`/`word3`. The map is self-keyed at runtime so nothing breaks — align them anyway.

---

## Rules that must hold

* **Do not de-anglicise parser contract.** JSON keys, enum values, and `str.format` placeholders
  stay verbatim in every language. `scripts/sweep_prompt_metalanguage.py` documents each
  exclusion. Two judges fail **silently** if a rewrite inverts them.
* **Version, do not overwrite.** Follow `scripts/apply_prompt_rewrites.py` — insert a new version
  row and flip `is_active`, so rollback is a flag change.
* **Assert each substitution fires.** A rule matching nothing means the row drifted; fail the run
  rather than writing a no-op version bump.
* **Numeric-index convention is already met — do not "fix" it.** Ladder option maps are 0-based,
  P1/P2 maps are 1-based, and both are correct. Do not unify them.
* **CRLF:** these rows use `\r\n`. Preserve line endings.

## Acceptance

1. `python scripts/audit_prompt_conventions.py --check cefr` reports **0 rows** for all 14 task
   names above. (It will still report the conversation/mystery group — that is expected and out
   of scope.)
2. No `cefr_level` key remains in any test-gen or exercise-gen output schema.
3. All three `cloze_distractor_generation` rows emit the same five-value tag set.
4. `PYTHONPATH=. python -m pytest tests/` — baseline **1922 passed, 3 skipped, 0 failed**.
5. Smoke one generation per changed family before declaring done — `prose_generation` and
   `exercise_sentence_generation` at minimum, at two different tiers, and confirm the emitted
   difficulty actually tracks the requested tier.

## Report honestly

Say which consumer checks you ran for `cefr_level`, whether the ja single-brace anomaly in E1 was
a real bug, and whether `collocation_sentence_generation` was made tier-aware or had the field
dropped. Those three are the decisions most likely to be got wrong quietly.
