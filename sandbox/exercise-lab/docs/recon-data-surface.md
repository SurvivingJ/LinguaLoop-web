# Recon: Data Surface for Deterministic Exercise Generation

Read-only recon, 2026-09-17. Repo: `c:\Users\James\Documents\Coding\LinguaLoop\WebApp`.
Goal: inventory what exists on disk / in schema to build exercises **without an LLM**,
and what a sandbox SQLite build could seed from without touching Supabase.

All line numbers are as of this recon; cite the file for anything load-bearing.

---

## 1. Schema — tables/columns that matter to exercise construction

Primary source: `wiki/database/schema.tech.md` (dated but mostly accurate — two real
gaps found and flagged below). Cross-checked against `migrations/*.sql`.

### `dim_languages` (schema.tech.md:60-84)
`id smallint PK, language_code varchar UNIQUE, language_name, native_name, iso_639_1,
iso_639_3, is_active, display_order, tts_voice_ids jsonb, tts_speed numeric, grammar_check_enabled`.
Known IDs from context: `1=zh, 2=en, 3=ja` (inferred from `l1_lookup.py:48` registering ja
as `3`, and `_render_hant_mirror` gating `language_id != 1` for zh).

### `dim_vocabulary` (schema.tech.md:234-259)
Master lemma registry, one row per (language_id, lemma).
`id, language_id FK, lemma text, phrase_type text default 'single_word', component_lemmas text[],
part_of_speech text, frequency_rank real, level_tag text, semantic_class text`.
**`frequency_rank` is a Zipf score (0.25–6.56), not a rank** — a historical misnomer;
inverting this ordering is a real, previously-hit bug (`migrations/calibration_semantic_distractors.sql:39-52`).
1,003/11,795 rows (8.5%, that snapshot) have NULL `frequency_rank`.

### `dim_word_senses` (schema.tech.md:262-309)
Definitions, **two rows per sense** (`definition_level` = `simple`|`standard`, sharing one
`sense_rank`). Columns that matter: `id, vocab_id FK, definition_language_id FK, definition text,
definition_level, pronunciation text` (filled deterministically via pypinyin/fugashi, not LLM),
`ipa_pronunciation, example_sentence, sense_rank int, usage_frequency, semantic_category,
morphological_forms jsonb, is_validated bool, gen_confidence real, source ('llm'|'manual')`.
**`embedding vector(1536)` exists live but is UNDOCUMENTED in schema.tech.md** — added by
`migrations/dim_word_senses_embedding.sql` (applied live 2026-08-08, backfilled by
`scripts/backfill_sense_embeddings.py`, OpenAI `text-embedding-3-small`). HNSW index
`idx_dim_word_senses_embedding` (cosine). **Read paths must filter `definition_level='standard'`**
or duplicate.

### `word_assets` (schema.tech.md:1124-1147)
Pre-generated LLM exercise material per sense, one row per `(sense_id, asset_type)` where
`asset_type ∈ {prompt1_core, prompt2_exercises, prompt3_transforms}` (variant suffixes `_A`/`_B`
also occur in practice — see `exercise_renderer.py:114-139`). `content jsonb` holds the raw model
output (sentences[], pronunciation, definition, semantic_class, morphological_forms,
collocate_grounding — inferred from `exercise_renderer.py` usage, not separately schematized).
This is the **only** table an LLM touches for ladder content; everything downstream of it is
pure transformation.

### `exercises` (schema.tech.md:1032-1071)
The final, servable row. `id, language_id, exercise_type text, source_type enum
(grammar/vocabulary/collocation/conversation/style), grammar_pattern_id, word_sense_id FK,
word_asset_id FK, content jsonb, tags jsonb, difficulty_static, irt_difficulty/irt_discrimination/
irt_n_attempts/irt_calibrated_at/irt_se_difficulty (Phase 11 IRT fit), complexity_tier (T1-T6),
ladder_level int (1-9), attempt_count, correct_count, is_active`.
Constraint: at least one of grammar_pattern_id/word_sense_id/corpus_collocation_id/
conversation_id/style_pack_item_id must be non-null.

