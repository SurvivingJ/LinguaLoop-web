---
title: Test Prestudy (tests as teaching material)
type: feature
status: in-progress
tech_page: ./test-prestudy.tech.md (not yet written — pending the open questions below)
last_updated: 2026-10-31
demo: ../demos/test-prestudy-demo.html
open_questions:
  - "ANSWERED 2026-10-29: ELO for a first attempt made after prestudy = reduced K with factor 0.5 (`test_attempts.prestudied = true`, `elo_reduction_factor = 0.5`, existing badge)."
  - "ANSWERED 2026-10-29: trigger = both — automatic prestudy block when the learner's unknown share for the test exceeds 0.25, and opt-in 'Study first' on the preview page and session card; per-language setting auto / ask / off."
  - "ANSWERED 2026-10-29: prestudy words do NOT count against `new_words_per_day`; prestudy writes word-test BKT evidence only and never admits to the ladder."
  - "ANSWERED 2026-10-29: a prestudy block spends tests-share minutes (0.5 × the test's time estimate, capped at 8 min)."
  - "OPEN: lesson content spend. Per-sentence L1 translations and answer explanations for ~305 active tests at test-generation prices is roughly $3–10 total; needs approval before Phase 2."
  - "OPEN: may lesson mode show the test's own questions before the attempt? Recommendation: never; use `questions.pool_source = 'lab_expansion'` items (Listening Lab) as teaching checks and keep the originals for the attempt."
  - "ANSWERED 2026-10-30: Chinese reading input = toneless pinyin typed, then a per-syllable tone picker; inline tone numbers or marks also accepted. Alternatives considered: tone marks required (hard to type), hanzi via IME (tests writing, not reading), audio recording (no grader). Open follow-up: whether the pinyin trainer's per-character tone game should replace the picker for multi-character words."
  - "OPEN: whether Azure TTS audio can be segmented per sentence (word timestamps are not stored today). Without it, sentence-by-sentence listening falls back to whole-clip audio plus the text."
---

# Test Prestudy (tests as teaching material)

## Purpose

Let a comprehension test be used as a *lesson* before (or instead of) being used as a
measurement. Today a test the learner is not ready for is a cold plunge that returns a low score
and a little BKT evidence. Prestudy turns the same passage, audio, token map and glosses into
preparation: a guided read with the learner's unknown words glossed, a short word quiz on the
words that block the passage, and later a sentence-by-sentence walkthrough with translations and
explained answers. It is the test-side complement of [[features/lookahead-preteaching]], which
prepares the learner through the practice ladder over several days; prestudy prepares them in the
minutes before the attempt, using the test itself.

## Why now — what the catalogue and the attempts show (live, 2026-10-29)

**The recommender has nothing in band to serve for the main Japanese learner.** Measured over
the 59 active ja tests against their current `user_vocabulary_knowledge`:

| Unknown share of the test's linked senses | Tests | Avg difficulty | Avg senses |
|---|---|---|---|
| 0–20% | 9 | 1.9–2.0 | 12–13 |
| 30–50% | 4 | 4.0–4.5 | 25–29 |
| 60–80% | 8 | 5.7–6.0 | 45 |
| 80–100% | 38 | 7.3–8.5 | 59–70 |

The target band for [[features/vocabulary-aware-test-selection]] is 5–25% unknown. Four tests sit
anywhere between 20% and 60%. Once the nine easy tests are used up, every "new" slot is a test
with 30–40 unknown words out of 40 — the three most recent ja failures scored 20%, 0% and 40% on
tests that were 29/38, 31/43 and 16/38 senses unknown at the time. Searching harder for an easier
test (ADR-024) cannot fix this; the content is bimodal. Prestudy makes the hard half usable.

**Vocabulary is not the only failure mode.** Three difficulty-1 ja tests with 0–2 unknown words
scored 7%, 31% and 44%. Prestudy must also scaffold the passage (listening, structure, question
type), not only the word list.

**The ladder cannot do this job yet.** Of the senses linked to active tests, those with the
3+ exercises the supply gate needs: zh 166 of 4,240 (3.9%), en 167 of 6,098 (2.7%),
ja 112 of 1,655 (6.8%). Anything that routes test preparation through ladder exercises reaches
under 7% of the words. This is the known blocker on [[features/lookahead-preteaching]].

