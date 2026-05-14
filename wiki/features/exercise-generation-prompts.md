---
title: Exercise Generation Prompts — Verbatim Reference
type: feature-tech
status: complete
prose_page: ./exercises.md
last_updated: 2026-05-14
dependencies:
  - "prompt_templates table (Supabase) — model + provider are now first-class tracked columns"
  - "corpus_collocations table (Supabase) — used by L5 PMI gate"
  - "services/prompt_service.py — single choke point for model lookup"
  - "services/vocabulary_ladder/asset_pipeline.py"
  - "services/vocabulary_ladder/asset_generators/prompt1_core.py"
  - "services/vocabulary_ladder/asset_generators/prompt2_exercises.py"
  - "services/vocabulary_ladder/asset_generators/prompt3_transforms.py"
  - "services/vocabulary_ladder/asset_generators/_renderer.py"
  - "services/vocabulary_ladder/validators.py — VALID_POS / VALID_SEMANTIC_CLASSES include both English and Chinese enums; contains_target_whole_word falls back to substring match for non-ASCII targets"
breaking_change_risk: low
open_questions:
  - "Japanese (language_id=3) seeds remain absent for all three tasks."
  - "Chinese L5/L8 silently skip until corpus_collocations is populated for language_id=1 (PMI gate). Acceptable bootstrap state; revisit when Chinese collocation data lands."
  - "RESOLVED 2026-05-12: Chinese L1 audio now ships. LadderExerciseRenderer._render_phonetic pre-renders TTS into the L1 content jsonb at exercise insert time, voiced from dim_languages.tts_voice_ids (Azure neural voices, see migrations/seed_chinese_tts_voices.sql). Frontend renderPhonetic auto-plays and hides IPA/pinyin while audio is present."
  - "Upstream sense selection is not yet wired — `{sense_id}` is currently passed as the integer ID but `{sense_definition}` defaults to the existing definition. Once a true sense-disambiguation step lands, plumb the chosen sense's definition independently."
---

# Exercise Generation Prompts — Verbatim Reference

Verbatim copies of the LLM prompt templates that power the **vocabulary ladder
exercise generation pipeline**. The pipeline is a 3-prompt chain executed once
per `(sense_id, language_id)`; outputs are stored in `word_assets` and rendered
into rows of the `exercises` table.

These templates are the source of truth for every ladder exercise (levels 1–8)
served via [Vocab Dojo](./vocab-dojo.md) and embedded in
[Language Packs](./language-packs.md).

## Templating mechanism

All templates are rendered by
[services/vocabulary_ladder/asset_generators/_renderer.py](../../services/vocabulary_ladder/asset_generators/_renderer.py):

```python
_PLACEHOLDER_RE = re.compile(r'\{([A-Za-z_][A-Za-z0-9_]*)\}')
```

This regex substitutes `{name}` tokens (where `name` is a plain Python
identifier) and **leaves every other brace untouched** — including the literal
JSON examples at the bottom of each prompt. We therefore use **single braces**
in JSON literals, not f-string-style doubled braces. If a placeholder appears
in the template but is not passed as a kwarg, the renderer raises `KeyError`.

## Provenance (currently deployed)

All templates live in `public.prompt_templates` keyed by `(task_name,
language_id, version, is_active)`. They are loaded at runtime by
`services.prompt_service.get_template_config`. English (`language_id = 2`) and
Chinese (`language_id = 1`) are seeded; Japanese (`language_id = 3`) is not.

| Task | Lang | Active version | Default model | Migration |
|------|------|----------------|---------------|-----------|
| `vocab_prompt1_core` | EN | v4 | `google/gemini-2.5-flash-lite` | `migrations/restrict_l5_and_lock_l8_sentence.sql` |
| `vocab_prompt2_exercises` | EN | v3 | `anthropic/claude-opus-4-7` | `migrations/reframe_english_l1_listening.sql` |
| `vocab_prompt3_transforms` | EN | v2 | `anthropic/claude-opus-4-7` | `migrations/improve_vocab_pipeline_prompts.sql` |
| `vocab_prompt1_core` | CN | v1 | `qwen/qwen-2.5-72b-instruct` | `migrations/seed_chinese_vocab_prompts.sql` |
| `vocab_prompt2_exercises` | CN | v1 | `qwen/qwen-max` | `migrations/seed_chinese_vocab_prompts.sql` |
| `vocab_prompt3_transforms` | CN | v1 | `qwen/qwen-max` | `migrations/seed_chinese_vocab_prompts.sql` |

The Chinese templates mirror the English structure (same numbered rule layout,
same numeric-keyed JSON schema) but with Chinese-native rules: a Hanzi
character-count tier table, a sense-match substring rule (replaces the English
whole-word rule), L1 reframed as a listening exercise (audio → pick correct
Hanzi, with tonal-confusable distractors), L4 reinterpreted as compound-completion
(Chinese has no inflectional morphology), L6/L7 errors using Chinese categories
(wrong measure word, misplaced aspect particle, word-order error, misused
directional/resultative complement), and Chinese-language enum values
(`具体名词` / `语料` / `生成` / `正式` / etc.).

**P1 v4 changes vs v3** (deployed 2026-05-03):
- Rule 7 tightened: `primary_collocate` is null unless the (target, collocate) pair is a fixed lexical collocation, not just a frequent co-occurrence.
- Rule 14 (new): when `primary_collocate` is non-null, at least one sentence must contain it as a whole word — gives L8 a guaranteed anchor.
- Rule 20 verification step picks up the new collocate-coverage check.

