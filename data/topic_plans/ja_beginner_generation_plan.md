# Plan — Generating the 100 N5/N4 Japanese tests through headless Claude

Status: **proposed** (2026-11-08). Nothing in this plan has been built or run yet.
Topic list: [`ja_n5_n4_topics.md`](ja_n5_n4_topics.md).

## 1. What already exists (and is reused unchanged)

The pipeline is already mostly provider-agnostic. Every stage that goes through
`services.llm_service.call_llm` switches to headless Claude when the process
default provider is `claude_cli`:

| Piece | File | Role |
|---|---|---|
| Headless transport | `services/claude_cli_client.py` | OpenAI-shaped facade over `claude -p --tools "" --output-format json`. Runs from a neutral cwd so CLAUDE.md is not loaded, strips `ANTHROPIC_API_KEY` so calls bill the subscription, and logs `llm_calls.model = claude-cli:<model>`. |
| Provider switch | `scripts/provider_arg.py` | `--provider claude-cli` calls `set_default_provider('claude_cli')` and caps concurrency at 2 (`clamp_concurrency`). |
| Harness contract | `.claude/skills/lingualoop-generation/SKILL.md` | System prompt via `CLAUDE_CLI_SYSTEM_PROMPT_FILE`. The generation prompts themselves stay in `prompt_templates`. |
| Test pipeline | `services/test_generation/orchestrator.py` `_generate_test` | Translate topic, then prose, jev tier, dedup, ELO seed, title, questions + judges + validator, audio, save, pitch + furigana payloads, then vocab (extract, then match or create senses, then token map, then per-question `sense_ids`). |
| Sense match/create | `services/vocabulary/sense_generator.py` | `prefer_existing=True`: reuses an existing sense when one fits (`vocab_sense_selection`) and writes a new two-level sense otherwise. Already goes through `call_llm`. |
| Tests to assets | `scripts/run_content_build.py` | `preflight`, `canary`, `tests`, `select` (rank the new tests' senses by frequency, drop those that already have assets), `ladder` (`VocabAssetPipeline` and then `LadderExerciseRenderer`). Already takes `--provider`, keeps a resumable state file, and fails closed on judge outages. |
| Deferred-word repair | `scripts/backfill_senses.py --provider claude-cli` then `scripts/relink_deferred_vocab.py` | Fills in words above the inline cap (`TEST_GEN_INLINE_ENRICHMENT_CAP`, 80). |

So "use headless Claude instead of OpenRouter" is mostly a flag. The work is in
the five gaps below plus one thin runner script.

## 2. Gaps found in the current code

1. **The phrase detector bypasses the provider switch.**
   `ProseWriter.__init__` (`services/test_generation/agents/prose_writer.py:42`)
   builds its client with a hard-coded OpenRouter base URL. That client is handed
   to `VocabularyExtractionPipeline`, and from there to
   `PhraseDetector` (`services/vocabulary/phrase_detector.py:81`), which calls
   `client.chat.completions.create` directly. Under `--provider claude-cli` this
   one call would still go to OpenRouter.
2. **Imported topics have no tier, and the orchestrator refuses topics without one.**
   `JSONTopicEntry` (`services/topic_generation/json_importer.py:19`) has no tier
   field, and `import_orchestrator.py:300` calls `insert_topic` without
   `target_age_tier`, although `insert_topic` already accepts it. The
   orchestrator raises on a topic with no tier (TASK-740).
3. **`run_batch` cannot target specific topics.** It takes *any* pending ja queue
   items (135 are pending today, most of them adult topics) and assigns a balanced
   tier schedule that ignores each topic's tier. `run_single(queue_id)` is the right
   entry point, because it uses the topic's own `target_age_tier`.
4. **There is nowhere to put the per-topic brief.** The plan gives each topic a format
   (dialogue/diary/notice/…) and a grammar focus. `topics` has no field for either,
   and `prose_generation` only takes `{topic_concept}`/`{keywords}`. The tier
   length range is far too wide for beginners: T1 is 0–500 characters and T2 is
   120–2000, so the existing T1–T2 tests came out at about 60 characters. Every
   test is also stored with `style='academic'`, because `insert_test` never writes
   `style`.
5. **There is one model for everything.** Under `claude_cli`, `_resolve_model`
   (`services/llm_service.py:197`) returns `CLAUDE_CLI_MODEL` for every task.
   We want Opus writing passages and questions and Sonnet handling the
   high-volume sense calls.

Some calls stay off the Claude CLI on purpose. They are not text generation, and
they are cheap:

- **jev tier classifier** (OpenRouter `/alpha/decisions`). Its per-language
  calibration tables were fitted against jev itself, so replacing it would undo
  ADR-029. It needs `OPENROUTER_API_KEY` and costs fractions of a cent per call.
- **OpenAI embeddings**, used by dedup, topic novelty and sense embeddings.
- **Azure TTS** for test and exercise audio.

## 3. Code changes (small, additive)

| # | Change | Files | Size |
|---|---|---|---|
| C1 | `ProseWriter.client = get_client()` (process default provider) instead of the hard-coded OpenRouter URL. `ClaudeCliClient` already accepts `response_format=json_object` and ignores the unprefixed OpenRouter slug. OpenRouter runs behave the same, because the default provider *is* OpenRouter. | `services/test_generation/agents/prose_writer.py` | XS |
| C2 | Per-task Claude model: `CLAUDE_CLI_MODEL_BY_TASK` env (e.g. `prose_generation=opus,title_generation=opus,question_*=opus,*=sonnet`). `call_llm` passes `task_name` into `_resolve_model`, which looks up the map and falls back to `CLAUDE_CLI_MODEL`. The `claude-cli:<model>` prefix is already parsed by `_build_argv`. | `services/llm_service.py`, `services/claude_cli_client.py` (docs only) | S |
| C3 | Topic import carries tier and lens: optional `target_age_tier` (and `distinctive_vocabulary`) on `JSONTopicEntry`, passed through `entry_to_candidate`, then to `insert_topic`. Entries without it behave as today. | `services/topic_generation/json_importer.py`, `import_orchestrator.py` | S |
| C4 | Per-topic generation brief: a `TopicBrief(format, grammar_focus, char_min, char_max, style)` dataclass and an optional `orchestrator.topic_briefs: dict[UUID, TopicBrief]`. In `_generate_test`, when the topic has a brief: (a) override `word_min/word_max` with `char_min/char_max`; (b) append the brief to the prose prompt through the existing `extra_instruction` parameter (already used for the dedup nudge), combined with the nudge on retry; (c) write `style` on the test row. With no brief there is no behaviour change. | `services/test_generation/orchestrator.py`, `services/test_generation/schemas.py` (`GeneratedTest.style`), `database_client.insert_test` | S–M |
| C5 | New runner `scripts/run_ja_beginner_build.py` (section 4). It reuses `run_content_build`'s state file, `phase_preflight`, `phase_canary`, `phase_select` and `phase_ladder` by import. Only the `tests` phase is new. | new file | M |

The prose brief appended through `extra_instruction` (Japanese, matching the
template) looks like this:

```
**追加の指定（このテストのみ）：**
*   **形式:** 会話（二人のやりとり。話者は「A:」「B:」で示す）
*   **文法の焦点:** 〜てしまう を自然に2回以上使う
*   **文字数:** 150〜300文字（上の文字数指定より優先）
*   **場面:** 日本での日常生活。登場人物は一般的な名前（例：田中さん）
```

Format to style mapping (`tests_style_check` allows academic, conversational,
business, casual, technical): dialogue → `conversational`; diary and
email/letter → `casual`; narrative and notice → `academic`.

## 4. The runner: `scripts/run_ja_beginner_build.py`

```
python scripts/run_ja_beginner_build.py --plan data/topic_plans/ja_n5_n4_topics.md \
    --provider claude-cli --phases import,preflight,canary,tests,select,ladder \
    [--only 1-10] [--resume RUN_ID] [--yes]
```

| Phase | What it does | Reuses |
|---|---|---|
| `import` | Parses the plan table into JSON entries: `topic` = English title + format + grammar focus (the concept the translator, embedder and dedup see), `languages=['ja']`, `target_age_tier` (N5→1, N4→2, but see open question Q1), `keywords` = a few target words, category from the theme (mapped to the existing 17 categories; new `Daily Life` and `Travel` categories if wanted, see Q3). Runs `ImportOrchestrator` with `skip_gatekeeper=True`, because the topics are hand-curated and ja-only. Novelty stays on. Records `plan # → topic_id → queue_id` in the state file. | `run_topic_import` machinery (C3) |
| `preflight`, `canary` | Unchanged. | `run_content_build` |
| `tests` | For each plan row not yet done: register its `TopicBrief` on the orchestrator, then call `orchestrator.run_single(queue_id)`. Afterwards read back the stored test: if jev assigned a tier **above** the plan's, set `is_active=false`, record it, and retry once with a "simplify" line added to the brief. A second overshoot is left inactive for manual review. Checkpoint after each topic. Runs with 2 workers (`clamp_concurrency`). | `run_single` + C4 |
| `select`, `ladder` | Unchanged. Ranks the senses the new tests introduced, drops those that already have `word_assets`, and builds ladder exercises for the rest through `VocabAssetPipeline` under the same provider. | `run_content_build` |
| `finish` | Prints the follow-on commands (section 5) and a per-test report: tier target vs assigned, characters, number of questions, senses linked/created/deferred, `vocab_sense_stats` shortfalls. | — |

Why not `run_content_build --tests 100`: it calls `run_batch`, which would pull
in the 135 older pending ja topics and ignore the plan's tiers (gap 3).

## 5. Run order (on a machine with `.env` and the `claude` CLI)

```bash
export CLAUDE_CLI_SYSTEM_PROMPT_FILE=.claude/skills/lingualoop-generation/SKILL.md
export CLAUDE_CLI_MODEL=sonnet
export CLAUDE_CLI_MODEL_BY_TASK='prose_generation=opus,title_generation=opus,question_*=opus'
unset ANTHROPIC_API_KEY            # the client strips it too; belt and braces

# 1. dry pass on 5 topics, then inspect them in the app
python scripts/run_ja_beginner_build.py --provider claude-cli --phases import,preflight,tests --only 1-5
# 2. the rest
python scripts/run_ja_beginner_build.py --provider claude-cli --resume <RUN_ID> --phases tests,select,ladder --yes
# 3. vocab tail beyond the inline cap
python scripts/backfill_senses.py --language ja --provider claude-cli
python scripts/relink_deferred_vocab.py --language ja
# 4. non-LLM assets
python -m scripts.backfill_sense_embeddings --language 3
python scripts/build_test_sentences.py --apply
python scripts/backfill_exercise_audio.py --language ja
```

Sentence-level L1 references (`sentence-reference-authoring`) are a separate
optional pass and are not part of this plan.

## 6. Size and cost

Per test, roughly: 1 translate, 1 prose, 1 title, 5–6 questions with about 10
judge calls, 1 phrase detection, and up to 80 sense calls. At N5/N4 most words
already have a sense (ja has about 6,100 fat-seeded senses), so many of those 80
are cheap reuse decisions. Call it about 40–60 CLI calls per test.

- **Tests:** 100 × ~50 = ~5,000 calls. At 2 concurrent and ~10–20 s per call
  (Opus calls are slower), that is about 8–12 hours of wall clock, best spread
  over several sessions because of subscription limits. The transport surfaces
  rate-limit errors and `run_content_build`-style checkpointing makes reruns
  safe.
- **Ladder:** about 5.5 min per sense (TASK-515). After the `select` filter, only
  senses the new tests introduce *and* that lack assets remain. That is probably
  a few hundred at most, and `--max-senses` caps it. If the number is large,
  switch this phase to the fat-seed path (`fat-seed-authoring`, $0.045/sense
  measured, already headless) rather than the online ladder.
- **Money:** only jev, embeddings and TTS are billed. Under the CLI transport
  `llm_calls.cost_usd` is written as 0, by design.

## 7. Verification

- Unit: `TopicBrief` threads into the prose prompt and the length override (mock
  `call_llm`); a topic without a brief produces the same prompt as today; C2's
  map resolves `question_literal_detail` through `question_*`; C3 round-trips a
  tier.
- Smoke: `scripts/smoke_test_generation_routing.py` under `--provider claude-cli`
  confirms that no request goes to `openrouter.ai/api/v1/chat` except jev
  (check the `llm_calls.model` prefixes for the run_id).
- Acceptance on the first 5: every test is stored at the planned tier (or
  flagged); length is inside the brief's range; the format is recognisable;
  4–5 questions survive; `vocab_sense_ids` is non-empty; furigana and pitch
  payloads are present; audio plays.

## 8. Open questions (need an answer before C4/C5)

- **Q1: N5 versus the T1 prompt.** The ja `prose_generation` T1 definition
  allows *present tense only*, but N5 grammar includes 〜ました, and 9 of the
  40 N5 topics are written in the past tense (#3, 11, 54, 57, 62, 64, 68, 70, 82). Options: (a) target those at T2 (likely
  where jev would put them anyway); (b) let the brief override "present only"
  for N5, accepting that jev may tier them T2; (c) rewrite those topics in the
  present tense.
  *Recommendation: (a).* It keeps the tier scale honest.
- **Q2: Should the overshoot policy deactivate tests?** The plan deactivates a
  test jev puts above its planned tier and retries it once. The alternative is
  to keep it at the assigned tier, which is how the pipeline behaves today.
- **Q3: Categories.** Map the themes onto the existing 17 categories, or add
  `Daily Life`, `Travel` and `Japanese Culture`? New categories are shared with
  other languages' topic generation, so adding them changes what zh/en explore
  next.
- **Q4: Listening or reading?** The runner defaults to `listening`, which
  generates audio for every test. N5/N4 learners benefit from both; generating
  everything as listening and letting the reading view use the transcript
  matches current practice.