### `tests` / `questions` (schema.tech.md:540-607)
`tests`: transcript, audio_url, difficulty (1-9), style, tier, `vocab_sense_ids integer[]` (GIN),
`vocab_sense_stats jsonb`, **`vocab_token_map jsonb`** (token→sense mapping — a column on `tests`,
not a separate table), `pinyin_payload jsonb`, `pitch_payload jsonb`.
`questions`: `test_id FK, question_id text, question_text, choices jsonb, answer jsonb,
question_type_id FK, sense_ids integer[]`. MC grading key is literal text matching one of
`choices` (confirmed from a real export row, §7) — no LLM at grade time.

### `vocab_token_map` — NOT a table
It's `tests.vocab_token_map` (jsonb column), confirmed in schema.tech.md:560. Task brief's
premise that it's a standalone table is wrong.

### `semantic_distractors` — NOT a table, it's an RPC
`public.semantic_distractors()` (`migrations/calibration_semantic_distractors.sql`) — HNSW
nearest-neighbour search over `dim_word_senses.embedding`, filtered to reader's
`definition_language_id`, anchor's own `vocab_id` siblings excluded, ranked by frequency-tier
then cosine. A second function, `nearest_senses()` (`migrations/dim_word_senses_embedding.sql`),
does k-NN generation (find candidates); `sense_similarity_to_lemmas()` scores NAMED candidates
(band-check). All three are pgvector/cosine, index-backed, deterministic given the embedding.