The currently-deployed v3 / v2 templates are reproduced verbatim below. Earlier
versions (P1 v2 / v1, P2 v1, P3 v1) are kept in the [Historical reference](#historical-reference-deactivated)
section at the bottom of this page.

---

# Active templates (deployed)

These three templates are currently `is_active = true` in
`public.prompt_templates`. Compared to the previous versions they add:

- **Tier calibration tables** mapping `complexity_tier` → hard sentence-level
  constraints (length, tense ceiling, register, abstraction).
- **Sense lock** (Prompt 1) and **`sense_fingerprint` propagation** (Prompts 2/3),
  so all downstream items align to a single chosen sense.
- **Register lock** so generated items don't drift between formal/informal
  unless a level (e.g. P2 L6) deliberately tests pragmatic misuse.
- **Substring / whole-word audit** preventing the LLM from treating "new" as
  matching "knew", "renew", etc.
- **Mixed-L1 guardrail** discouraging false-friend or transfer-error distractors
  that only fail learners with a specific L1.
- **`used_distractors_json` deduping** so the same distractor doesn't repeat
  across levels in a single item set.
- **Pre-output verification** rules (correct-option count, distractor uniqueness,
  whole-word check, JSON validity).
- **L1 listening-only distractor rules** (homophones, near-homophones, minimal
  pairs — never visual lookalikes) and **L8 anti-substitution test** for
  collocation distractors. L1 is rendered as an audio-then-MCQ listening
  exercise; visual-similarity distractors would test the wrong skill.
- New output fields on Prompt 1: `register` and `sense_fingerprint`.

## Deployment artefacts

- **Initial v3/v2 deploy:** [migrations/improve_vocab_pipeline_prompts.sql](../../migrations/improve_vocab_pipeline_prompts.sql)
  — deactivates the previous active rows and inserts P1 v3 / P2 v2 / P3 v2.
- **L5 restriction + L8 sentence-coverage:** [migrations/restrict_l5_and_lock_l8_sentence.sql](../../migrations/restrict_l5_and_lock_l8_sentence.sql)
  — deactivates P1 v3 and inserts P1 v4 with tightened collocate rule and
  collocate-must-appear-in-a-sentence requirement.
- **`get_distractors` auth fix:** [migrations/get_distractors_drop_auth_check.sql](../../migrations/get_distractors_drop_auth_check.sql)
  — removes the `auth.uid() IS NULL` raise that was failing the admin
  pipeline's service-role calls.
- **Pipeline-side L5 gate:** `services/vocabulary_ladder/asset_pipeline.py`
  drops level 5 from `active_levels` unless `corpus_collocations` has a
  `pmi_score >= 5.0` row backing the (lemma, primary_collocate) pair.
- **Generator plumbing:**
  - [services/vocabulary_ladder/config.py](../../services/vocabulary_ladder/config.py) —
    `PROMPT1_KEY_MAP` extended with `"10": "register"` and `"11": "sense_fingerprint"`.
  - [services/vocabulary_ladder/asset_generators/prompt1_core.py](../../services/vocabulary_ladder/asset_generators/prompt1_core.py) —
    `_build_prompt` now passes `sense_id` and `sense_definition` (the latter
    currently mirrors `existing_definition` until upstream sense selection lands).
  - [services/vocabulary_ladder/asset_generators/prompt2_exercises.py](../../services/vocabulary_ladder/asset_generators/prompt2_exercises.py) —
    `generate()` accepts an optional `used_distractors: list[str]`; `_build_prompt`
    passes `register`, `sense_fingerprint`, and `used_distractors_json`.
  - [services/vocabulary_ladder/asset_generators/prompt3_transforms.py](../../services/vocabulary_ladder/asset_generators/prompt3_transforms.py) —
    same change as P2. Plus three follow-up fixes shipped 2026-05-03:
    `_remap_level_4` and `_remap_level_8` now read the options array from
    sub-key `"1"` (matching the v2 template), `_pick_l8_sentence_index`
    scans the full 10-sentence pool for a sentence containing the
    collocate, and `_call_with_retry` falls back to a text-mode salvage
    that uses `json.JSONDecoder.raw_decode` to recover individual top-level
    levels when strict JSON parsing fails.

---

## Prompt 1 v4 (active) — `vocab_prompt1_core`

```
Role: Expert computational linguist generating English vocabulary assets.

Target word: {word}
Existing definition: {existing_definition}
Sense ID (optional): {sense_id}
Sense definition (optional): {sense_definition}
Learner tier: {complexity_tier}

Corpus sentences already approved (use these unchanged):
{corpus_sentences_json}

Task: Generate the base linguistic assets for this vocabulary word for exactly one sense only.

Tier calibration (mandatory)
Map {complexity_tier} to these hard constraints. Do not exceed them in generated learner-facing text.

| Tier | Name | Age Analog | Max sentence length | Tense/aspect ceiling | Topic/context register | Abstract language |
|------|------|------------|---------------------|----------------------|------------------------|-------------------|
| 1 | The Toddler | 4–5 | 12 words | Simple present/past only | Home, animals, food, concrete actions | Forbidden |
| 2 | The Primary Schooler | 8–9 | 18 words | Future simple allowed | School, family, hobbies, familiar places | Forbidden |
| 3 | The Young Teen | 13–14 | 25 words | Present/past continuous, perfect simple | Emotions, opinions, social events | Minimal |
| 4 | The High Schooler | 16–17 | 35 words | All perfects, passive, first/second conditional | Academic, media, abstract social issues | Allowed |
| 5 | The Uni Student | 19–21 | 45 words | Modals, embedded clauses, inversion | University, professional, technical | Expected |
| 6 | The Educated Professional | 30+ | No hard cap | Any structure including rare patterns | Technical, literary, highly nuanced | Full range |

Hard rules:
1. All output values must be in English only.
2. Output valid JSON only using numeric keys.
3. Return the part of speech as one of:
   noun, verb, adjective, adverb, preposition, conjunction, pronoun, determiner, interjection
4. Return the semantic class as one of:
   concrete_noun, abstract_noun, action_verb, state_verb, adjective, adverb, other
5. Sense lock:
   - Generate assets for exactly ONE sense only.
   - If {sense_id} or {sense_definition} is provided, lock to that sense.
   - Otherwise infer the sense from the approved corpus sentences.
   - If the corpus sentences mix senses, use the majority sense and keep all generated content aligned to it.
6. Return a definition suitable for the learner tier.
   - If {existing_definition} is provided and is adequate for the chosen sense and tier, reuse it.
   - If not adequate, rewrite it in simpler or more precise English while preserving the same sense.
7. Return the primary_collocate ONLY if the (target word, collocate) pair is a fixed lexical collocation. A fixed collocation means:
   - Swapping the collocate for a near-synonym would produce a noticeably less natural sentence in MOST contexts (e.g. "make a decision" → "do a decision" sounds wrong; "heavy rain" → "weighty rain" sounds wrong).
   - The pair appears together far more often than chance would predict.
   It is NOT enough that the collocate co-occurs frequently within a topic domain. For example "personalize" co-occurs often with "advertising", "marketing", "promotion", "publicity" — none of these are fixed collocations of "personalize" because they are interchangeable. In that situation return null.
   When in doubt, return null. False positives produce broken exercises.
8. Determine the register of the chosen sense as one of:
   formal, neutral, informal, technical
9. Return exactly 10 correct example sentences total.
   - Use the provided corpus sentences unchanged.
   - Generate exactly {sentences_needed} additional sentences so the total is 10.
10. All 10 sentences must:
   - express the SAME sense of the word;
   - fit the learner tier;
   - respect the register identified in Rule 8.
11. Syntactic frame diversity mandate:
   - Across all 10 sentences, the target word must appear in at least three distinct grammatical roles or frames.
   - No more than four sentences may use an identical frame.
12. For each sentence, return the exact target word as it appears in that sentence.
   - It must be a whole word only, never a substring of another word.
   - Match case and inflection exactly as written in the sentence.
13. Substring audit (mandatory verification):
   - Before returning output, verify that every sentence uses the target as a free-standing whole word.
   - If the target is "new", then "knew", "renew", and "renewal" do NOT count.
   - Reject and regenerate any violating sentence.
14. Collocate sentence coverage (only when primary_collocate is non-null):
   - At least one of the 10 sentences MUST contain the primary_collocate as a free-standing whole word.
   - Prefer to place it in 2–3 of the 10 sentences so downstream exercises have flexibility.
   - If no natural sentence using both target and primary_collocate together can be written within the tier constraints, return null for primary_collocate instead.
15. Return the pronunciation as a natural reading string.
16. Return the IPA pronunciation as a standard broad dictionary-style transcription.
17. Return the syllable count as an integer.
18. Return 3–5 morphological forms with labels.
   - Use contemporary standard English forms.
   - If a form is archaic, obsolete, or dialectal, avoid it unless it is still widely recognized.
19. Create a short sense fingerprint for downstream prompts.
   - It must be a concise English string that uniquely identifies the chosen sense.
   - Format: "[part_of_speech] | [8–14 word sense summary]"
20. Pre-output verification:
   - Confirm the JSON is valid.
   - Confirm there are exactly 10 sentences.
   - Confirm every generated sentence fits the tier constraints.
   - Confirm no sentence violates the whole-word rule.
   - If primary_collocate is non-null, confirm at least one sentence contains it as a whole word.

Output schema:
"1" = part_of_speech (string)
"2" = semantic_class (string)
"3" = definition (string)
"4" = primary_collocate (string or null) — null is the safe default; only emit a string for genuine fixed collocations per Rule 7
"5" = pronunciation (string, natural reading)
"6" = ipa (string)
"7" = syllable_count (integer)
"8" = array of sentence objects, each:
      "1": full_sentence, "2": exact_target_word, "3": source ("corpus" or "generated"), "4": complexity_tier
"9" = array of morphological form objects, each:
      "1": form_text, "2": form_label
"10" = register (string: formal / neutral / informal / technical)
"11" = sense_fingerprint (string)

Return JSON only. No prose, no markdown fences.

Literal JSON template:
{
  "1": "",
  "2": "",
  "3": "",
  "4": null,
  "5": "",
  "6": "",
  "7": 0,
  "8": [
    {"1": "", "2": "", "3": "corpus", "4": ""},
    {"1": "", "2": "", "3": "generated", "4": ""}
  ],
  "9": [
    {"1": "", "2": ""}
  ],
  "10": "",
  "11": ""
}
```

---

## Prompt 2 v3 (active) — `vocab_prompt2_exercises`

**v3 vs v2 (deployed 2026-05-07, [migrations/reframe_english_l1_listening.sql](../../migrations/reframe_english_l1_listening.sql)):**
- L1 reframed from "Phonetic/Orthographic Recognition" with form-similarity distractors (Levenshtein, first/last letter, homophones) to "Listening Recognition" with phonetic-only distractors (homophones, near-homophones, minimal pairs, mishear-able rhymes). The L1 renderer at [services/vocabulary_ladder/exercise_renderer.py:155](../../services/vocabulary_ladder/exercise_renderer.py#L155) returns `pronunciation` / `ipa` so the frontend plays audio — visual-similarity distractors were testing the wrong skill.
- Rule 5 (whole-word substring audit) preserved verbatim from v2.
- L3, L5, L6 unchanged.

The full text below shows the v3 L1 listening block; verbatim P2 text in the database for v3 is the canonical source. The richer rule list shown here (mixed-L1 guardrail, sense-fingerprint, used_distractors deduping) reflects design intent that has accreted in this wiki page over time and is partly aspirational — the actual deployed prompt is more concise, see the migration file.



```
Role: Expert computational linguist generating English vocabulary exercises.

Target word: {word}
Part of speech: {pos}
Semantic class: {semantic_class}
Tier: {complexity_tier}
Definition: {definition}
Primary collocate: {primary_collocate}
Register: {register}
Sense fingerprint: {sense_fingerprint}

Base sentences:
{sentences_json}

Generate ONLY the exercise levels listed here:
{active_levels_json}

Used distractors already assigned elsewhere in this item set:
{used_distractors_json}

Sentence indexing note:
- All referenced sentence indices are exactly as provided by the calling system.

Tier calibration (mandatory)
All learner-facing text you generate must fit the tier.

| Tier | Name | Age Analog | New sentence difficulty | Explanation difficulty |
|------|------|------------|--------------------------|------------------------|
| 1 | The Toddler | 4–5 | very short, concrete only | 4–8 words |
| 2 | The Primary Schooler | 8–9 | short, familiar contexts | 5–10 words |
| 3 | The Young Teen | 13–14 | moderate length, basic abstraction | 6–14 words |
| 4 | The High Schooler | 16–17 | more complex syntax, abstract themes | 8–18 words |
| 5 | The Uni Student | 19–21 | nuanced academic/professional language | 8–24 words |
| 6 | The Educated Professional | 30+ | full range, subtle distinctions allowed | 8–30 words |

Global rules:
1. All output values must be in English only.
2. Output valid JSON only using numeric keys.
3. For every option object:
   - "1" = option text
   - "2" = true/false
   - "3" = short pedagogical explanation
4. Mixed-L1 guardrail:
   - This system serves mixed-L1 cohorts.
   - Do NOT rely on L1-specific false friends, transfer patterns, or culturally narrow assumptions.
5. Sense lock:
   - Every exercise must match {sense_fingerprint}.
   - Do not generate distractors or wrong examples that depend on a different sense.
6. Register lock:
   - Respect {register} in all normal items.
   - Only Level 6 may deliberately violate register for pragmatic misuse.
7. Treat the target word as a discrete whole word.
   - Apply a whole-word boundary check mentally before returning output.
8. If a level is not included in {active_levels_json}, omit it entirely.
9. Do not reuse any distractor present in {used_distractors_json}.
10. Do not repeat the same distractor across multiple levels in this response.
11. Explanations must teach the learner why the answer is correct or wrong.
12. Do not use bare synonyms of the target as distractors unless the level allows form-similar items.
13. Do not use antonyms as distractors for Tier 1 or Tier 2.
14. Pre-output verification:
   a. Exactly one option per multiple-choice level has "2": true.
   b. No distractor is duplicated.
   c. No distractor violates the whole-word rule.

Level "1" (Listening Recognition):
- Scenario: the learner HEARS the target word spoken aloud (TTS) and selects which of 4 written options matches what they heard.
- Return 4 options total.
- Exactly 1 correct option = the target word.
- Exactly 3 distractors must be PHONETICALLY confusable with the target by ear (audio confusables, not visual).
- Use a mix of at least two of these phonetic-distractor types:
  (i) homophones / near-homophones (e.g. "their" ↔ "there" / "they're"; "knew" ↔ "new");
  (ii) minimal pairs differing by one phoneme (e.g. "ship" ↔ "sheep" / "chip");
  (iii) same-stress same-syllable-count rhymes a learner could plausibly mishear.
- Distractors must NOT be selected on visual / spelling similarity alone — "tough" and "though" look alike but sound completely different and would make the audio test trivial.
- Distractors must NOT be semantic synonyms, antonyms, translation equivalents, or other inflections of the target.
- Level 1 is the only level where homophones or near-homophones are allowed.
- Each option's "3" briefly states the phonetic relationship to the target (homophone, minimal pair, rhyme).

Level "3" (Cloze Completion):
- Use sentence at index {level_3_sentence_index}.
- Correct option = the target word exactly as it appears in that sentence, including inflection.
- Return 4 options total.
- 3 distractors must:
  - be the same part of speech as the correct answer;
  - be grammatically valid in the sentence;
  - be contextually wrong.
- Anti-substitution test:
  - If replacing the target with a close synonym would make the distractor also sound natural, reject that distractor.
- Do NOT use homophones or near-homophones of the target.

Level "5" (Collocation Gap Fill) — only if included:
- Use sentence at index {level_5_sentence_index}.
- Correct option = the primary collocate.
- Return 4 options total.
- 3 distractors must:
  - be the same part of speech as the correct collocate;
  - be semantically near enough to tempt a learner;
  - be collocationally unnatural with the target word in this sentence.
- Distractor explanations must say specifically why the pairing is unnatural.
- If {primary_collocate} is null, omit Level 5 even if requested.

Level "6" (Semantic Discrimination):
- Use sentence at index {level_6_sentence_index} as the correct usage.
- Generate 3 new wrong sentences that all contain the target word as a whole word.
- The 3 wrong sentences must be grammatical, but semantically or pragmatically inappropriate.
- At least 1 must be semantically inappropriate (factually or logically impossible).
- At least 1 must be pragmatically inappropriate (wrong register, social fit, or usage norm).
- Each wrong sentence explanation must label the misuse type: "semantic" or "pragmatic".

Return JSON only. No prose, no markdown fences.

Literal JSON template:
{
  "1": [
    {"1": "", "2": true, "3": ""},
    {"1": "", "2": false, "3": ""},
    {"1": "", "2": false, "3": ""},
    {"1": "", "2": false, "3": ""}
  ],
  "3": [
    {"1": "", "2": true, "3": ""},
    {"1": "", "2": false, "3": ""},
    {"1": "", "2": false, "3": ""},
    {"1": "", "2": false, "3": ""}
  ],
  "5": [
    {"1": "", "2": true, "3": ""},
    {"1": "", "2": false, "3": ""},
    {"1": "", "2": false, "3": ""},
    {"1": "", "2": false, "3": ""}
  ],
  "6": {
    "1": 0,
    "2": [
      {"1": "", "2": "semantic: "},
      {"1": "", "2": "pragmatic: "},
      {"1": "", "2": ""}
    ]
  }
}
```

---

## Prompt 2 v4 (active, 2026-05-14) — L3 strengthening

**Change scope:** [migrations/cloze_distractor_quality.sql](../../migrations/cloze_distractor_quality.sql) supersedes v3 by replacing **only the Level 3 block** of the English (language_id=2) template; L1, L5, L6 are preserved verbatim from v3. A parallel Chinese (language_id=1) update bumps that template from v1 → v2 with the equivalent L3 strengthening (see migration for the Chinese text). v3/v1 are marked `is_active=false` but retained for audit.

Replacement L3 block (English v4):

```
Level "3" (Cloze Completion):
- Use sentence at index {level_3_sentence_index}.
- Correct option = the target word as it appears in that sentence (its exact inflected form).
- 3 distractors: same POS as the target, grammatically valid in the slot, but contextually wrong.
- Do NOT use any homophone or near-homophone of the target as a distractor here.
- MANDATORY per-distractor self-check before emitting each distractor:
  (a) Failure dimension — tag each distractor with exactly one reason it fails in this sentence, chosen from:
        - "semantic"      : refers to a wrong class of referent / wrong concept
        - "collocational" : does not co-occur naturally with the surrounding lexis in this sentence
        - "aspectual"     : wrong lexical aspect / event structure (stative vs telic vs activity)
        - "register"      : wrong formality, domain, or social fit for this sentence
        - "valency"       : wrong argument structure (e.g. transitive vs intransitive, wrong preposition complement)
      Put the tag in the option's "3" (explanation) as a leading label, e.g. "semantic: ...".
  (b) Substitution audit — silently consider one common synonym of the target word and ask: if I swapped that synonym in for the target, would my distractor become a valid completion? If yes, REJECT this distractor and choose a different one. The distractor must be wrong for THIS sentence even under near-synonym variants of the target.
- Across the 3 distractors, at least TWO distinct failure dimensions must appear. No four near-identical "wrong-but-similar" options.
- Final pre-output check: silently re-read the sentence with each distractor in the blank. If any reads as natural, replace it before emitting.
```

Prompt-level self-check is supplemented by a runtime **Distractor Judge** pass — see [Prompt: `cloze_distractor_judge` v1](#prompt-cloze_distractor_judge-v1) below.

---

## Prompt: `cloze_distractor_judge` v1 (active, 2026-05-14)

New task added to `prompt_templates`. A cheap-model verifier (default `google/gemini-2.5-flash-lite`) that rules on each distractor produced by the cloze generator. Any distractor judged to be acceptable in context is rejected upstream by [`services/exercise_generation/cloze_judge.py`](../../services/exercise_generation/cloze_judge.py); the rejection count, model, and version are recorded under `exercises.tags.cloze_judge`.

Asymmetric design: the cloze generator runs on a strong model (Opus/Qwen-max), while the judge runs on a fast cheap model. Pipelines that invoke the judge:
- [services/vocabulary_ladder/exercise_renderer.py](../../services/vocabulary_ladder/exercise_renderer.py) `_render_cloze` — drops rejects, returns `None` if fewer than 3 valid distractors remain so the variant is skipped.
- [services/exercise_generation/generators/cloze.py](../../services/exercise_generation/generators/cloze.py) `generate_one` — on rejection, retries `_generate_distractors` once; if still short, returns `None` and the orchestrator moves on to the next sentence.

```
You are a strict cloze-test judge. A learner is shown a sentence with a blank and 4 options. Exactly ONE option is the intended correct answer; the other 3 must each be clearly wrong in this sentence. Your job is to rule on each candidate distractor and flag any that could in fact pass as a valid completion.

Sentence with blank: {sentence_with_blank}
Intended correct answer: {correct_answer}
Candidate distractors:
{distractors_numbered}

For EACH distractor, rule as follows:
- "keep"   = grammatical in the slot but CLEARLY semantically, collocationally, aspectually, register-wise, or valency-wise wrong in THIS sentence. The distractor would never be marked correct by a competent native speaker.
- "reject" = the distractor could itself be selected by a competent reader as a valid completion of this sentence (i.e. it is grammatically AND semantically acceptable, even if less idiomatic than the intended answer). Synonyms, near-synonyms, and contextually appropriate alternatives must all be REJECTed.

Be conservative: if you are unsure whether a distractor is acceptable in context, REJECT it. A good cloze test has zero ambiguous distractors.

Return JSON ONLY, keyed by the 1-based index of each distractor, with verdict and a short reason (<= 12 words):
{"1": {"verdict": "keep|reject", "reason": "..."}, "2": {"verdict": "keep|reject", "reason": "..."}, "3": {"verdict": "keep|reject", "reason": "..."}}

No prose outside the JSON. No markdown fences.
```

Failure mode on judge errors (template missing, LLM down, malformed JSON): the judge falls back to keeping every distractor and logs a warning. This is intentional — we'd rather degrade to the generator's own quality than drop content.

---

## Prompt: `cloze_distractor_generation` v2 (active, 2026-05-14) — legacy generator

Strengthened version of the legacy single-block cloze distractor prompt used by [services/exercise_generation/generators/cloze.py](../../services/exercise_generation/generators/cloze.py) for non-vocab-ladder sources (grammar, conversation, collocation). v1 marked inactive. Same failure-dimension + substitution-audit rules as Prompt 2 v4 L3, in single-block form.

```
Sentence: {original_sentence}
Blank: {sentence_with_blank}
Correct answer: {correct_answer}
Learner level: {complexity_tier}

Generate exactly 3 distractors that are wrong completions of this sentence.

Hard rules:
1. Each distractor must be the same part of speech as the correct answer.
2. Each distractor must be grammatically valid in the blank slot.
3. Each distractor must be contextually WRONG in this specific sentence.
4. Distractors must NOT be homophones, near-homophones, inflected variants of the correct answer, or substrings of it.

Mandatory per-distractor self-check before emitting each one:
(a) Failure dimension — assign exactly one reason it fails here, from:
    - "semantic"      : wrong referent class / wrong concept
    - "collocational" : does not co-occur naturally with the surrounding lexis
    - "aspectual"     : wrong lexical aspect / event structure
    - "register"      : wrong formality / domain / social fit
    - "valency"       : wrong argument structure / wrong complement
(b) Substitution audit — consider one common synonym of the correct answer and silently swap it in. If your distractor would become a valid completion under that synonym, REJECT the distractor and pick a different one.

Across the 3 distractors, at least TWO distinct failure dimensions must appear.
Re-read the sentence with each distractor in the blank as a final check. If any reads naturally, replace it before emitting.

Return JSON:
{"distractors": ["word1","word2","word3"], "distractor_tags": {"word1":"semantic","word2":"collocational","word3":"valency"}, "explanation": "Brief explanation of why the correct answer is right."}

Put the correct answer first in any option lists — do NOT shuffle.
```

---

## Prompt 3 v2 (active) — `vocab_prompt3_transforms`

```
Role: Expert computational linguist generating English grammar and usage exercises.

Target word: {word}
Part of speech: {pos}
Semantic class: {semantic_class}
Tier: {complexity_tier}
Primary collocate: {primary_collocate}
Register: {register}
Sense fingerprint: {sense_fingerprint}

Base sentences:
{sentences_json}

Morphological forms available:
{morphological_forms_json}

Generate ONLY the exercise levels listed here:
{active_levels_json}

Used distractors already assigned elsewhere in this item set:
{used_distractors_json}

Sentence indexing note:
- All referenced sentence indices are exactly as provided by the calling system.

Tier calibration (mandatory)
All learner-facing text must fit the tier.

| Tier | Name | Age Analog | Error subtlety |
|------|------|------------|----------------|
| 1 | The Toddler | 4–5 | very obvious |
| 2 | The Primary Schooler | 8–9 | obvious |
| 3 | The Young Teen | 13–14 | moderate |
| 4 | The High Schooler | 16–17 | moderately subtle |
| 5 | The Uni Student | 19–21 | subtle |
| 6 | The Educated Professional | 30+ | very subtle |

Global rules:
1. All output values must be in English only.
2. Output valid JSON only using numeric keys.
3. For option objects: "1" = text, "2" = true/false, "3" = explanation.
4. Mixed-L1 guardrail:
   - This system serves mixed-L1 cohorts.
   - Do NOT use L1-specific transfer errors or false-friend traps.
5. Sense lock:
   - All exercises must align with {sense_fingerprint}.
6. Register lock:
   - Normal items must respect {register}.
   - An incorrect sentence may violate grammar, but it must still be plausible.
7. Treat the target word as a discrete whole word.
8. Do not reuse any distractor present in {used_distractors_json}.
9. If a level is not included in {active_levels_json}, omit it entirely.

Level "4" (Morphology Slot):
- Use sentence at index {level_4_sentence_index}.
- Correct option = the exact target word as it appears in that sentence.
- Return 4 options total.
- 3 distractors must be real morphological siblings of the SAME lemma.
- Distractors must be wrong for this exact sentence context.
- Required metadata keys attached to the level object (not the options):
  - "4" = base_form
  - "5" = form_label
  - "6" = sentence_index

Level "7" (Spot Incorrect Sentence):
- Use sentences at indices {level_7_correct_indices} as 3 correct sentences.
- Generate 1 new incorrect sentence containing the target word spelled correctly.
- The incorrect sentence must contain exactly ONE structural error from this whitelist:
  - article omission or misuse
  - subject-verb agreement error
  - countable/uncountable noun misuse
  - basic word order inversion
  - tense/aspect mismatch
- Scale error type by tier.
- Output keys directly on the level object:
  - "1" = incorrect_sentence
  - "2" = corrected_sentence
  - "3" = error_description
  - "4" = array of correct_sentence_indices

Level "8" (Collocation Repair) — only if included:
You are building a multiple-choice exercise that tests whether a learner knows the natural collocate of "{word}" in a specific sentence.

The source sentence (sentence at index {level_8_sentence_index}) is:
"{level_8_sentence_text}"

The natural, correct collocate of "{word}" in this sentence is exactly:
"{level_8_collocate_word}"

Produce 4 options for the learner:
- Option 1 (correct): the text MUST equal "{level_8_collocate_word}" character-for-character.
- Options 2, 3, 4 (distractors): three different words you generate.
- Each distractor must NOT collocate naturally with "{word}" in this sentence.
- Distractor anti-substitution test: mentally replace "{word}" with a close synonym in the sentence. If the sentence would still sound natural with that distractor, reject the distractor.

Hard rules for Level "8":
- Option 1 MUST have "2": true. The distractors have "2": false.
- Do not return a distractor identical to "{level_8_collocate_word}".
- Required metadata keys attached to the level object (not the options):
  - "4" = sentence_index
  - "5" = error_collocate (one of the distractors you generated)

Return JSON only. No prose, no markdown fences.

Literal JSON template:
{
  "4": {
    "1": [
      {"1": "", "2": true, "3": ""},
      {"1": "", "2": false, "3": ""},
      {"1": "", "2": false, "3": ""},
      {"1": "", "2": false, "3": ""}
    ],
    "4": "",
    "5": "",
    "6": 0
  },
  "7": {
    "1": "",
    "2": "",
    "3": "",
    "4": [0, 1, 2]
  },
  "8": {
    "1": [
      {"1": "", "2": true, "3": ""},
      {"1": "", "2": false, "3": ""},
      {"1": "", "2": false, "3": ""},
      {"1": "", "2": false, "3": ""}
    ],
    "4": 0,
    "5": ""
  }
}
```

---

# Historical reference (deactivated)

These earlier versions are kept for archaeological reasons; they are
`is_active = false` in `public.prompt_templates`.

## Prompt 1 — Core Asset Generator (`vocab_prompt1_core`)

**Purpose:** classify a word and produce its base linguistic assets — POS,
semantic class, definition, IPA, syllable count, morphological forms, and 10
example sentences (corpus-first, generate the rest).

### v3 (deactivated by `restrict_l5_and_lock_l8_sentence.sql`) — pre-collocation-restriction

Replaced by v4 because Rule 7 was permissive enough that the LLM happily
emitted `primary_collocate` for words like "personalize" with no fixed
collocate (downstream L5 then produced synonym-soup distractors). v4 also
adds Rule 14 to guarantee L8 has a sentence with the collocate.

Source: [migrations/improve_vocab_pipeline_prompts.sql](../../migrations/improve_vocab_pipeline_prompts.sql) (P1 v3 INSERT block)

### v2 (deactivated by `improve_vocab_pipeline_prompts.sql`) — 10 sentences

Source: [migrations/phase8_momentum_bands.sql:952-986](../../migrations/phase8_momentum_bands.sql#L952-L986)

```
Role: Expert computational linguist generating English vocabulary assets.

Target word: {word}
Existing definition: {existing_definition}
Learner tier: {complexity_tier}

Corpus sentences already approved (use these unchanged):
{corpus_sentences_json}

Task: Generate the base linguistic assets for this vocabulary word.

Rules:
1. All output values must be in English only.
2. Return the part of speech as one of: noun, verb, adjective, adverb, preposition, conjunction, pronoun, determiner, interjection.
3. Return the semantic class as one of: concrete_noun, abstract_noun, action_verb, state_verb, adjective, adverb, other.
4. Return a definition suitable for the learner tier. If an existing definition is provided and adequate, reuse it.
5. Return the primary collocate for this word if one is strongly relevant; otherwise return null.
6. Return exactly 10 correct example sentences total. Use the provided corpus sentences unchanged. Generate exactly {sentences_needed} additional sentences so the total is 10.
7. Every sentence must place the word in a meaningfully different context or sentence structure.
8. For each sentence, return the exact substring used for the target word as it appears in that sentence.
9. Return the IPA pronunciation.
10. Return the syllable count.
11. Return 3-5 morphological forms with labels (e.g. past_tense, plural, comparative).
12. Output valid JSON only using numeric keys.

Output schema:
"1" = part_of_speech (string)
"2" = semantic_class (string)
"3" = definition (string)
"4" = primary_collocate (string or null)
"5" = pronunciation (string, natural reading)
"6" = ipa (string)
"7" = syllable_count (integer)
"8" = array of sentence objects, each: {"1": full_sentence, "2": exact_target_substring, "3": source ("corpus" or "generated"), "4": complexity_tier}
"9" = array of morphological form objects, each: {"1": form_text, "2": form_label}
```

### v1 (deactivated by `phase8_momentum_bands.sql`) — 6 sentences

Superseded by v2 on the migration that introduced 10-sentence pools. Kept
here for historical reference; `is_active = false` in the database.

Source: [migrations/vocabulary_ladder_schema.sql:155-189](../../migrations/vocabulary_ladder_schema.sql#L155-L189)

```
Role: Expert computational linguist generating English vocabulary assets.

Target word: {word}
Existing definition: {existing_definition}
Learner tier: {complexity_tier}

Corpus sentences already approved (use these unchanged):
{corpus_sentences_json}

Task: Generate the base linguistic assets for this vocabulary word.

Rules:
1. All output values must be in English only.
2. Return the part of speech as one of: noun, verb, adjective, adverb, preposition, conjunction, pronoun, determiner, interjection.
3. Return the semantic class as one of: concrete_noun, abstract_noun, action_verb, state_verb, adjective, adverb, other.
4. Return a definition suitable for the learner tier. If an existing definition is provided and adequate, reuse it.
5. Return the primary collocate for this word if one is strongly relevant; otherwise return null.
6. Return exactly 6 correct example sentences total. Use the provided corpus sentences unchanged. Generate exactly {sentences_needed} additional sentences so the total is 6.
7. Every sentence must place the word in a meaningfully different context or sentence structure.
8. For each sentence, return the exact substring used for the target word as it appears in that sentence.
9. Return the IPA pronunciation.
10. Return the syllable count.
11. Return 3-5 morphological forms with labels (e.g. past_tense, plural, comparative).
12. Output valid JSON only using numeric keys.

Output schema:
"1" = part_of_speech (string)
"2" = semantic_class (string)
"3" = definition (string)
"4" = primary_collocate (string or null)
"5" = pronunciation (string, natural reading)
"6" = ipa (string)
"7" = syllable_count (integer)
"8" = array of sentence objects, each: {"1": full_sentence, "2": exact_target_substring, "3": source ("corpus" or "generated"), "4": complexity_tier}
"9" = array of morphological form objects, each: {"1": form_text, "2": form_label}
```

---

## Prompt 2 — Lexical & Semantic Exercises (`vocab_prompt2_exercises`)

**Purpose:** generate exercise content for ladder levels 1 (phonetic
recognition), 3 (cloze completion), 5 (collocation gap fill), and 6 (semantic
discrimination). Single LLM call covers all included levels; the generator
omits any level not in `active_levels_json`.

### v1 (deactivated)

Source: [migrations/vocabulary_ladder_schema.sql:200-241](../../migrations/vocabulary_ladder_schema.sql#L200-L241). Superseded by v2 (deployed in `improve_vocab_pipeline_prompts.sql`) and then v3 (the current active, listening reframe). The L1 wording shown below ("Phonetic/Orthographic Recognition", "look or sound similar") is a historical artefact — the active v3 explicitly excludes visual-similarity distractors.

```
Role: Expert computational linguist generating English vocabulary exercises.

Target word: {word}
Part of speech: {pos}
Semantic class: {semantic_class}
Tier: {complexity_tier}
Definition: {definition}
Primary collocate: {primary_collocate}

Base sentences:
{sentences_json}

Generate ONLY the exercise levels listed here: {active_levels_json}

Rules:
1. All output values must be in English only.
2. Output valid JSON only using numeric keys.
3. For every option: "1" = option text, "2" = true/false (correct?), "3" = explanation.
4. Explanations must be short, clear, and pedagogical.

Level "1" (Phonetic/Orthographic Recognition):
- Return 4 options. 1 correct = target word. 3 distractors look or sound similar.
- Distractors must NOT be semantic synonyms. Only form similarity.

Level "3" (Cloze Completion):
- Use sentence at index {level_3_sentence_index}.
- Correct option = the target substring from that sentence.
- 3 distractors: same POS, grammatically valid in context, but contextually wrong.

Level "5" (Collocation Gap Fill) — only if included:
- Use sentence at index {level_5_sentence_index}.
- Correct option = the primary collocate.
- 3 distractors: semantically close but collocationally unnatural with the target word.

Level "6" (Semantic Discrimination):
- Use sentence at index {level_6_sentence_index} as the correct usage.
- Generate 3 new sentences using the target word that are grammatical but semantically or pragmatically inappropriate.

Output schema:
Top-level keys are level numbers as strings.
Each level value is an array of 4 option objects: [{"1": text, "2": bool, "3": explanation}, ...]
Exception: Level "6" value is {"1": correct_sentence_index, "2": array of 3 wrong sentence objects [{"1": text, "2": explanation}, ...]}
```

---

## Prompt 3 — Grammar & Structure Exercises (`vocab_prompt3_transforms`)

**Purpose:** generate exercise content for ladder levels 4 (morphology slot),
7 (spot incorrect sentence), and 8 (collocation repair). Single LLM call
covers all included levels; the generator omits any level not in
`active_levels_json`, and additionally drops L8 if `primary_collocate` does
not appear as a whole-word in the chosen sentence.

### v1 (active)

Source: [migrations/vocabulary_ladder_schema.sql:252-293](../../migrations/vocabulary_ladder_schema.sql#L252-L293)

```
Role: Expert computational linguist generating English grammar and usage exercises.

Target word: {word}
Part of speech: {pos}
Semantic class: {semantic_class}
Tier: {complexity_tier}
Primary collocate: {primary_collocate}

Base sentences:
{sentences_json}

Morphological forms available:
{morphological_forms_json}

Generate ONLY the exercise levels listed here: {active_levels_json}

Rules:
1. All output values must be in English only.
2. Output valid JSON only using numeric keys.
3. For option objects: "1" = text, "2" = true/false, "3" = explanation.

Level "4" (Morphology Slot):
- Use sentence at index {level_4_sentence_index}.
- Correct option = the exact target substring (an inflected form).
- "4" = base_form, "5" = form_label (e.g. "past_tense").
- 3 distractors: real morphological siblings that are wrong for this sentence context.

Level "7" (Spot Incorrect Sentence):
- Use sentences at indices {level_7_correct_indices} as 3 correct sentences.
- Generate 1 new sentence containing a common learner-like structural error with the target word spelled correctly.
- "1" = incorrect_sentence, "2" = corrected_sentence, "3" = error_description.

Level "8" (Collocation Repair) — only if included:
- Use sentence at index {level_8_sentence_index}.
- Replace the correct collocate with an unnatural-but-plausible substitute.
- Correct option = the real collocate. 3 distractors = unnatural substitutions.

Output schema:
Top-level keys are level numbers as strings.
Level "4": array of 4 option objects + "4": base_form + "5": form_label + "6": sentence_index
Level "7": {"1": incorrect_sentence, "2": corrected_sentence, "3": error_description, "4": array of correct_sentence_indices}
Level "8": array of 4 option objects + "4": sentence_index + "5": error_collocate
```

---

## Template Variables

All variables below are populated by the generator classes on every render —
the renderer raises `KeyError` if any are missing.

| Variable | Filled by | Notes |
|----------|-----------|-------|
| `{word}` | `dim_vocabulary.lemma` | the target lemma |
| `{existing_definition}` | `dim_word_senses.definition` | `'None provided'` if blank |
| `{sense_id}` | `dim_word_senses.id` (the sense being generated for) | passed as a string; empty if absent |
| `{sense_definition}` | mirrors `existing_definition` until upstream sense selection lands | empty string if no definition |
| `{complexity_tier}` | sentence's tier or `'T3'` default | T1–T6, see [[decisions/ADR-003-age-tiers]] |
| `{corpus_sentences_json}` | NLP-extracted real sentences | `[]` if none |
| `{sentences_needed}` | `VOCAB_SENTENCES_PER_WORD - len(corpus)` | makes total = 10 |
| `{pos}` | from P1 output | passed to P2/P3 |
| `{semantic_class}` | from P1 output | passed to P2/P3 |
| `{definition}` | from P1 output | passed to P2 |
| `{primary_collocate}` | from P1 output | `'null'` literal if absent |
| `{register}` | from P1 output key `"10"` | falls back to `'neutral'` |
| `{sense_fingerprint}` | from P1 output key `"11"` | empty string fallback |
| `{sentences_json}` | array of `{index, text, target}` | from P1 output |
| `{morphological_forms_json}` | from P1 output | passed to P3 |
| `{active_levels_json}` | derived from `active_levels` & POS routing | levels skipped per semantic class |
| `{used_distractors_json}` | item-set distractor pool | passed via `generate(..., used_distractors=[...])`; default `[]` |
| `{level_3_sentence_index}` | `SENTENCE_ASSIGNMENTS_A[3]` (default 0) | which sentence to cloze |
| `{level_5_sentence_index}` | `SENTENCE_ASSIGNMENTS_A[5]` (default 2) | which sentence for collocation gap |
| `{level_6_sentence_index}` | `SENTENCE_ASSIGNMENTS_A[6]` (default 3) | which sentence is the correct usage |
| `{level_4_sentence_index}` | `SENTENCE_ASSIGNMENTS_A[4]` (default 1) | which sentence holds the inflected form |
| `{level_7_correct_indices}` | `L7_CORRECT_INDICES_A` (default `[0,1,2]`) | the 3 correct sentences |
| `{level_8_sentence_index}` | `SENTENCE_ASSIGNMENTS_A[8]` (default 4) | which sentence for collocation repair |
| `{level_8_sentence_text}` | sentence at that index | always passed (template references it) |
| `{level_8_collocate_word}` | `primary_collocate` or `'null'` | always passed (template references it) |

Defaults live in [services/vocabulary_ladder/config.py](../../services/vocabulary_ladder/config.py).

## Related Pages

- [[features/exercises]] — Prose description of exercise types
- [[features/exercises.tech]] — Generator architecture and JSON schema
- [[algorithms/vocabulary-ladder]] — 10-level ladder rationale
- [[algorithms/vocabulary-ladder.tech]] — POS routing, level activation
- [[decisions/ADR-003-age-tiers]] — `complexity_tier` value semantics

## Open Questions

- Chinese (`language_id=1`) and Japanese (`language_id=3`) variants of these
  three templates have not been seeded. The pipeline currently raises
  `RuntimeError` if invoked for those languages.
- Upstream sense selection is not yet wired — `{sense_id}` is currently passed
  as the integer ID but `{sense_definition}` defaults to the existing
  definition. Once a true sense-disambiguation step lands, plumb the chosen
  sense's definition independently.
- The `used_distractors` deduping pool is currently passed as `[]` from the
  pipeline orchestrator. Wiring this to the cross-variant distractor cache
  (so variant B sees variant A's distractors) is a follow-up.
