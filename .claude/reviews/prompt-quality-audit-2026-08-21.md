# Prompt Quality Audit — 161 active `prompt_templates` rows (en / zh / ja)

**Reviewed:** 2026-08-21
**Scope:** every `is_active = true` row in `prompt_templates`, project `kpfqrjtfxmujzolwsvdq`
**Criteria:** (1) no language mixing, (2) numeric indices for JSON output, (3) age tiers not CEFR
**Decision:** **REQUEST CHANGES** — 3 HIGH, 7 MEDIUM, 2 LOW

Auditor: `scripts/audit_prompt_conventions.py` (new, read-only). Re-runnable:
`python scripts/audit_prompt_conventions.py [--check language|json|cefr] [--verbose]`

---

## Inventory

| | en | zh | ja | total |
|---|---|---|---|---|
| active rows | 55 | 56 | 50 | **161** |
| distinct `task_name` | | | | 66 |
| template text | | | | 192,811 chars (median 893, max 6,915) |

Three rows per task is the norm; 9 tasks are single-language by design
(`explorer_ideation_t1..t6`, `gatekeeper_check`, and the zh-only collocation family).

---

## Verdict per criterion

| Criterion | Verdict | Detail |
|---|---|---|
| 1. No language mixing | **Mostly clean, 2 real defects** | 43 rows carry Latin runs but nearly all are parser contract, already adjudicated in `sweep_prompt_metalanguage.py`. Two genuine defects below (H1, M5). |
| 2. Numeric JSON indices | **Compliant** | 137 rows dictate JSON: 64 use numeric keys, 24 use index-valued enums. The 27 "labels-only" rows are persisted taxonomy values or fixed constants, not enum choices — see the note below. Not drift. |
| 3. Age tiers not CEFR | **FAILING — 12 rows** | CEFR was replaced project-wide by `VALID_TIERS = T1..T6`, yet 12 active rows still instruct models in CEFR bands, including the primary content generator in all three languages. |

### Note on criterion 2 — why "labels-only" is not a defect

The 27 rows emitting a spelled-out label rather than an index almost all emit a value that is
**written straight into a database column**, not decoded against an in-memory enum:
`phrase_type` → `orchestrator.py:1034-1035` and `pipeline.py:281`; `question_type` →
`test_service.py:270`. Converting these to indices would require a decode table on the write path
and would change the stored column contract. Meanwhile `question_type` is a *constant* each
prompt echoes back (one prompt per question type), not a choice among options.

The convention is in fact being applied exactly where it belongs — where the model **chooses
among presented options** (ladder option maps, DT `category`/`source`/`severity`/`subtype`). Both
live numberings remain correct and must not be unified: ladder maps are 0-based (0 = first option,
9 = escape hatch), P1/P2 maps are 1-based.

---

## HIGH

### H1 — `vocab_phrase_detection` teaches an English grammar category to zh and ja

All three rows use `"phrase_type": "phrasal_verb"` as their sole worked example — including the
Chinese row (example phrase `放弃`) and the Japanese row (`取り組む`).

**Neither Chinese nor Japanese has phrasal verbs.** It is an English-specific construction. The
zh/ja prompts are demonstrating a category that does not exist in the language being analysed,
using a native word as the example of it. This is language mixing of the most consequential
kind — not a stray English token, but an imported grammatical framework.

It is also persisted: `phrase_type` is written directly to a column, so every zh/ja phrase
detected under this prompt carries an English-grammar label into storage.

*Fix:* author a per-language `phrase_type` set (zh: 离合词 / 成语 / 固定搭配; ja: 複合動詞 /
慣用句 / 連語) and replace each row's worked example with one from its own language. Check what
`phrase_type` values are already stored before changing the vocabulary.

### H2 — `cloze_distractor_generation` enum set diverges across languages

| lang | ver | `distractor_tags` values |
|---|---|---|
| en | v2 | `semantic`, `collocational`, `valency` |
| zh | v1 | `semantic`, `form_error`, `learner_error` |
| ja | v1 | `semantic`, `form_error`, `learner_error` |

Four of the six distinct values exist in only one branch. Any consumer that switches on
`distractor_tags` is either handling values it never sees for two languages, or silently dropping
values it does not recognise. The en row is v2 and the other two are v1 — this reads as an en-only
revision that was never propagated.

*Fix:* decide the canonical set, then version all three together. This is the failure mode
recorded in the `prompt-latin-mostly-contract` note — enum drift across languages fails silently.

### H3 — Three prompts label an age tier as a CEFR level

`conversation_persona_design`, `conversation_scenario_plan` and `mystery_plot` all contain the
literal line:

```
CEFR Level: {complexity_tier}
```

`complexity_tier` is populated from `VALID_TIERS = ('T1'..'T6')`
(`services/conversation_generation/categorical_maps.py:163`). So the model is told
**"CEFR Level: T4"** — a value that is not a CEFR level, under a label that says it is. Both
halves are wrong: the scale name is stale, and the label contradicts its own value.

Affects all three languages for each task (the zh/ja rows carry the English string `CEFR` too,
which is why they surface in the language check as well).

*Fix:* relabel to `Complexity tier: {complexity_tier}` and add the T1–T6 legend already written
in `TIER_DISPLAY_NAMES`.

---

## MEDIUM

### M1 — `prose_generation` (en, zh, ja) defines its entire difficulty ladder in CEFR