**What every linked test already has, with no generation:**

- `tests.vocab_token_map` — an ordered `[surface, sense_id]` list covering the whole transcript
  (zh 98 of 126 tests, en 117 of 121, ja 59 of 60).
- A definition and an example sentence for **100%** of linked senses, and cross-language glosses
  in all three UI languages for every ja and zh sense (en senses are glossed in English only).
- Audio for every active test (zh 125, en 121, ja 59); furigana payloads on all ja tests;
  pinyin payloads on all zh tests.
- Question `sense_ids` on 1,195 of 1,424 questions; question types across six levels
  (literal detail, vocabulary in context, main idea, supporting detail, inference, author purpose).
- The pre-submit test payload (`GET /api/tests/test/<slug>`) already ships the transcript, the
  token map and personalised definitions; word clicks are blocked only by the client's
  `isSubmitted` check. The post-test word quiz builder works on any sense list.
- Listening Lab expansion questions (`pool_source = 'lab_expansion'`) exist for some passages and
  are not the scored questions.

**What is missing:** `questions.answer_explanation` is NULL on **all 1,424 questions**
(the comprehension-tests page's "results with explanations" describes the code path, not the
data). There are no L1 translations of transcripts outside Dual Translation's passage windows,
which are built only for tests the learner has already attempted. The ranker computes
`unknown_share` and the unknown senses but never sends them to the browser.

**Scale caveat:** 68 attempts by 2 learners across 32 tests. Every number above is one learner's
catalogue; the design below is chosen so it works at that scale and measures itself.

## User Story

> I opened a Japanese listening test and got 0%. It came back as a retry four days later and I
> still could not understand it. I don't want an easier test — I want to be taught this one.

A learner is offered a hard test. Instead of "Start", the card says "Study first (6 min), then
take it". They read the passage with their unknown words highlighted and tap to see glosses in
their own language, hear it sentence by sentence, answer a five-word quiz on the words that
matter most, and then take the test. Their score is real learning, not a guess, and the words
they met have evidence behind them when the ladder decides what to teach next week.

## How It Works

Prestudy is one feature with four **modes** (cheap to expensive) and four **triggers**.

### Modes

1. **Guided preview** (no content generation). The passage is shown before the attempt with the
   learner's unknown senses highlighted (three strengths: unknown / encountered / learning),
   tappable glosses in the learner's definition language, the example sentence, and for ja/zh the
   reading. Listening tests get the audio player plus the text — the point of prestudy is that the
   text is *not* hidden. A side panel lists the K highest-value unknown words (see "Which words").
   Furigana (ja) and pinyin with sandhi-adjusted tone marks (zh) are laid over the passage from
   the test's existing `furigana_payload` / `pinyin_payload`, aligned to the token map by
   character offset. Default: shown only on words below p 0.5, so the support fades as knowledge
   grows; the learner can switch to every word or off. Finishing the preview unlocks the prime.
