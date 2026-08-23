# Handoff brief — redesign the ja L1 listening exercise

Copy everything below the line into a fresh session. Every fact in the
"Verified state" section was checked live against project `kpfqrjtfxmujzolwsvdq`
on 2026-08-22 — **do not re-derive it, and do not spend LLM calls confirming it.**

Prior work: `.claude/reviews/task735-ja-l1-fixes.md` (TASK-735).

---

## Your task

L1 of the Japanese vocabulary ladder works, but only just. After three rounds of
prompt surgery it renders **1 of 2** test variants, where it needs to render
close to all of them. Rather than a fourth round of the same tuning, I want you
to **step back and explore the design space**, then report.

Two parallel tracks:

**Track A — prompt variants.** Draft and evaluate several genuinely different
prompt strategies for the existing architecture (one LLM call emits distractors,
a second LLM judges them). Different *strategies*, not reworded versions of the
same one.

**Track B — different architectures.** Question whether an LLM should be
generating the distractors at all. Propose at least two designs that change the
mechanism rather than the wording.

Then produce **one report covering every proposal from both tracks**, in the
format specified under "Deliverable".

**Do not apply anything to the live database.** This pass ends with a report and
a recommendation. Prompt drafts belong in `data/eval/<task>/` as files.

---

## What L1 is for — the goals any proposal must preserve

The learner **hears** the target word spoken aloud by TTS and picks the matching
**written** form from four options. That is the whole exercise. It trains the
mapping from sound to orthography, which in Japanese is the hard part.

Therefore a good distractor is:

- a **real word** — a headword you could look up;
- **audio-confusable** with the target — the learner who hears the target should
  plausibly reach for it;
- **not a synonym** — otherwise picking it is defensible and the item has two
  right answers;
- **not a spelling look-alike that sounds different** — that defeats the whole
  point, because it makes the item solvable without listening;
- **not distinguishable only by pitch accent** — L1 plays *one* TTS rendering,
  so there is no second utterance to compare against and the learner cannot
  decide. 機械/機会 and 箸/橋 are invalid for this reason. This one is
  counter-intuitive and was got wrong twice, so state it explicitly in any
  prompt you draft.

## Constraints — these are not negotiable

### 1. Age tiers must be honoured, and currently are not

`{complexity_tier}` is injected into the ja P2 template header
(`学習者レベル：{complexity_tier}`) but **the L1 block never references it**. I
confirmed this against the live v4 row. So a T1 learner (age 4–5) and a T6
learner (age 30+) receive identically-calibrated distractors today. That is a
defect, and closing it is part of this task.

The tier codes are T1–T6, resolved from
`services/conversation_generation/categorical_maps.py`:

| helper | line | use |
|---|---|---|
| `TIER_DISPLAY_NAMES` | 170 | localised display name per tier per language |
| `get_tier_display(tier, language_id)` | 284 | resolve one code → ja display name |
| `build_tier_legend(language_id)` | 290 | full legend |

| Tier | Age | Character |
|---|---|---|
| T1 | 4–5 | ~500 words, concrete nouns, one idea per sentence |
| T2 | 8–9 | ~2,000 words, compound sentences, literal topics |
| T3 | 13–14 | ~5,000 words, colloquialisms, everyday conversation |
| T4 | 16–17 | ~10,000 words, standard adult structures |
| T5 | 19–21 | ~15,000+ words, complex clauses, cultural idioms |
| T6 | 30+ | ~25,000+ words, high register, domain jargon |

Canonical: `wiki/features/exercise-generation-prompts.md:168-173`,
[ADR-003](../../wiki/decisions/ADR-003-age-tiers.md). **Use the helpers; do not
hardcode tier strings.** Prompts should carry the localised display name and
age, not a bare `T4` — that convention was settled in TASK-733.

A specific question worth answering in your report: **should phonetic distance
scale with tier?** A tight one-mora minimal pair may be right for T5/T6 and
simply cruel at T1, where a wider phonetic gap is the honest difficulty. Or the
tier should govern the *vocabulary* the distractors are drawn from and not the
distance. Argue it either way, but argue it.

### 2. JSON output with numeric index keys

The parser contract is fixed by `remap_keys` / `OPTION_KEY_MAP`
(`services/vocabulary_ladder/config.py:1024`). Top-level keys are level numbers
as strings; each option object is:

```json
{"1": "option text", "2": true, "3": "explanation"}
```

`"1"` = text, `"2"` = is_correct (JSON boolean), `"3"` = explanation.

**Do not renumber these.** There is a second, 0-based map
(`LADDER_OPTION_KEY_MAP`, line 1037) used by the split single-type prompts —
the two numberings are deliberately different and unifying them would mean
re-authoring P2 and migrating stored assets. If a proposal needs a new field,
propose it as an *additional* numeric key and say what would have to change.