### Pronunciation / phonetic infrastructure
No single "pronunciation table" — pronunciation lives on `dim_word_senses.pronunciation` /
`ipa_pronunciation`, filled at generation time by **pypinyin** (zh) / **fugashi+UniDic** (ja),
never by the LLM (schema.tech.md:275). For Japanese pitch accent specifically, there is a
**separate, fully deterministic pipeline**: `services/pitch_accent_service.py` runs
**pyopenjtalk** (`run_frontend`) over test transcripts, segments into morae, and derives
pattern class (heiban/atamadaka/nakadaka/odaka) + HL contour — written to `tests.pitch_payload`
at test-generation time (`services/test_generation/orchestrator.py:848-862`), not per-sense. This
is a genuine off-the-shelf accent dictionary (OpenJTalk's bundled NHK-derived data) already wired
in — a second deterministic asset source beyond CC-CEDICT.

### Measure-word (classifier/counter) dictionaries — UNDOCUMENTED in schema.tech.md
`dim_classifiers` / `dim_classifier_noun_pairs` / `dim_classifier_distractor_groups` (zh 量词,
`migrations/add_classifier_drill_mode.sql:31-72`) and the Japanese counter mirror `dim_counters` /
`dim_counter_noun_pairs` / `dim_counter_distractor_groups` (`migrations/counter_drill.sql`).
Shape (classifier side): `dim_classifiers(id, language_id, hanzi, pinyin, pinyin_display,
semantic_label, example_nouns text[], frequency_rank, distractor_group_id FK)`;
`dim_classifier_noun_pairs(id, language_id, noun_sense_id FK→dim_word_senses, lemma_text,
classifier_id FK, is_primary bool, frequency_score, source)`. Generic measure words (个/個, つ/こ)
are excluded by form at read time (`services/vocabulary_ladder/deterministic/dictionaries.py:58-61`),
mirroring the exclusion in `get_classifier_drill_session`.

### `dim_grammar_patterns` (schema.tech.md:313-337)
`pattern_code, pattern_name, description, user_facing_description, example_sentence,
language_id, complexity_tier (T1-T6), category (tense/aspect/voice/particles/word_order/
modality/clause_structure/conjugation/honorifics/measure_words/complement)`. Feeds
`exercises.grammar_pattern_id`.

### User ability / ELO / BKT
- `user_skill_ratings` (schema.tech.md:417-439): per (user, language, test_type) ELO, 400-3000,
  init 1200.
- `test_skill_ratings` (610-629): per (test, test_type) ELO, init 1400.
- `user_vocabulary_knowledge` (1151-1177): **BKT** state per (user, sense) —
  `p_known numeric default 0.10, status enum (unknown/encountered/learning/probably_known/
  known/user_marked_unknown), evidence_count, comprehension_correct/wrong, word_test_correct/wrong`.
- `user_word_ladder` (1210-1243): per (user, sense) ladder progression — canonical state is
  Phase 8 "Momentum Bands": `family_confidence jsonb` (6 cognitive families, BKT-style, clamped
  0.02-0.98), `gates_passed jsonb (gate_a/gate_b)`, `current_ring 1-4`, `stress_test_score`,
  `word_state enum (new/active/gated/pre_mastery/relearning/mastered)`. Phase-4 counter columns
  are written but never read (dead observability data, per an inline comment).
- `user_flashcards` (1180-1206): FSRS params (`stability, difficulty, due_date, reps, lapses,
  state`).

### Submission / attempt tables
- `test_attempts` (632-668): ELO snapshots before/after, `dictation_word_correct/total` +
  `dictation_diff jsonb` (dictation-only, Levenshtein-tolerant), `replay_count`,
  `elo_reduction_factor`.
- `question_attempt_results` (672-694): per-question grain (`is_correct, selected_answer,
  correct_answer`) — the data that feeds distractor pick-rate calibration and mis-key detection.
- `exercise_attempts` (1074-1095): per-ladder-exercise grain (`user_response jsonb, is_correct,
  time_taken_ms`). **`is_correct` arrives from the client already computed** for every type
  except `cloze_typed` (see §5) — `routes/vocab_dojo.py:52-64` takes `is_correct` as a request
  field, it does not compute it server-side.
- `word_quiz_results` (1246-1265): per-sense-within-test-attempt MC result.

---

## 2. Deterministic assets on hand (no LLM)

| Asset | Location | Coverage / notes | Powers |
|---|---|---|---|
| **CC-CEDICT** (zh dictionary) | `raw/cedict_ts.u8` — 124,962 lines, raw import | Imported via `scripts/import_cedict_classifiers.py` (classifier extraction specifically) | zh classifier seeding, potential broader zh lemma/definition source (memory notes: "CC-CEDICT exhausted for coverage" as a standalone dictionary-completeness source, i.e. it's already mined out for what it uniquely offers) |
| **Japanese mora phonetic trie** | `services/vocabulary_ladder/phonetic_trie/{trie.py, ja_mora.py}` + built artifact `data/content_builds/phonetic_trie/ja_mora_trie.pkl` (21.2 MB) | ja only, live since 2026-08 (see `l1_lookup.py`). Registry (`l1_lookup.py:47-49`) has exactly one entry, `language_id=3`. zh (initial,final,tone) and en ARPAbet tries are **designed for but not built** — `phonetic_trie/__init__.py:5-7` and `trie.py:3-7` describe the language-agnostic unit-sequence trie explicitly to support them, but no zh/en module exists yet | ja L1 phonetic-recognition distractors: one-mora-substitution real-word neighbors, tier-floored by `wordfreq.zipf_frequency`, with deterministic dakuten/long-vowel/geminate/moraic-n contrast explanations (`l1_lookup.py:92-147`) |
| **pyopenjtalk pitch-accent extraction** | `services/pitch_accent_service.py` | Runs per test transcript at generation time (not per-sense); ja only | `tests.pitch_payload` — mora segmentation, accent nucleus, HL contour, pattern class |
| **fugashi + UniDic** (ja lemmatizer) | `services/vocabulary/processors/japanese.py` (222 lines) | Segmentation/lemmatization + kana reading (`reading_for`), with careful orthBase-vs-lemma disambiguation rules for kanji variants, loanwords, kana homophones, classical conjugations | ja lemma identity, reading generation for `dim_word_senses.pronunciation` |
| **pypinyin** | referenced in schema.tech.md:275 as the zh pronunciation source (not separately inspected as a file — it's a pip dependency, not a data asset) | zh only | `dim_word_senses.pronunciation` for zh |
| **pgvector embeddings + HNSW** | `dim_word_senses.embedding vector(1536)`, `migrations/dim_word_senses_embedding.sql` | OpenAI `text-embedding-3-small`; embeds `"{lemma}: {definition}"` (not definition alone) specifically so a word's own senses cluster together and get excluded, not confused with true near-neighbors. `zh` 34% pronunciation coverage doesn't gate this — embedding coverage is presumably near-complete per language but wasn't directly re-measured this session (UNVERIFIED exact %) | `nearest_senses()` (distractor generation), `semantic_distractors()` (calibration's harder, frequency-matched picker), `sense_similarity_to_lemmas()` (band-check scoring) |
| **wordfreq (Zipf frequency)** | Python package, used directly (`l1_lookup.py:31`, `zipf_frequency`) and mirrored into `dim_vocabulary.frequency_rank` | zh/en/ja all have "has_zipf" ~92-94% per 2026-09-08 inventory (§3) | Frequency-band matching for distractors (soft key, cosine is the hard key in `semantic_distractors`); tier floors for L1 candidates |
| **Classifier/counter dictionaries** | `dim_classifiers`/`dim_counters` + pairs/groups tables (see §1); curated JSON in `data/classifier_curation/*.json` (44 files) and `data/counter_curation/*.json` (44 files), one per measure word, plus `approved_curation.json` (25.7 KB) | zh 量词 + ja 助数詞, curated via LLM once then stored — now a pure lookup, no further LLM calls needed at generation time | `classifier_match` / `counter_match` deterministic exercise types |
| **POS tags** | `dim_vocabulary.part_of_speech` (LLM-derived once, cached), UniDic POS tags at tokenize time | All languages | Gating which ladder levels/types are even offered (`semantic_class`/POS-driven capability matrix in `services/vocabulary_ladder/config.py`) |
| **`services/vocabulary_ladder/deterministic/*` registry** | 10 files, no DB writes, no LLM calls ever (module docstring, `deterministic/__init__.py:1-32`) | See exact registered type list below | The actual "cheap generation" pipeline the user is asking to expand |

**Deterministic exercise types already registered** (grep `@register(` across
`services/vocabulary_ladder/deterministic/*.py`): `classifier_match`, `counter_match`,
`definition_match`, `cloze_typed`, `jumbled_sentence`, `hanzi_to_pinyin`, `pinyin_to_hanzi`,
`kanji_to_reading`, `reading_to_kanji`, `tone_id_word`. These read only `dim_word_senses` +
`dim_vocabulary` (+ classifier/counter tables where relevant) — **no `word_assets` row required**,
confirmed both by the module docstring and by the 2026-09-08 inventory note that ja's 1,067
ladder exercises coming from only 76 `word_assets`-backed senses means "pre-generated exercise
rows are useless as a broad item pool... build such items on the fly from the deterministic
builders instead" (memory: `webapp-content-inventory-2026-08.md`, quoted verbatim).

`readings.py` (script↔sound, 4 types) is worth flagging specifically: script→sound distractors
come from a phonological confusion-set module (`phonology.py`, 16.8 KB — tone variants for zh,
voicing for ja); sound→script distractors are corpus-derived (true homophones → shared-component
characters → frequency-band filler, in that priority order) — i.e. it needs zero net-new data,
only smarter queries against what's already in `dim_vocabulary`/`dim_word_senses`.

---

## 3. Coverage numbers (verified against project memory, dated 2026-09-08 — 8 days old, itself flagged as "verify before asserting")

Source: `webapp-content-inventory-2026-08.md` (session memory file), "UPDATE 2026-09-08" section,
which explicitly supersedes an earlier 2026-08-21 snapshot in the same file (that older snapshot
said "ja has 0 exercises/word_assets" — **now stale, corrected below**).

| lang | senses | rank1 (freq-ranked) | has_pron | has_zipf | active ladder exercises | word_assets-backed senses |
|---|---|---|---|---|---|---|
| zh | 23,870 | 23,543 | 8,084 (34%) | 94% | 334 | 30 |
| en | 10,774 | 8,441 | 22 (0%) | 92% | 252 | 21 |
| **ja** | 21,378 | 21,204 | **4,770 (22%)** | 92% | **1,067** | **76** |

Corrections to the task brief's assumptions:
- "~22k senses total" — **wrong**, actual is ~56,022 across the three languages combined
  (23,870 + 10,774 + 21,378). Possibly the brief meant "22% coverage" and conflated it with a
  count; flagging rather than guessing at intent.
- "ja has 1,067 ladder exercises from only 76 senses" — **confirmed correct**, verbatim.
- "ja pronunciation coverage 4,770 senses (22%)" — **confirmed correct**, verbatim.
- "en words have ZERO zh/ja glosses" — **confirmed, more precisely**: 0/4,222 cross-language
  gloss rows for English source words. Gloss coverage is otherwise "essentially complete" for
  zh/ja study languages (ja 3,534/3,534 across zh/en/ja target languages; zh 3,914/3,955).

Additional, not previously in the task brief:
- `vocab_gloss_translation` (the cross-language gloss generator) economics: 9,962 calls in 29 min
  wall clock, mean **$0.000026/call** — closing the full en→zh/ja gap is estimated at ~5,600 calls,
  ~$0.15, ~16 minutes. Cheap; not the bottleneck.
- Tests: en 106 active / zh 125 / ja 82→48 (a corrupted ja beginner batch was hard-deleted
  2026-08-22). Tests cluster at difficulty `{1,3,6,9}` — mid-band difficulties (2,4,5,7,8) are
  nearly empty across all three languages, independent of the vocabulary/exercise question.
- `vocab_sense_ids` link coverage **on tests** (a different metric from sense-table coverage
  above): ja 59/59 (100%), en 100/121 (~83%), zh 98/125 (~78%) — source:
  `wiki/decisions/ADR-024-vocabulary-aware-test-selection.md:44`. So 17-22% of en/zh *tests*
  carry no vocabulary link at all, independent of per-sense pronunciation/exercise coverage.

UNVERIFIED this session: exact embedding-column fill rate per language (referenced as a design
constraint in `calibration_semantic_distractors.sql` but not independently re-queried); exact
row counts for `dim_classifiers`/`dim_counters`/pairs tables (curation JSON file counts given
instead, §2).

---

## 4. Exercise rendering — stored seed vs. computed-at-render

Source: `services/vocabulary_ladder/exercise_renderer.py` (1,122 lines), the offline (admin
upload time, not request path) pipeline turning `word_assets` into `exercises` rows. Two
generation paths converge on the same `exercises` table:

**Path A — LLM-seeded (9 ladder levels, L1-L9).** `render_all(sense_id, language_id)` →
`build_rows()`:
1. Loads all `word_assets` rows for the sense (`prompt1_core`, `prompt2_exercises[_A/_B]`,
   `prompt3_transforms[_A/_B]`, `llm_types_A/B`) — one Supabase read, no LLM call here.
2. `prompt1_core` (the seed) supplies: `semantic_class`, `sentences[]` (each with a target word,
   complexity_tier, sentence_source), `pronunciation`, `definition`, `collocate_grounding`. This
   is the **small stored seed** the task is asking about — everything else is derived from it.
3. Per level (1-9), a dedicated `_render_*` method pulls the relevant P2/P3 fragment and:
   - **Computed at render time, every time**: option shuffling (`random.shuffle`), blanked-sentence
     construction (`text.replace(target, '___', 1)`), Simplified→Traditional mirror for zh
     (`_render_hant_mirror`, lazy-loaded converter), audio TTS generation + R2 upload for L1
     (`_generate_l1_audio`), and — critically — **judge calls** (`l1_distractor`, `cloze_judge`,
     `collocation`, `sentence_validity`) that filter/verify the LLM's own candidate distractors
     against the same corpus data (embeddings, dictionaries) before they're allowed to ship.
   - L1 has a second path: if a phonetic trie exists for the language (ja only), distractors
     are looked up deterministically instead of read from the LLM's `level_1` asset at all
     (`_render_phonetic`, `l1_lookup.build_candidates`) — the LLM seed is bypassed entirely for
     that level, and the *same* post-hoc judge still runs on the trie's output.
   - L9 (jumbled) stores almost nothing (`{'original_sentence': text}`) — chunking happens at
     **serve time**, not render time, i.e. an even later deferred-computation point beyond what
     this recon traced (frontend or a separate serve-path service, not inspected this session).
4. A/B variants double the sentence assignments so the same word produces two distinguishable
   items from one `word_assets` row.
5. Two/uuid4 exercise rows are inserted per level per variant, each tagged with `ladder_level,
   semantic_class, variant, provenance, collocate_grounding` (where applicable) and any
   `<judge_key>_judge` metadata sidecar.

**Path B — Deterministic (10 types, §2).** `_render_deterministic()` / `_render_llm_types()`
build `SenseContext` from the **same** `prompt1_core` (`lemma, pronunciation, definition,
semantic_class`) plus direct DB lookups (classifier/counter dictionaries, phonology confusion
sets) — no `word_assets` variant-specific fragment required beyond what P1 already has. This is
the path that needs the least new infrastructure to scale, since it already runs off
`dim_word_senses`/`dim_vocabulary` alone in the cases that don't touch classifier/counter tables.

**Design implication for a cheaper pipeline** (this recon's synthesis, not a repo claim): the
"stored seed, render many variants" model already exists in production for both LLM-seeded and
fully-deterministic types. A LLM-free generation pipeline could plausibly skip `word_assets`
entirely for any sense that already has `dim_word_senses.pronunciation` + `definition` +
`dim_vocabulary.frequency_rank`/POS filled — which per §3 is a materially large slice of the
lexicon (94%/92%/92% Zipf coverage; pronunciation lags at 34%/0%/22%). The renderer's `core`
object needed by the deterministic path is a strict subset of what P1 provides, so back-filling
that subset without an LLM (pypinyin/fugashi already do this for pronunciation; nothing currently
back-fills `sentences[]`/example usage deterministically — that gap is presumably why the
deterministic types that need a P1 sentence, e.g. `cloze_typed`, still depend on a `word_assets`
row rather than running off `dim_word_senses` alone).

---

## 5. Grading — per exercise type

| Type / surface | Graded by | LLM at grade time? | Evidence |
|---|---|---|---|
| Ladder MC types (phonetic_recognition, definition_match, cloze_completion, morphology_slot, collocation_gap_fill, semantic_discrimination, spot_incorrect_sentence, collocation_repair, hanzi_to_pinyin, pinyin_to_hanzi, kanji_to_reading, reading_to_kanji, tone_id_word, classifier_match, counter_match, jumbled_sentence) | **Client (browser JS)**. Server (`routes/vocab_dojo.py:52-64`) takes `is_correct` as a caller-supplied field and just records it — the correct option is already present in `content`, so hiding it server-side buys nothing | **Never** | `routes/vocab_dojo.py` |
| `cloze_typed` (free-text productive cloze) | **Server**, exact match after normalization (NFKC, simplified/traditional folding, case, punctuation — `utils/answer_normalization.py`), against a stored `accepted[]` set (key + morphological variants, only when the blank slot is uninflected) | **No** — deliberately deterministic; module docstring explicitly justifies server-side grading as "a normalisation rule... implemented twice in two languages is a rule that will eventually disagree with itself" | `services/vocabulary_ladder/deterministic/cloze_typed.py:81-113` |
| Comprehension test MC questions (`questions.answer`) | **Server**, literal string match of `selected_answer` against the keyed `correct_answer` (confirmed against a real exported row: `correct_answer` is exactly one of the `choices` strings) | **No** | `generated_tests_20251209_225642_questions.csv` (real data), `question_attempt_results` schema |
| Dictation (free-text/audio transcription test type) | **Server**, Levenshtein fuzzy tolerance (`services/dictation/tokenizer.py` — NFKD diacritic strip, punctuation strip, jieba for zh, char-level for ja, whitespace for others; a companion `_fuzzy_equal` in the grader treats ≥4-char words within edit distance 1 as equal) | **No** | `services/dictation/tokenizer.py`, `test_attempts.dictation_word_correct/dictation_diff` columns |
| Pinyin / Pitch-accent test types | **Server**, structured (tap/click sequence against precomputed `pinyin_payload`/`pitch_payload`) — not free text; not independently re-verified this session beyond confirming the payload is precomputed deterministically at test-gen time | Presumed no (UNVERIFIED — did not read `process_pitch_accent_submission` RPC body this session) | `migrations/add_pitch_accent_mode.sql`, `services/pitch_accent_service.py` |
| **Dual Translation (DT)** — free-text L1→L2 translation | **Cascade**: Tier 0 (`services/dual_translation/tier0.py`) does deterministic near-exact-match scoring first (reuses the dictation normalizer) and short-circuits to full marks if the reproduction is normalization-equivalent to the reference. Only if Tier 0 doesn't resolve does it escalate to Tier 1 (accuracy+range, single LLM call) and conditionally Tier 2 (understandability+fidelity+naturalness, always called if Tier 0 unresolved; re-checks Tier 1's dimensions on low confidence or large diff) | **Yes, conditionally** — the only user-facing grading path in the app that calls an LLM per submission, and only for the fraction of submissions Tier 0 can't resolve | `services/dual_translation/grader_cascade.py:1-40`, `services/dual_translation/tier0.py` |

Generation-time-only judges (entailment judge, distractor plausibility judges, L1/cloze/
collocation/sentence-validity judges used inside `exercise_renderer.py`) are **not** grading —
they vet candidate content once, at build time, and the cost is amortized across every future
learner attempt. They should not be confused with the (much smaller) set of grading paths above
that call an LLM per learner submission.

---

## 6. Free-text surface — complete enumeration

Only two exercise/test surfaces in the app currently accept genuinely free (non-MC) text input:

1. **`cloze_typed`** (ladder exercise type) — graded server-side, exact-match-after-normalization,
   no LLM. See §5.
2. **Dictation** (test type, `dim_test_types.type_code='dictation'`) — full transcription of
   audio, graded server-side via Levenshtein-tolerant token comparison, no LLM. See §5.
3. **Dual Translation (DT)** — full-sentence/passage free translation, graded via the Tier0→1→2
   cascade above; the only one of the three where an LLM is in the grading path (conditionally).

Everything else (all 16 other ladder types, all comprehension `questions`, pinyin/pitch-accent
test types) is selection-based (MC index / tap sequence) and graded by string/index equality,
client- or server-side, never an LLM.

---

## 7. Existing local sample data (no Supabase required to seed from)

| Path | Contents | Size / rows |
|---|---|---|
| `raw/cedict_ts.u8` | Full CC-CEDICT zh dictionary dump | 124,962 lines |
| `data/content_builds/phonetic_trie/ja_mora_trie.pkl` | Built ja mora phonetic trie (pickle) | 21.2 MB |
| `tests/fixtures/dt_gold/{en,ja,zh}.json` | **Human-adjudicated** DT gold set: real `dt_passage.l2_text` (pulled live 2026-07-05), 30 items/language (10 clean/15 single-error/25 multi-error split varies slightly), full reference+reproduction text, seeded error spans, expected rubric bands. See `tests/fixtures/dt_gold/README.md` for full schema and provenance | en.json 934 lines, ja.json 934, zh.json 918 (~30 items each) |
| `dim_languages_rows.csv` (repo root) | Literal export of the live `dim_languages` table | 3 data rows |
| `dim_test_types_rows.csv` (repo root) | Literal export of the live `dim_test_types` table | 7 data rows |
| `generated_tests_20251209_225642_tests.csv` (repo root) | Real generated test rows (transcript, difficulty, style, tier, language, generation_model, etc.) from a 2025-12-09 batch run | 704 lines (≈703 tests) |
| `generated_tests_20251209_225642_questions.csv` (repo root) | Real MC questions paired to the above tests (`question_text, choices, correct_answer, answer_explanation`) | 766 lines (≈765 questions) |
| `generated_tests_20251209_225642.json` (repo root) | Presumably the same batch, full JSON (not opened this session — 509 KB) | UNVERIFIED contents beyond filename |
| `spot_check_semantic_class.csv` (repo root) | Human-vs-machine semantic_class agreement spot-check (`vocab_id, lang, lemma, pos, definition, machine_class, confidence, human_class, agree`) | 199 lines |
| `data/classifier_curation/*.json` (44 files) + `approved_curation.json` | Curated zh classifier-noun groupings, per-classifier-character, already LLM-vetted | 44 files, approved file 25.7 KB |
| `data/counter_curation/*.json` (44 files) | Curated ja counter-noun groupings, mirror of the above | 44 files |
| `data/eval/*` | Various judge eval fixtures (distractor gold frame, entailment AB tests, cloze/distractor judge samples) — generation-time judge eval data, not exercise seed data per se | ~40 files |
| `data/sense_linking/tests_missing_senses.csv` | Tests whose transcript vocab hasn't been linked to `dim_word_senses` yet | UNVERIFIED row count |
| `data/exercise_seeding/`, `data/sense_seeding/`, `data/gloss_seeding/` | Batch-run inputs/outputs from the content-generation skills (ja exercise batches, ja/zh sense batches, gloss batches) | 8 / 2 / 396 files respectively — mostly small per-run JSON, not bulk corpora |

**No `.sqlite`/`.db` file exists anywhere in the repo** (checked via glob across the whole tree).
A sandbox SQLite build has no existing SQLite artifact to copy — it would need to be constructed
fresh from the CSV/JSON sources above, which is entirely feasible: the three `dim_*_rows.csv`
files plus the `generated_tests_*` pair give a complete, self-consistent `dim_languages` +
`dim_test_types` + `tests` + `questions` slice with zero Supabase access, and `dt_gold/*.json`
gives a ready-made DT eval set with human-verified labels.

---

## Open items / things to verify before relying on this doc

- Exact per-language embedding fill rate on `dim_word_senses.embedding` (not re-queried this
  session).
- `process_pitch_accent_submission` and pinyin-submission RPC bodies (grading mechanics assumed
  deterministic based on payload shape and naming, not read line-by-line).
- `data/sense_linking/tests_missing_senses.csv` row count.
- `generated_tests_20251209_225642.json` (509 KB) full structure — likely a superset/raw form of
  the two CSVs, not separately parsed.
- Exact row counts in `dim_classifiers`/`dim_classifier_noun_pairs`/`dim_counters`/
  `dim_counter_noun_pairs` (live DB, not queryable read-only from this repo-only recon).
