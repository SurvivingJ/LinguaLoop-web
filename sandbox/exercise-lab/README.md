# exercise-lab

An isolated sandbox for prototyping **a new exercise-generation pipeline**
and **a new exercise-serving algorithm** for LinguaLoop, without ever
touching Supabase, running a migration, or spending a cent of the project's
remaining OpenRouter budget. Nothing outside `sandbox/exercise-lab/` was
created or modified to build this.

Read `docs/recon-generation.md`, `docs/recon-serving.md`, and
`docs/recon-data-surface.md` first if you haven't - this sandbox is built
directly from what those three recon passes found in the live codebase.

---

## 1. Isolation guarantees (the hard rules this sandbox obeys)

1. **Filesystem scope.** Every file this sandbox creates or modifies lives
   under `sandbox/exercise-lab/`. It reads from elsewhere in the repo
   (`raw/`, `data/`, root-level CSVs, `tests/fixtures/`) but never writes
   there.
2. **No Supabase, ever.** No file here imports a Supabase client, holds a
   connection string, or runs a migration. The only database is
   `db/lab.sqlite`, a local file, built by `db/build_db.py` from local
   files.
3. **No real LLM/embedding API calls.** `lab/mock_llm.py`'s "live" mode is a
   stub that raises unless BOTH a constructor flag (`allow_live=True`) AND
   the environment variable `EXERCISE_LAB_ALLOW_LIVE_LLM=1` are set - and
   even then it raises `NotImplementedError`, because no real call is wired
   in. This is deliberate: the project's **total remaining OpenRouter
   budget for the whole effort is $6.31**, not per-run, so it must be close
   to impossible to trigger a real spend by accident from this sandbox.
   `lab/embeddings.py` never calls an embedding API either - see §4.
4. **Read-only elsewhere.** This sandbox imports repo modules read-only
   where useful (e.g. `pypinyin`, `wordfreq`, `spacy` are shared venv
   dependencies) but never imports and calls production service code that
   could reach a network or a real database (e.g. nothing here imports
   `services/vocabulary_ladder/asset_pipeline.py` or anything under
   `routes/`).
5. **Regenerable, not precious.** `db/lab.sqlite` is gitignored
   (`sandbox/exercise-lab/.gitignore`) and rebuilt from scratch by
   `db/build_db.py` every time it's run - there is no manual/incremental
   state to protect. Same for `reports/*.json` / `reports/*.md` (harness
   output).

---

## 2. How to run everything

All commands assume you're at the repo root
(`c:\Users\James\Documents\Coding\LinguaLoop\WebApp`) and use the repo's
existing venv, per project convention.

### Build the database

```bash
cd sandbox/exercise-lab
../../venv/Scripts/python db/build_db.py
```