### 3. Same goals as the original prompt

Whatever you propose still has to produce a four-option listening MCQ with one
correct answer and per-option explanations in Japanese. A design that produces
something pedagogically different is out of scope, however elegant.

---

## Verified state — do not re-derive

### Live prompt rows (`prompt_templates`)

| id | task_name | lang | version | model |
|---|---|---|---|---|
| 184 | `vocab_prompt2_exercises` | ja | **v4** | `qwen/qwen3.7-plus` |
| 370 | `ladder_l1_distractor_judge` | ja | **v3** | `qwen/qwen3.7-plus` |
| 145 | `vocab_prompt2_exercises` | en | v4 | `anthropic/claude-sonnet-5` |
| 173 | `ladder_l1_distractor_judge` | en | v1 | `google/gemini-3.5-flash-lite` |
| 274 | `vocab_prompt2_exercises` | zh | v4 | `qwen/qwen3.7-plus` |
| 254 | `ladder_l1_distractor_judge` | zh | v2 | `qwen/qwen3.7-plus` |

All ja rows are **LF**, not CRLF. The en generator row is CRLF.

The en L1 section is the reference doctrine and is worth reading before you
start — it is the only one of the three that has never produced a fabrication.

### Two different template engines — this trap has bitten twice

| task | engine | brace rule |
|---|---|---|
| `vocab_prompt2_exercises` | `asset_generators/_renderer.render_template` | **single** braces; only `{bare_identifier}` is substituted, all other braces pass through |
| `ladder_l1_distractor_judge` | plain `str.format` (`judges/l1_distractor.py:79`) | **doubled** braces or it raises |

Getting this backwards is a live crash, not a quality regression. It took out ja
`exercise_sentence_generation` entirely under TASK-733.

### Placeholders the P2 caller actually supplies

From `asset_generators/prompt2_exercises.py:_build_prompt`. Using anything
outside this set is a `KeyError` at generation time:

```
word, pos, semantic_class, complexity_tier, definition, primary_collocate,
register, sense_fingerprint, sentences_json, active_levels_json,
used_distractors_json, level_3_sentence_index, level_5_sentence_index,
level_6_sentence_index
```

Note `complexity_tier` resolves via `_extract_tier()` →
`sentences[0].get('complexity_tier', 'T3')` — so it can silently be the T3
default if P1 did not stamp a tier. Check whether it actually is, for ja; if the
default is firing, tier-aware L1 is building on sand and you should say so.

`used_distractors_json` is supplied but **the ja L1 block ignores it** — worth
considering, since repeated distractors across an item set are their own defect.

### The render gate is all-or-nothing

`exercise_renderer._render_phonetic` (line ~470):

1. requires `len(options) >= 4`;
2. sends every distractor to the L1 judge;
3. **returns `None` for the entire variant if `len(kept) < 3`**;
4. otherwise keeps `kept[:3]`, shuffles with the correct answer, TTSes the
   target via `_generate_l1_audio`.

So a distractor-quality problem surfaces as **zero exercises**, not weak ones.
Any proposal must be evaluated on whether the item *renders*, not on keep rate.

The renderer reads only `is_valid=True` assets, so a level that fails validation
takes the whole P2 asset — L1, L3, L5, L6 — down with it.

### Validator

`services/vocabulary_ladder/validators.py`: `OPTION_COUNTS = {1: (4, 8)}`,
`DEFAULT_OPTION_COUNT = (4, 4)`. L1 may over-generate 4–8 options; L3/L5/L8 are
pinned at exactly 4 because their distractors are *not* individually judged.
Regression test: `tests/test_l1_option_overgeneration.py`. If a proposal changes
option counts, that test is the thing to update.

### Measured baseline (canary `ja-20260822-232552`, then TASK-735)

| metric | before TASK-735 | after |
|---|---|---|
| fabricated distractors | 2 of 6 (`向こうし`, `無蚊地`) | 0 of 7 |
| judge keeps, recorded sets | 0/12 | 5/12, zero false keeps |
| **variants that would render** | **0/4** | **1/2** |

Residual failures are generator-side and are all *padding*: the model finds 2–3
good candidates, then fills the remaining slots with whatever is nearby —
`向き` (genuinely 2 morae from むかし), `可笑し` (a classical form). The judge
called both correctly. **Padding under a count quota is the failure mode to
design against.**

### Existing harness — reuse it, don't rebuild it

| script | what it does |
|---|---|
| `scripts/smoke_task735_ja_l1.py --judge` | replays *recorded* distractor sets through two judge versions at temp 0. Isolates the prompt from generator variance. ~6 calls. |
| `scripts/smoke_task735_ja_l1.py --gen` | regenerates L1 from the stored `prompt1_core` asset and judges it live. ~$0.02/sense. |
| `scripts/apply_task735_ja_l1_fixes.py` | the versioned applier pattern: deactivate incumbent, insert `max(version)+1`, must_go/must_have token checks, per-row EOL preservation, verify-after-write. **Copy this pattern; do not invent a new one.** |