2. **Word prime** (no content generation). A staged, interleaved drill on the K highest-value
   unknown senses, about **five exposures per word in random order** (decided 2026-10-30). For
   Japanese and Chinese the learner is tested on **reading before meaning**, so the word can be
   heard in the head before its sense is attached:
   1. *Reading, typed*: see the word, type its reading. No multiple choice for reading, so the
      recall is active (decided 2026-10-30). Japanese accepts kana or romaji (Hepburn and kunrei
      spellings, macrons or doubled vowels). Chinese accepts pinyin: toneless letters first, then a
      per-syllable tone picker (1 2 3 4 ·) appears; tone numbers or tone marks typed inline are
      graded directly and skip the picker. Syllables and tones are graded separately so the
      feedback says which half was wrong.
   2. *Meaning*: the word with its reading now shown, choose the gloss in the learner's language.
   3. *Reading, typed again*: the same as stage 1, spaced by at least one round.
   4. *Reverse meaning*: the gloss, choose the word from four passage words.
   5. *Use*: the passage sentence with the word blanked, choose the word (a passage cloze).
   6. *Practice, use*: one real ladder exercise for the word from the sentence-use group
      (cloze completion, typed cloze, particle selection, morphology slot, definition match).
   7. *Practice, judge*: one from the judgement group (semantic discrimination, spot the
      incorrect sentence, translation choice, jumbled sentence, synonym/antonym).
   Rounds 6 and 7 run only for words that already have ladder exercises; the other words are
   sent to the generation queue with reason `prestudy`. Reading-type ladder items (kanji to
   reading, hanzi to pinyin, tone identification) are not used here because reading is already
   typed in rounds 1 and 3. Exercise answers are recorded as ordinary exercise attempts tagged
   `source = prestudy` and update BKT with the exercise's cognitive-tier parameters; they still
   do not create a ladder row.
   Every item carries an **"I don't know"** button (decided 2026-10-30). It is an honest miss:
   the answer is shown in full as a teaching moment (for reading items the meaning is shown too),
   the item is re-asked two to four places later (up to three times, against two for a wrong
   guess), and one booster exposure of that word (a different cheap stage, meaning or typed
   reading, at most two per word) is appended to the end of the prime so the word gets more turns.
   The BKT update treats it as an explicit skip, as calibration already does: `is_correct = false`
   with a NULL answer, graded with guess 0, so it moves `p_known` down more than a wrong pick does.
   Each stage runs as a round over all K words in shuffled order, so the same word never comes
   twice in a row and reading always precedes meaning for every word. A miss re-queues the same
   item three to five places later, at most twice; then the answer is shown and the drill moves on.
   Distractors come from the same passage, same part of speech first. Words with no reading or no
   locatable passage sentence skip those stages (never the meaning stage). Every exposure is
   direct word-test BKT evidence, exactly as the post-test quiz is today; reading items also carry
   the ladder family they exercise (form recognition / form production) for a future per-family
   write. 
   **Readiness check (gates the attempt, decided 2026-10-30).** After the prime: five typed
   readings on the words the learner missed most (ranked by "I don't know" count, then wrong
   count, then lowest p_known), with no feedback until the end and an "I don't know" on each.
   Pass is 80% (4 of 5). On a pass, "Take the test" is offered. On a fail, one short extra round
   (typed reading plus meaning on the missed words) and one more check; after the second check
   the attempt is offered regardless, because prestudy never blocks a test. The score is stored
   as `readiness_score` on the session and is the readiness measure for the ELO analysis.

   **Post-test follow-up (decided 2026-10-30).** After the attempt, the unknown senses behind
   the questions answered wrong come straight back for a two-minute follow-up prime (typed
   reading, meaning, passage cloze) and then enter ladder Queue A1 with that evidence, as they do
   today from the post-test quiz. Senses that were primed and still missed are flagged for
   next-day review.

   **Spacing across days (decided 2026-10-30).** A word answered "I don't know" twice, missed in
   the readiness check, or primed-and-still-missed in the test gets one review the next day inside
   the normal practice session's Maintenance pool, via a `prestudy_followups` row. It is still not
   a ladder admission and does not count against `new_words_per_day`.

3. **Lesson walkthrough** (needs generated content). Sentence by sentence: the sentence, its
   glossed unknowns, an L1 translation (toggle), audio for that sentence where segmentation
   exists, and one teaching check every few sentences drawn from the Listening Lab expansion pool
   or from a short "which sentence says…" item built from the passage itself. The scored
   questions are never shown. Ends with a one-screen summary of the passage's main idea and the
   question types the test will ask, with a one-line strategy for each (e.g. "author purpose:
   look for evaluative words, not facts").
4. **Study-then-retry** (remediation). A test that scored below 50% comes back through the retry
   slot (ADR-006) with a guided preview and word prime attached, and the explanations of the
   questions the learner got wrong — the learner studies what they missed, then retries. ELO on
   the retry is already reduced by ADR-006, so this mode raises no new rating question.

### Triggers

| Trigger | Where | Default |
|---|---|---|
| Learner opt-in | "Study first" on the test preview page and on the session test card | always available |
| Over-threshold new test | the daily session inserts a prestudy block before a `new` slot whose unknown share for this learner exceeds a threshold (proposed 0.25) | on, per-language setting "Prestudy hard tests: auto / ask / off" |
| Retry slot | before every `retry` slot | on |
| Light prime | for in-band tests (5–25% unknown), a 60-second three-word card instead of the full preview | on |

### Which words

For a given test and learner, rank the test's unknown senses (`p_known < 0.5`, or no row and a
Zipf prior below 0.5) by: appears in a question's `sense_ids` (the words the test actually turns
on) first; then occurrences in the passage; then lower frequency rank. Take the top K, where K is
5 for the light prime, 8 for the word prime and unlimited for highlighting. Words already in the
learner's ladder or with a flashcard are shown but not quizzed.