Takes ~30 seconds. It deletes any existing `db/lab.sqlite` first and
rebuilds from scratch (sources are deterministic local files, so "stale vs
fresh" isn't a failure mode worth guarding against). It prints a running
log of what it loaded from where, and a final row-count summary for every
table. See §5 for the real numbers from the last run.

### Run the tests

Per project memory (`webapp-pytest-needs-pythonpath.md`): pytest silently
collects **zero** tests on a hidden import error rather than failing loudly
if you don't get the invocation right. This sandbox's own
`tests/conftest.py` inserts its own directories onto `sys.path`
specifically so it does **not** depend on you getting `PYTHONPATH` right -
but the explicit-path habit from that memory note is still good practice:

```bash
venv/Scripts/python -m pytest sandbox/exercise-lab/tests -v
```

23 tests, ~1 second, all passing as of this writing (full output in §6).

### Use the harness on your own generator

```python
import sys
sys.path.insert(0, "sandbox/exercise-lab")

from lab.harness import run_harness, write_report
from lab.models import SenseRow, ExerciseRow
from lab import db as labdb
from pathlib import Path

conn = labdb.connect()  # opens db/lab.sqlite with foreign_keys=ON
rows = conn.execute("""
    SELECT ws.id, ws.vocab_id, v.language_id, v.lemma, v.part_of_speech,
           v.frequency_rank, ws.definition, ws.definition_level,
           ws.pronunciation, ws.example_sentence, ws.sense_rank
    FROM dim_word_senses ws JOIN dim_vocabulary v ON v.id = ws.vocab_id
    WHERE v.language_id = 1 AND ws.definition_level = 'standard'
    ORDER BY v.frequency_rank DESC LIMIT 20
""").fetchall()
senses = [SenseRow(sense_id=r[0], vocab_id=r[1], language_id=r[2], lemma=r[3],
                    part_of_speech=r[4], frequency_rank=r[5], definition=r[6],
                    definition_level=r[7], pronunciation=r[8],
                    example_sentence=r[9], sense_rank=r[10]) for r in rows]

class MyGenerator:
    name = "my_prototype"
    def generate(self, sense: SenseRow) -> list[ExerciseRow]:
        ...  # your new pipeline

report = run_harness(MyGenerator(), senses, concurrency=4)
print(report.to_markdown())
write_report(report, Path("sandbox/exercise-lab/reports"), "my_prototype_run1")
```

### Use the mock LLM inside a generator

```python
from lab.mock_llm import MockLLMClient

client = MockLLMClient(mode="synthetic")   # or mode="replay" with a fixture cache
resp = client.complete("your real prompt text here")
# resp.text, resp.tokens_in/out, resp.cost_usd, resp.latency_ms, resp.mode
```

### Use the learner simulator for a serving prototype

```python
from lab.learner_sim import make_population, NearestEloSelector, simulate, learning_curve

learners = make_population(50, skills=["reading", "listening", "pitch_accent"], seed=42)
selector = NearestEloSelector()  # replace with your own Selector subclass
history = simulate(selector, learners[0], n_days=90)
curve = learning_curve(history, "reading")
```

### Sanity-check the whole thing ran (what "actually runs end to end" looks like)

```bash
cd sandbox/exercise-lab
../../venv/Scripts/python db/build_db.py          # build the DB (see §5 for real output)
cd ../..
venv/Scripts/python -m pytest sandbox/exercise-lab/tests -v   # 23 passed (see §6 for real output)
```

---

## 3. Directory layout

```
sandbox/exercise-lab/
  README.md                 - this file
  .gitignore                - db/lab.sqlite and reports/* are regenerable, not committed
  docs/
    recon-generation.md      - peer recon: how exercises are generated today
    recon-serving.md         - peer recon: how exercises/tests are selected/served today
    recon-data-surface.md    - peer recon: exact schema/columns/local data files available
  db/
    schema.sql               - the SQLite schema (16 tables, see §4 of this README)
    build_db.py               - builds db/lab.sqlite from local files only (§2, §5)
    lab.sqlite                - GITIGNORED, generated by build_db.py
  lab/
    __init__.py
    models.py                 - SenseRow / ExerciseRow dataclasses shared by harness+generators
    db.py                     - tiny sqlite3 connection helper (sets PRAGMA foreign_keys=ON)
    embeddings.py             - EmbeddingBackend protocol + local TF-IDF proxy (§4)
    mock_llm.py                - replay / synthetic / live(stub) LLM client (§4)
    harness.py                 - times/costs any Generator, single-item latency + throughput
    learner_sim.py             - synthetic learner population for serving prototypes
    fixtures/                  - mock_llm replay-mode fixture cache lives here (created on demand)
  tests/
    conftest.py                - makes imports work regardless of how pytest was invoked
    test_build_db.py
    test_harness.py
    test_mock_llm.py
    test_learner_sim.py
  reports/                    - harness output (JSON+markdown) lands here; gitignored contents
```

---

## 4. What's in the database, and where it came from

`db/schema.sql` defines exactly the 16 tables the task specified:
`dim_languages, dim_vocabulary, dim_word_senses, word_assets, exercises,
tests, questions, user_skill_ratings, user_vocabulary_knowledge,
exercise_attempts, test_attempts, question_attempt_results,
dim_classifiers, dim_classifier_noun_pairs, dim_counters,
dim_counter_noun_pairs` - column-faithful to production per
`docs/recon-data-surface.md` §1, with SQLite-forced deviations documented
at the top of the schema file itself (no pgvector/array/jsonb types, no
RLS, FK enforcement is opt-in per connection).

### Sources used, and what came from each

| Source (local file) | Feeds | Notes |
|---|---|---|
| `dim_languages_rows.csv` | `dim_languages` | literal export, 3 rows |
| `raw/cedict_ts.u8` (CC-CEDICT, 124,933 real entries) | zh `dim_vocabulary` + `dim_word_senses` | one lemma (simplified form) per unique CEDICT headword; multiple CEDICT lines sharing a lemma become multiple senses under one vocab row, exactly like production's polysemy model |
| `raw/jmdict_eng.json` (JMdict, found during this build, **not** in the recon's source list) | ja `dim_vocabulary` + `dim_word_senses` | filtered to `common: true` entries only (22,630 of 218,461 total) - a real structured dictionary, better than the "derive from corpus" fallback the task anticipated for a language with no local dictionary |
| `wordfreq` package (`top_n_list('en', 4000)`) + tokens mined from the local EN test transcripts | en `dim_vocabulary` | no local English dictionary exists anywhere in this repo (confirmed - see §"Fidelity gaps" below); this is a real published wordlist standing in for one |
| `en_core_web_sm` (spaCy, already installed offline) | en `dim_vocabulary.part_of_speech` | real POS tagging, run with parser/NER/lemmatizer disabled for speed |
| `generated_tests_20251209_225642_tests.csv` + `_questions.csv` | `tests`, `questions` | see the row-count correction below |
| `data/classifier_curation/*.json` (44 files, 43 used - `approved_curation.json` is a summary, not a classifier) | `dim_classifiers`, `dim_classifier_noun_pairs` | classifier pinyin computed via `pypinyin` (same library production uses, not an LLM) |
| `data/counter_curation/*.json` (44 files, 43 used) | `dim_counters`, `dim_counter_noun_pairs` | ja counter mirror of the above |
| `pypinyin`, `wordfreq.zipf_frequency` | `frequency_rank` columns (all languages) | Zipf score, **not inverted** - see the dedicated test `test_frequency_rank_is_a_zipf_score_not_a_rank` |

`tests/fixtures/dt_gold/{en,ja,zh}.json` (human-adjudicated DT gold set,
~30 items/language) was inspected but **not loaded** - it's a
translation-grading eval fixture, not exercise/vocabulary seed data, and
none of the 16 required tables has a natural home for it. It remains
available at its original path for a later agent working on
generation/grading quality specifically.

### Row-count correction worth flagging

The recon estimated "~703 tests / ~765 questions" from a naive line count
of the CSV files (704 physical lines). The actual number of **rows**,
correctly parsed with `csv.DictReader` (which handles the embedded
newlines inside quoted `transcript` fields), is **153 tests** (76 English +
76 Chinese + 1 Japanese) and **765 questions** - the questions count was
right, the tests count was inflated ~4.6x by counting physical lines
instead of records. This build reports the correct 153.

The CSV's `transcript` column is not plain text - it's a ` ```json`-fenced
blob like `{"transcript": "...", "difficulty_level": N}`. `build_db.py`
unwraps this (`_extract_transcript`) before storing; sentence-mining for
example sentences and en vocabulary corpus extraction both run against the
unwrapped plain text.

---

## 5. Actual row counts from the last build (2026-09-17)

```
dim_languages:               3
dim_vocabulary:         148,427   (zh 121,159 + ja 22,426 + en 4,842)
dim_word_senses:        304,810   (zh 249,866 + ja 45,260 + en 9,684 - simple+standard pairs)
tests:                      153   (en 76, zh 76, ja 1)
questions:                  765
dim_classifiers:             43
dim_classifier_noun_pairs:  570   (554 resolved to a seeded zh sense, 16 NULL)
dim_counters:                43
dim_counter_noun_pairs:     578   (423 resolved to a seeded ja sense, 155 NULL)
word_assets:                  0   (never populated - no LLM calls allowed here)
exercises:                     0   (never populated by build_db.py - harness-run prototypes populate this)
user_skill_ratings:            0
user_vocabulary_knowledge:     0
exercise_attempts:             0
test_attempts:                 0
question_attempt_results:      0
```

Embeddings + corpus-mined example sentences (capped at the top 8,000
highest-Zipf senses per language, see `EMBED_TOP_N_PER_LANGUAGE` in
`build_db.py`):

```
zh: 8,000 senses embedded, 2,546 got a real corpus-mined example_sentence (from 517 candidate sentences)
ja: 8,000 senses embedded,    29 got a real corpus-mined example_sentence (from only  7 candidate sentences - only 1 ja test exists)
en: 4,842 senses embedded, 2,604 got a real corpus-mined example_sentence (from 1,028 candidate sentences)
```

Build time: ~32 seconds. Database size: ~123 MB (mostly the 20,842 stored
512-float32 embedding BLOBs plus the full CC-CEDICT/JMdict text).

---

## 6. Test run output (2026-09-17)

```
$ venv/Scripts/python -m pytest sandbox/exercise-lab/tests -v

collected 23 items

test_build_db.py::test_all_required_tables_exist                              PASSED
test_build_db.py::test_row_counts_match_the_documented_seed                   PASSED
test_build_db.py::test_frequency_rank_is_a_zipf_score_not_a_rank              PASSED
test_build_db.py::test_dim_word_senses_has_two_rows_per_sense_rank            PASSED
test_build_db.py::test_en_senses_have_no_definition_documented_gap            PASSED
test_build_db.py::test_embedding_blob_round_trips_to_the_right_shape          PASSED
test_build_db.py::test_classifier_noun_pairs_link_back_to_seeded_zh_senses    PASSED
test_harness.py::test_harness_times_and_aggregates_serially                   PASSED
test_harness.py::test_concurrency_improves_wall_clock_and_throughput          PASSED
test_harness.py::test_harness_survives_a_generator_that_raises                PASSED
test_harness.py::test_report_serializes_to_json_and_markdown                  PASSED
test_learner_sim.py::test_population_has_correlated_but_distinct_per_skill_ability  PASSED
test_learner_sim.py::test_guess_floor_caps_worst_case_response_probability    PASSED
test_learner_sim.py::test_simulation_produces_a_learning_curve_that_climbs_toward_true_ability  PASSED
test_learner_sim.py::test_forgetting_decays_toward_a_floor_not_to_zero        PASSED
test_mock_llm.py::test_synthetic_mode_is_deterministic_given_the_same_prompt  PASSED
test_mock_llm.py::test_live_mode_raises_with_no_opt_in_at_all                 PASSED
test_mock_llm.py::test_live_mode_raises_with_constructor_flag_but_no_env_var  PASSED
test_mock_llm.py::test_live_mode_raises_with_env_var_but_no_constructor_flag  PASSED
test_mock_llm.py::test_live_mode_with_both_opt_ins_is_still_an_unimplemented_stub  PASSED
test_mock_llm.py::test_replay_mode_requires_a_recorded_fixture                PASSED
test_mock_llm.py::test_replay_mode_returns_the_recorded_fixture               PASSED
test_mock_llm.py::test_budget_ceiling_hard_stops_before_overspend             PASSED

============================= 23 passed in 1.01s ==============================
```

---

## 7. Fidelity gaps (collected - read this before trusting any prototype result)

Every one of these is also inline in the relevant module as a
`# FIDELITY GAP:` comment. Collected here so nobody has to go hunting:

1. **Distractor-selection embeddings are orthographic, not semantic**
   (`lab/embeddings.py`). A hashed character n-gram TF-IDF vector
   overstates similarity between words that merely share spelling (zh 打电话
   vs 打篮球 look close because they share 打) and understates similarity
   between true synonyms spelled differently (en "happy" vs "glad" look
   unrelated). Any distractor-quality number from this sandbox measures
   orthographic confusability, not semantic confusability. No local
   sentence-transformer model was found installed (`pip list` has no
   `sentence-transformers`/`torch`) - checked via
   `check_local_sentence_transformer_available()`, not assumed.
2. **No pgvector / no HNSW index** (`db/schema.sql`). Embeddings are a flat
   BLOB column; any "nearest neighbour" search in this sandbox is a linear
   scan in Python. This validates nothing about production's index-backed
   query latency.
3. **English has no local dictionary at all** (`db/build_db.py:load_en_vocab`).
   Every en `dim_word_senses.definition` is NULL. en lemmas come from
   `wordfreq`'s published frequency list plus tokens mined from the 76
   local EN test transcripts; only `part_of_speech` (via spaCy) and
   `frequency_rank` (via wordfreq) are real. `definition_match`-style
   prototypes and definition-based distractor prototypes cannot be built
   for English from this seed data without new synthesis.
4. **zh/ja definitions are English glosses, not native-language
   definitions.** CC-CEDICT and JMdict are both bilingual-to-English
   dictionaries. Every zh/ja sense's `definition_language_id` is English.
   Production supports a same-language (e.g. zh-language) definition of a
   zh word for a native-reading learner - no local source in this repo
   provides that, so it isn't representable here.
5. **zh vocabulary scale is much larger and broader than production's
   curated set.** Full CC-CEDICT is ~125k entries vs. production's curated
   ~23,870 zh senses (per `docs/recon-data-surface.md` §3) - it includes
   proper nouns, classical/literary entries, and technical jargon
   production has never curated. Don't treat zh coverage numbers from this
   sandbox as representative of production's curated scope.
6. **Embeddings and corpus-mined example sentences are capped at the top
   8,000 highest-Zipf senses per language** (`EMBED_TOP_N_PER_LANGUAGE` in
   `build_db.py`), not the full dictionary, purely to keep the build under
   a minute. A prototype working with a rare/long-tail sense will find no
   embedding and no example sentence for it.
7. **`simple` and `standard` definition levels are byte-identical** for
   every zh/ja sense seeded here. Production generates genuinely different
   text per level (two separate LLM outputs); CC-CEDICT/JMdict each give
   exactly one definition per entry, so this sandbox duplicates it. Any
   prototype that branches on `definition_level` for content will see no
   real difference for zh/ja.
8. **`word_assets` and `exercises` are seeded empty by design** - this
   sandbox may never call an LLM, and those tables exist in production
   specifically to hold LLM output. A harness-run prototype generator is
   expected to populate them, not `build_db.py`.
9. **`tests.vocab_sense_ids` / `vocab_token_map` and
   `questions.sense_ids` are all empty** (`[]`/`{}`) for every seeded row.
   No sense-linking pass (`.claude/skills/test-sense-linking`) has been run
   in this sandbox - a vocabulary-aware serving prototype that wants
   per-test vocabulary coverage has to compute it itself (e.g. by
   substring-matching `tests.transcript` against `dim_vocabulary.lemma`,
   which is exactly what the corpus-sentence-mining step in `build_db.py`
   already does, at a small scale, for embeddings).
10. **`learner_sim.py`'s response model is an assumption, not a port of
    production math.** It's a logistic-IRT-with-a-floor model chosen
    specifically to reproduce the MC-guessing-floor mechanism
    `docs/recon-serving.md` §4 blames for capping ELO's reachable ability
    spread at ~191 points - it is NOT the literal
    `sec_submission_rpcs_auth_gate.sql` ELO/BKT formula. Forgetting is a
    single global exponential half-life per learner; real forgetting is
    per-item and per-learner. Every number `simulate()` produces describes
    "does this selector mechanism work at all in a controlled world", never
    "real users will learn N% faster."
11. **`mock_llm.py` token/cost estimates are order-of-magnitude, not
    exact.** Tokens are estimated as `len(text)//4` (no real tokenizer
    wired in); per-token pricing is illustrative, not tied to any real
    OpenRouter rate card. Fine for comparing two pipelines' relative cost;
    not fine for reconciling against a real bill.
12. **`synthetic` mock-LLM output is linguistically meaningless** -
    template-filled placeholder text, valid only for
    latency/throughput/architecture measurement, never as a stand-in for
    real content quality.
13. **Harness concurrency measures the generator's own overhead, not real
    provider behavior.** `lab/harness.py`'s concurrency is threads in one
    Python process talking to a mock client that never touches a network -
    it says nothing about real rate limits or the cross-run budget-ceiling
    race documented in `docs/recon-generation.md` §6 ("three concurrent
    runs trip each other's ceilings on each other's spend").
14. **Classifier/counter noun-sense linking is partial by construction.**
    16/570 classifier pairs and 155/578 counter pairs have
    `noun_sense_id = NULL` because that noun's lemma wasn't found in the
    seeded zh/ja vocabulary (CC-CEDICT/JMdict don't guarantee 100% overlap
    with the curation JSON's noun list) - this is real, reported coverage,
    not a bug to silently paper over.

---

## 8. What was NOT done, and why

- **`raw/jmdict_eng.json` full dictionary (218,461 entries) was not loaded
  in full** - only `common: true` entries (22,630) were, to keep ja
  vocabulary at a scale close to production's own curated set rather than
  importing every archaic JMdict headword. The rest of the file is
  available locally if a later agent wants deeper ja coverage.
- **`tests/fixtures/dt_gold/*.json` was read but not loaded into any
  table** - it's a translation-grading gold set, not vocabulary/exercise
  seed data, and none of the 16 required tables fit it. Flagged, not
  silently dropped (§4).
- **No real embedding model, local or hosted, was used** - checked for an
  offline sentence-transformer (none installed) and the hard rule forbids
  a hosted call. The TF-IDF proxy is the best available option under those
  constraints, loudly documented as a proxy (§7 items 1-2).
- **No `dim_grammar_patterns` table** - it wasn't in the task's required
  16-table list, so it was left out to keep the schema exactly matched to
  what was asked for.
- **`user_skill_ratings`/`user_vocabulary_knowledge`/attempt tables are
  seeded empty, not pre-populated with synthetic history.** `learner_sim.py`
  generates learner trajectories in memory, on demand, when a later agent
  runs a serving prototype - baking a specific population into the static
  seed would have hidden a design choice (population size, ability
  distribution, number of simulated days) that a later agent should
  actually control per-experiment via `make_population()`/`simulate()`
  arguments.