The primary content generator. All three rows carry a full `【A1-A2 (Beginner)】` /
`【B1-B2 (Intermediate)】` / `【C1-C2】` band structure with target-audience definitions per band.
The zh row anchors bands to HSK levels, the ja row to JLPT — both reasonable *within* their
language, but the CEFR spine is the thing the project replaced.

Highest-impact of the CEFR findings: it shapes every generated passage.

### M2 — `title_generation` (en, zh, ja) maps difficulty integers to CEFR bands

`Difficulty 1-2 (A1)` … `Difficulty 5 (B1)` … through C2. A difficulty→tier map already exists
(`categorical_maps.py:263`, `1: 'T1', 2: 'T1', 3: 'T2', …`). These rows should use it. Also has
a NULL model (see M6).

### M3 — `scenario_batch_generation` injects a placeholder literally named `cefr_level`

`Target CEFR difficulty: {cefr_level}` (en v2/v3; zh and ja carry the English token `CEFR`).
Unlike H3 the placeholder name matches the label, so the caller may genuinely be passing a CEFR
band — which would mean CEFR is still live in that pipeline, not merely stale wording. Worth
tracing the caller before rewriting.

### M4 — `collocation_sentence_generation` [zh] emits CEFR in its **output** schema

`{"sentence": "...", "cefr_level": "B1"}` — CEFR is not just prompt wording here, it is a field
the model is asked to produce, so it lands in stored data. The only row in the estate that does
this.

### M5 — `cloze_distractor_judge` zh and ja are byte-identical English copies

All three rows are 1,492 characters with the same opening text. The zh and ja rows are the English
prompt filed under a CJK `language_id`, not translations.

Judging zh/ja content in English is a defensible design choice — but if it is the choice it should
be deliberate and documented, because the rest of the estate was natively rewritten (TASK-722) and
these rows read as an oversight. Separately, the ja row is on `qwen/qwen-2.5-72b-instruct`, the
only row in the estate on that slug, and memory records ja judges being moved *off* qwen for
quality artefacts.

### M6 — 23 active rows have NULL `model` and NULL `provider`

`cloze_target_selection`, `context_spectrum_generation`, `explorer_ideation_t1..t6`,
`gatekeeper_check`, `semantic_discrimination_from_context`, `title_generation`,
`vocab_definition_generation`, `vocab_sense_selection`.

`services/prompt_service.py:44-58` raises `RuntimeError` on a NULL model — "No silent fallback —
operator must populate the table." Any of these fetched through `get_active_prompt` is a hard
failure at call time.

**Caveat, and it matters:** `services/topic_generation/database_client.py:549` selects only
`template_text` and never reads `model`, so on that path NULL is harmless. I did not trace every
caller, so this is "23 rows are unusable on one of two access paths", not "23 broken features".
Worth confirming per task before mass-populating.

### M7 — the alternate prompt accessor silently falls back to English

`services/topic_generation/database_client.py:562-575`: if no row exists for the requested
`language_id`, it retries with `language_id = 2` and returns the English prompt, logging at
`debug`. A missing zh/ja row therefore *becomes* a language-mixing incident at runtime, invisibly.
This is a live mechanism for producing exactly the defect criterion 1 is meant to prevent.

---

## LOW

### L1 — ja `cloze_distractor_generation` localises its example keys

zh/en key the `distractor_tags` map as `word1`/`word2`/`word3`; ja uses `語1`/`語2`/`語3`. The map
is self-keyed by the actual distractor at runtime, so these are illustrative only and nothing
breaks — but it is a gratuitous divergence in a schema example.

### L2 — `question_vocabulary_context` [en] labels a worked example "Advanced Example (C2)"

A single CEFR token in an example heading. Cosmetic next to M1/M2, same root cause.

---

## What is genuinely clean

- **`dual_translation_tier1/2/3`** (6 rows, cjk_ratio 0.0) are **not defects**. Their text reads
  "Model-routing row only; no prompt text" — they carry a model slug and are never sent to a
  model. Correctly excluded.
- **The 43 rows flagged with Latin runs are overwhelmingly contract**: `antonym`/`synonym`/
  `no_relation`, `corpus_validated`, `llm_asserted`, `sentence_index`, `estimated_tier`, the 27
  persona archetype ids, the `plain/polite/honorific/humble/formal/casual` register list, and
  `str.format` placeholders. `sweep_prompt_metalanguage.py` documents each exclusion and why.
  Rewriting these would break parsers silently. **Do not "de-anglicise" them.**
- **Criterion 2 is met** where it is meaningful — see the note above.

---

## Validation

| Check | Result |
|---|---|
| Tests (`PYTHONPATH=. pytest tests/`) | Pass — 1922 passed, 3 skipped, 0 failed (unchanged; the new script is read-only and standalone) |
| Auditor runs against live | Pass — 161 rows, three checks |
| Lint | Skipped — `npm run check` exits 1 on a pre-existing CRLF prettier baseline |

## Suggested order of work

1. **H3** — one-line relabel in 9 rows, zero risk, removes the most incoherent instruction in the estate.
2. **H1** — needs a per-language taxonomy decision first; check stored `phrase_type` values before changing.
3. **H2** — decide the canonical enum set, version all three languages together.
4. **M1/M2** — the CEFR→T1–T6 rewrite of `prose_generation` and `title_generation`; largest content impact, needs native review for zh/ja.
5. **M7** — make the English fallback log at `warning`, or remove it.
6. **M3/M4/M6** — trace callers first; each may be narrower than it looks.