### What it writes

- Word-prime answers: word-test BKT evidence (slip .05, guess .25, transit .05), the same path as
  the post-test quiz. No ladder admission from prestudy itself.
- A `prestudy_sessions` record: test, learner, mode, minutes, the **unknown share at the moment
  prestudy opened** (snapshot — see the evaluation trap in [[features/lookahead-preteaching.tech]]
  §8.1: never recompute it later), and the words shown and quizzed.
- On the following attempt: `test_attempts.prestudied = true` and, under the recommended ELO
  policy, `elo_reduction_factor` set so the existing badge explains the smaller rating move.
- Study time to the ledger ([[features/weekly-minutes]]) as kind `prestudy`.

## The full workflow: Study, Test, Produce (decided 2026-10-30)

Prestudy, the attempt and dual translation run as **one session item** with four parts, shown
as one card with four dots in the runner:

1. **Study**: guided preview and typed prime, readiness check (about 6 min).
2. **Test**: the attempt, `prestudied = true`, ELO at 0.5× (about 5 min).
3. **Follow-up**: two-minute prime on the unknown senses behind wrong answers.
4. **Produce**: dual translation ([[features/dual-translation]]) of one 2–4 sentence window of
   the same transcript, chosen to contain the most primed senses (tie-break: senses behind wrong
   questions, then shorter). The learner reproduces it from the L1 reference; the diff screen
   is the noticing surface as in DT today, plus one row per primed word: produced, produced in a
   different form, or omitted (about 5 min).

Why this is the right closing stage: the ladder's `contextual_use` family has no exercise type,
which caps every word's p_known at about 0.92; producing the primed words in their original
passage is that capstone, and each per-word row is the first `contextual_use` evidence the
system has had. It costs no new budget: dual translation is already a planner surface slot
([[decisions/ADR-021-plannable-surface-boundary]]), and the workflow fills today's DT slot with
the passage from today's prestudied test. DT's rule that passages come only from attempted tests
is satisfied at step 2. About 18 minutes end to end; the card says so up front, together with
the slots it uses (the test slot and the translation slot) and any test dropped.

What has to change for it: a second window selector in the DT passage builder (maximise primed
senses, not grammar coverage); the primed senses passed to the grader as target words so the
diff can report per-word production (a prompt slot plus a span-to-token-map match, not a new
grader); L1 references generated when the prestudy block is scheduled (the night before), not
lazily after the attempt; a `prestudy_workflow` queue item kind. Primed words omitted in Produce
join the next-day review list; systematic grammar errors go to the existing DT remediation
cards unchanged.

