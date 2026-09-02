# Word List → Topics → Tests → Exercises — Implementation Plan (v2: similarity-routed)

Feature: user submits a list of target words; system finds existing topics
whose vocabulary is already lexically/semantically close to those words and
reuses them for fresh test generation, falling back to pattern-guided new
topic generation only when no close existing neighbor exists. Exercises are
then generated from the resulting tests via the existing pipeline.

**v1 rejected**: directly clustering submitted words via LLM and instructing
prose generation to force-include them produces unnatural, keyword-stuffed
text. v2 instead finds where similar vocabulary already lives naturally and
either reuses that context or uses it as a style anchor.

Reuses: [services/topic_generation/import_orchestrator.py](../../services/topic_generation/import_orchestrator.py),
[services/test_generation/orchestrator.py](../../services/test_generation/orchestrator.py),
[services/exercise_generation/orchestrator.py](../../services/exercise_generation/orchestrator.py),
existing sense embeddings ([dim_word_senses_embedding](../../migrations/dim_word_senses_embedding.sql)).

Out of scope: changing the daily automated topic-generation rotation
(ExplorerAgent/ArchivistAgent/GatekeeperAgent flow for organic topics) —
this feature adds a parallel word-seeded path, it does not alter the
existing one.

Open questions (not blocking, flagged for calibration once real data exists):
- Exact K for top-K neighbor lookup (default guess: 5, tune empirically).
- Whether `topic_vocabulary` (topic_id → vocab lemmas used) needs a
  materialized view for performance at scale, or a live join suffices at
  current data volumes.

---

## Step 1 — Schema: word-match tracking

**Intent:** Add persistence for tracking each submitted word's match outcome:
which existing word(s)/topic(s) it matched via similarity, whether it was
routed as reuse or generate-fallback, and whether it was later found (soft
coverage) in the resulting generated text. Migration only, additive.

## Step 2 — SimilarityMatcher service (dual backend)

**Intent:** Build `services/topic_generation/similarity_matcher.py` exposing
one interface with two backends: character n-gram Jaccard for zh/ja (no
embedding dependency) and embedding cosine for en (reusing existing sense
embeddings). Given a word and language, returns ranked nearest existing
`dim_vocabulary` entries, then resolves those to candidate topics via a
`tests.topic_id → tests.vocab_sense_ids → dim_vocabulary` join.

## Step 3 — Batch clustering via SimilarityMatcher

**Intent:** Cluster the submitted word list into scenario-sized groups using
the same per-language similarity backend from Step 2 (word-to-word, not
word-to-corpus), replacing the earlier plan's LLM-based clustering step.

## Step 4 — Reuse path

**Intent:** For clusters whose top-K corpus lookup returns at least one
nonzero-similarity candidate topic, skip topic authoring entirely and queue
a fresh test generation against that existing topic (via the existing
`production_queue` mechanism), tagging the queue entry and the Step 1
tracking rows with `match_mode='reuse'`, `source_batch_id`, and the neighbor
word(s)/topic(s) that produced the match.

## Step 5 — Generate-fallback path

**Intent:** For clusters whose top-K lookup comes back empty or near-zero
(cold start / genuinely novel vocabulary), build a synthesizer
(`services/topic_generation/agents/word_topic_synthesizer.py`) that takes
the best available neighbor topics (even weak ones) as few-shot style/theme
anchors and drafts a new `TopicCandidate` in that register — critically,
without instructing the LLM to force-include the literal submitted word.
Runs through the existing `TopicImportOrchestrator` novelty/quality gates
unchanged.

## Step 6 — Post-hoc coverage check

**Intent:** After test generation completes (either path), scan the
generated prose for each cluster's submitted words (substring/tokenizer
check per language) and update the Step 1 tracking table's coverage fields.
This is reporting only — it must never feed back into generation as a
constraint.

## Step 7 — Batch coordinator script

**Intent:** Add `scripts/run_word_list_import.py` that runs: clustering
(Step 3) → per-cluster similarity lookup (Step 2) → branch into reuse
(Step 4) or generate-fallback (Step 5) → `TestGenerationOrchestrator` →
`exercise_generation` orchestrator → coverage check (Step 6), all scoped to
one `source_batch_id`, printing a final per-word report (matched topic,
reuse vs. generated, covered vs. not).

## Step 8 — API route for submission and status

**Intent:** Add `routes/word_list_import.py` with `POST /api/word-list/submit`
(enqueues Step 7's script as a background job) and
`GET /api/word-list/status/<batch_id>` (returns stage progress plus, per
word: match mode, matched topic(s), and coverage), following the pattern in
`routes/test_intros.py`.

## Step 9 — Frontend submission UI

**Intent:** Add a minimal page/modal (textarea for words, language picker,
submit button, polling status table showing per-word match mode and
coverage) calling the new API routes, using the i18n key pattern already
established in `static/i18n/en.json` etc.

## Step 10 — End-to-end test coverage

**Intent:** Integration tests covering: SimilarityMatcher output for both
backends (zh/ja n-gram, en embedding), the reuse path end-to-end, the
generate-fallback path end-to-end (simulated cold start with no matching
existing vocabulary), the coverage check, and the new API routes, following
fixture patterns in `tests/test_topic_novelty_global_scope.py` and
`tests/test_test_gen_fail_closed.py`.