`SENSES` in the smoke script is currently `(34997 昔, 35001 機械)`. **n=2 is far
too small** — the TASK-735 numbers are over-fit to those two words and you should
treat them as illustrative, not as a baseline. Widening to ~10 senses is roughly
$0.20 and is the first thing worth doing.

### Things that are true and non-obvious

- 一/いち, 様, 度 and similar bound morphemes are in the ja sense pool and
  `run_content_build.phase_select` ranks by test frequency, so they sort to the
  **top**. They fail P1 before L1 ever runs. Not your problem here, but do not
  attribute their failures to L1.
- `qwen/qwen3.7-plus` is not a reasoning model. `qwen3.8-max` is, and needs
  `max_tokens ~16k` plus block-format output — JSON mode breaks on CJK.
- Judge calls log under `task_name = 'judge_ladder_l1_distractor'`, not under
  their `prompt_templates` key. Querying the wrong one shows zero rows.
- `scripts/batch_generate_furigana.py` exists; there may be reading/kana
  infrastructure worth reusing. **Verify before building on it.**

---

## Directions worth exploring — starting points, not a menu

Do not feel bound by these, and do not propose all of them. Pick what survives
contact with the constraints, and say what you rejected.

**Track A (prompt strategies):**

- *Generate-then-filter vs. constrain-then-generate.* The current prompt asks
  for good candidates directly. An alternative asks for a wide net of readings
  first and filters in a second pass.
- *Removing the count quota.* Padding is the observed failure. What happens if
  the prompt asks for "every real word you can find at one-mora distance,
  however many that is" with no target number?
- *Explicit lexical retrieval framing* — make the model enumerate from memory in
  a structured way (by mora position) rather than free-associate.
- *Tier-conditioned distractor distance*, per the constraint above.
- *Few-shot with worked negatives* — the en row's approach; the ja row has never
  had worked examples of a *rejected* candidate with the reasoning.

**Track B (architectures):**

- *Deterministic candidate generation.* Enumerate one-mora substitutions over
  the target's reading, intersect with an actual lexicon, and use the LLM only
  to rank and explain. This makes fabrication **structurally impossible** rather
  than merely discouraged. The open question is where the ja lexicon comes from —
  `dim_vocabulary` (small, ~2,400 ja rows), JMdict, or something already in the
  repo. Investigate and cost it.
- *Precomputed phonetic neighbour index.* Build the neighbour table once per
  language, then L1 generation is a lookup plus an explanation call. Changes the
  economics completely — worth costing even if you do not recommend it.
- *Retrieval from the existing vocabulary table*, guaranteeing every distractor
  is a word the system already knows and can gloss.
- *Dropping the separate judge* if candidates are attested by construction —
  what would the judge still be for? (Synonymy and pitch-accent collision, at
  minimum. Say so.)

---

## Deliverable — the report

One markdown file at `.claude/reviews/ja-l1-redesign-options.md`.

**Every proposal gets both registers.** This is a hard requirement, not a
stylistic preference — the report has two audiences and neither should have to
read the other's half.

For each proposal:

### Technical
- mechanism, concretely: which files, which prompt rows, which tables
- placeholder and JSON-key contract — confirm it survives, or state exactly what
  breaks and what would have to migrate
- how age tiers enter the design
- failure modes, and what happens on each
- cost per sense and per 150-sense build, in dollars and wall-clock
- what would have to change in `validators.py`, `exercise_renderer.py`, or the
  applier

### Plain English
- what this actually does, in language a non-engineer follows end to end
- why it would work where the current approach does not
- what it would feel like to the learner, if anything changes
- the honest catch — every design has one

Then, across all proposals:

- **A comparison table** — fabrication risk, expected render rate, cost, build
  effort, blast radius if it goes wrong.
- **A recommendation**, with your reasoning, and explicitly what you would *not*
  do and why.
- **A measurement plan**: for whichever you recommend, exactly what to run to
  know whether it worked, and what number would count as success. The render
  rate over ~10 senses is the metric that matters; keep rate is a diagnostic,
  not a target.
- **What you could not determine**, if anything, and what it would take.

Where you draft actual prompt text, put it in `data/eval/<task>/` as files and
reference them from the report — do not inline full prompts in the report body.

## Budget

The prior session cost $67 and a good share of that was iterating prompts
against two senses. **Ask before spending on live generation runs.** Reading
code, reading the live prompt rows, and reasoning about designs are free — do
all of that first, and propose the experiment before running it.