The demo has a Produce step on all five tests with hand-written sentence-level English
references, the window selector, a deterministic character diff (DT's Tier 0) and the per-word
produced / variant / omitted rows; the rubric grade and typed errors need the real cascade.

## Measurement (decided 2026-10-30, built in from day one)

Every prestudy session writes one `prestudy_sessions` row with: test, language, mode, trigger
(`full` / `light` / `retry` / `opt_in`), `unknown_share_at_open` (snapshot, never recomputed),
words shown and quizzed, exposures, first-try correct, "I don't know" count, booster count,
ladder exercises answered, `readiness_score`, readiness rounds, `ready`, next-day review senses,
minutes and their source, `tests_dropped_today`, and the Produce result (window, primed senses in it, produced, omitted, Tier 0 similarity, hints). The attempt that follows carries
`prestudied = true` and `elo_reduction_factor = 0.5`. The follow-up measures are the test score
and the 7-day `p_known` on the quizzed senses. The question the data has to answer: does a
prestudied attempt's score predict 7-day retention the way a cold attempt's does? If it does, the
0.5 factor is conservative; if it does not, prestudied attempts are memorisation and the factor
should fall. The demo shows the record as JSON on its final step.

## Constraints & Edge Cases

- **Questions are never leaked.** No mode shows the scored questions before the attempt. Lesson
  checks come from the expansion pool or are passage-built. Showing the real questions would turn
  the first attempt into a repeat and the rating into a memory test.
- **Prestudy changes the measurement it is judged by.** Word-prime evidence raises `p_known` on
  the test's senses before the attempt, so any after-the-fact unknown share is contaminated. The
  snapshot at open is the only valid difficulty measure for analysis.
- **Unlinked tests** (28 zh, 21 en) have no token map: guided preview still works as plain text
  with audio, but there is no highlighting or word prime. They are never penalised; the light
  prime is skipped.
- **Dictation, pinyin and pitch-accent modes** are productive tests on the same passage; prestudy
  for them is the guided preview only (seeing the text before dictation defeats the test, so the
  preview for dictation is audio plus glossed word list, not the transcript).
- **Time, shown honestly (decided 2026-10-30).** When a prestudy block's estimate reaches the
  cost of a test slot, the session card says so before the learner starts: "Study first: ~6 min ·
  1 fewer test today". The estimate counts five exposures per word, two ladder exercises where
  they exist, and the readiness check. A prestudy block adds minutes to a day the planner already filled. Under the
  recommended policy it spends tests-share minutes, estimated at half the test's time estimate
  and capped; the planner may then hydrate one fewer test. Opt-in prestudy outside the session is
  free time, like extra practice rounds (ADR-036).
- **Repeat attempts without a retry slot** still earn zero ELO (status quo); prestudy does not
  change that.
- **Lesson mode content** is per test, generated once and cached (same rule as word assets).
  Without it, lesson mode is simply unavailable and the card offers guided preview.

## Business Rules

- Prestudy never blocks taking a test. "Take it cold" is always one tap away.
- The scored questions and answers are never shown before the attempt.
- A prestudied first attempt is recorded as a first attempt with `prestudied = true` and earns ELO
  at factor 0.5 for both user and test (decided 2026-10-29).
- Word-prime answers are word-test evidence. Prestudy does not admit words to the ladder and does
  not count toward `new_words_per_day`.
- Every primer item offers "I don't know"; it is recorded as an explicit skip (wrong, no answer),
  lowers `p_known` more than a wrong guess, and earns the word extra turns in the same prime.
- For Japanese and Chinese, a word's reading is tested before its meaning, and every primed word
  gets about five exposures in interleaved random order (typed reading, meaning, typed reading again, reverse
  meaning, passage cloze), plus up to two real ladder exercises where the word has them. Reading is
  always typed, never multiple choice.
- Unknown share is snapshotted when prestudy opens and never recomputed.
- Every learner-visible string exists in all four locales.

## Build plan (phases, not tasks yet — task decomposition waits on the open questions)

**Phase 0 — expose and unlock (no new content; S–M each).**
- Endpoint `GET /api/tests/<slug>/prestudy`: the learner's unknown senses for the test with
  gloss, reading, example, passage sentence (via token map), occurrence count, question-linked
  flag, and the snapshot unknown share. Server-side, from `recommended_tests_ranked`'s coverage
  logic or a small sibling RPC.
- A `prestudy` view in `templates/test.html` and the session player
  (`static/js/session/players/reading_listening.js`): render the transcript with highlighting,
  lift the `isSubmitted` gate for word popovers in this view only, keep furigana ruby when
  wrapping tokens (today's `wrapTranscriptWords` drops it).
- Word prime before the attempt, reusing `build_quiz_with_distractors` and
  `POST /api/vocabulary/word-quiz`.
- `test_attempts.prestudied` plus the ELO policy in `process_test_submission`; "Study first" on
  `templates/test_preview.html`.

**Phase 1 — session integration (M–L).**
- New queue kind `prestudy` in `build_session_queue`, added to `_valid_block_ids`, attached to the
  test it precedes, with the threshold rule and the retry-slot rule; a player in
  `player_registry.js`; per-language setting on the Daily session card
  ([[features/session-budget-settings]]).
- `prestudy_sessions` table and ledger kind.
- Measurement: prestudied vs cold first attempts on score, and 7-day `p_known` on the test's
  senses, both against the snapshot unknown share.

**Phase 2 — lesson content (L, spend approval).**
- Per-sentence L1 translations for active tests: extend the Dual Translation passage builder to
  unattempted tests and store per sentence, or a dedicated `test_sentence_translations` table.
- Backfill `questions.answer_explanation` (currently 0 of 1,424) with the entailment judge's
  evidence as the seed; these also fix the empty post-test review today.
- Sentence-level audio: check whether TTS can return boundaries; otherwise whole-clip.
- Lesson walkthrough player; question-type strategy strings per type and locale.

**Phase 3 — join the ladder.** The prestudy word list is a natural, test-pinned Queue B source
for [[features/lookahead-preteaching]] once the supply gate is lifted: words the learner met in
prestudy and still missed in the attempt are the strongest demand signal for exercise generation
(`_request_generation`). ADR-026 chose a pool over a pinned test for *multi-day* pre-teaching;
prestudy is same-day priming, so the two coexist — note the tension in the tech page.

## Implementation — "Study first" on the preview page (2026-10-31)

Built (repo; the ELO migration is not yet applied live):

- **Entry point.** The test preview page shows a "Study first" button under "Start Test" for the
  comprehension modes (listening, reading). It opens `/test/<slug>/prestudy?type=<mode>`.
- **Page.** `templates/test_prestudy.html` + `static/js/prestudy/prestudy.js`, ported from the demo:
  Preview (passage with new words highlighted, furigana/pinyin on new words, tap-to-gloss popover,
  ranked key words) → Word prime (typed reading → meaning → typed reading → reverse meaning →
  passage cloze → two ladder exercises, interleaved; "I don't know" on every item, retries and
  booster turns) → readiness check (up to five typed readings, 80% to pass, one extra round, never
  blocks) → Ready. Every string is an i18n key in en/es/zh/ja.
- **API.** `GET /api/tests/<id>/prestudy` (`services/prestudy.build_prestudy_payload`: passage, word
  map, glosses in the learner's definition language, their BKT rows, trimmed ladder exercises, and
  only the *sense ids* of each question — never question text, choices or answers).
  `POST /api/tests/<id>/prestudy/evidence` records one word-test evidence point per sense (majority
  of its answers; "I don't know" counts as wrong; senses outside the test are dropped) through
  `update_from_word_tests_batch(side_effects=False)`, so nothing is admitted to the ladder or
  counted against `new_words_per_day`.
- **ELO 0.5.** "Take the test" leaves a `sessionStorage` marker (6 h); `test.html` then submits
  `prestudied: true`. `routes/tests.py` passes `p_prestudied` to `process_test_submission` only when
  true and falls back to the 8-argument call if the function has no such parameter (PGRST202).
  `migrations/prestudy_elo_factor.sql` adds `test_attempts.prestudied` and the 9-argument function
  (first attempt: user and test K × 0.5, `elo_reduction_factor = 0.5`). Skipping from the preview
  step without answering anything takes the test cold at full K.

### Workflow completed (2026-10-31, second pass)

- **Measurement.** `POST /api/tests/<id>/prestudy/session` opens a `prestudy_sessions` row when
  the page loads (unknown share snapshotted at open). The evidence call completes it with the
  measurement record (words shown and quizzed, exposures, first-try, IDK, boosters, ladder
  exercises, readiness score and rounds, minutes, tests dropped), clamped server-side and
  restricted to the test's senses.
- **Server-verified ELO.** Submit checks for a completed prime session for this test in the
  last 6 h; that, not the client flag, decides `prestudied`, and the session is marked
  `consumed` with the attempt id. The client flag only counts while the table does not exist.
- **Ladder exercises** answered in the prime write `exercise_attempts` rows with
  `source = 'prestudy'` and exercise-type BKT (first attempt only); no ladder row, no practice
  minutes. Primed words with no exercises are queued for generation (reason `prestudy`).
- **Minutes** go to the ledger as kind `prestudy` (shown on the Study Plan's weekly minutes);
  `minutes_source` is `tests_share` when run from the daily session, else `free`.
- **Next-day review.** IDK twice and readiness misses (derived server-side from the answers),
  primed-and-still-missed words (from the follow-up) and words omitted in Produce become
  `prestudy_followups` rows due tomorrow (learner-local). Maintenance practice sessions serve
  one exercise per due sense (at most 5); any attempt on the sense completes it.
- **Post-test follow-up.** Test results (standalone and in the session) offer "Review the words
  you missed": the prestudy page in `mode=followup` primes the unknown senses behind wrong
  answers (typed reading, meaning, passage cloze; at most 5 words). That evidence is written
  with side effects, so the words enter Queue A1 as the post-test quiz's do.
- **Produce.** After the follow-up, `POST /api/tests/<id>/prestudy/produce` picks the 2-4
  sentence window with the most primed senses (then wrong-question senses, then shorter) whose
  references clear the language's tightness floor (ja 0.65, zh 0.70, en 0.60) and opens it
  through the shared `open_range_passage` helper; the DT page grades it with the primed words as
  target words. The result is stored on the prime session; omitted words go to next-day review.
  From the daily session, "Back to today's session" makes the session's translation slot use
  this window.
- **Daily session.** `GET /api/study-session` adds `kind: 'prestudy'` items (setting `auto`):
  full before new tests over 25% unknown, light (three words, reading and meaning, about a
  minute, no readiness check) for 5-25%, and before every retry slot. The block's card
  (`static/js/session/players/prestudy.js`) shows the minutes and "N fewer tests today"; when
  pending blocks cost a test slot (`test_budget_minutes / tests`), that many plain new tests
  move to the end as optional (`is_bonus`, `deferred_for_prestudy`). Every reading/listening test
  card carries a "Study first" banner (highlighted under `ask`). Setting: "Study before hard
  tests: Automatically / Ask me / Off" on the Study Plan's Daily session card
  (`user_study_plans.prestudy_mode`).

Still not built: lesson walkthrough (mode 3) and study-then-retry answer explanations (need the
content spend), sentence-level audio, the dictation-mode preview variant.

## Demo

`wiki/demos/test-prestudy-demo.html` is a standalone page showing modes 1 and 2 on five real tests
(three Japanese, two Chinese) with their token maps, three-language glosses and the main learner's
real knowledge rows (exported 2026-10-29; scored questions deliberately excluded). It shows the
trigger per test, the frozen snapshot vs the recomputed unknown share, the key-word ranking,
the gloss popover, the word prime with local BKT updates, and the rows a session would write.
Regenerate with the scratch scripts `export.py` + `build.py` (not in the repo).

## Open Questions

See frontmatter. Four were ANSWERED by the developer on 2026-10-29 (ELO 0.5, both triggers, no
quota counting, tests share). Three stay OPEN: lesson-content spend, teaching checks never using the
scored questions (recommended policy, not yet confirmed), and sentence-level audio. The tech page
and task breakdown can now be written.

## Related Pages

- [[features/comprehension-tests]] — the tests being reused (its "results with explanations"
  claim is stale: no explanations exist in the data)
- [[features/lookahead-preteaching]] — multi-day preparation through the ladder; this is the
  same-day complement
- [[features/vocabulary-aware-test-selection]] — why selection alone cannot reach the band
- [[features/session-budget-settings]] — settings card and new-word quota semantics
- [[features/practice-extra-rounds]] / [[decisions/ADR-036-open-ended-practice-beyond-budget]]
  — the precedent for optional work outside the budget
- [[decisions/ADR-006-retry-slot-reduced-elo]] — the retry slot and reduced-K mechanism
- [[decisions/ADR-024-vocabulary-aware-test-selection]] — the 5–25% band
- [[features/dual-translation]] — the Produce stage of the workflow; same transcripts, L1 reference per learner L1
- [[features/dictation]] — same passages, productive mode
- [[features/vocabulary-knowledge]] — the BKT evidence prestudy writes
- [[pages/study-session]] — where the prestudy block would sit
- [[database/schema.tech]] — `tests.vocab_token_map`, `questions.sense_ids`, `test_attempts`
