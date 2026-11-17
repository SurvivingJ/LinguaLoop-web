---
title: "ADR-047: How the app decides a learner already knows basic words"
status: accepted
date: 2026-11-17
---

# ADR-047: How the app decides a learner already knows basic words

> **Status: accepted — owner sign-off 2026-11-17.** Already in effect: step 1 (the frequency fill,
> applied to the live database 2026-11-17 after review) and the gloss-level part of step 5. Steps 2–4
> and 6 are not built; they are tasked as TASK-1004 in [[tasklist/fixes-2026-11-16.tasks]].

## Context

The prestudy preview showed 是, 都, 有, 不 as new or "unknown" to a learner taking
tests far above beginner level (TASK-994). Measured on the live database,
2026-11-17 (read-only):

**How p(known) is set today**
- A word sense's knowledge is one `user_vocabulary_knowledge` row per user and
  sense (BKT). With no row, readers fall back to a prior from
  `dim_vocabulary.frequency_rank`. That column holds a **Zipf score** from
  wordfreq 3.1.1, not a rank.
- There are two different priors:
  1. **Preview and planning** (`services/prestudy.prior_p_known`, and
     `priorP` in `static/js/prestudy/prestudy.js`): a logistic,
     `p = 1 / (1 + exp(-(1.5 * (zipf - ability) + ln(0.85/0.15))))`. Ability
     comes from `user_calibration_state.ability_zipf`, or 5.0 when missing.
     It returns a flat 0.3 when zipf is NULL.
  2. **Row creation in SQL** (`update_vocabulary_from_test`,
     `update_vocabulary_from_word_test(s)`, `update_vocabulary_from_word_tests_batch`,
     `bkt_contextual_inference`): a step function that ignores ability:
     zipf >= 6 gives 0.85, >= 5 gives 0.65, >= 4 gives 0.35, >= 3 gives 0.15,
     else 0.05. A NULL zipf gives **0.10**.
- Evidence sources:
  - Test questions: comprehension BKT (slip 0.10, guess 0.25, transit 0.02),
    applied only to the senses linked to each question.
  - Other passage words: `bkt_contextual_inference`, positive only, 30% x
    score of a comprehension step, and only when the score is at least 50%.
  - Word-test BKT (slip 0.05, guess 0.25, transit 0.05) comes from these
    sources: prestudy prime answers (where "I don't know" counts as wrong),
    dictation, Dual translation Produce (primed target words only), calibration
    (without side effects), flashcards, ladder exercises (with type-specific
    parameters) and the intro drill.
  - `bkt_infer_from_frequency` raises the floors of other tracked common words
    when a rarer word crosses 0.90.
- Status bands are the same in SQL `bkt_status` and the page: unknown < 0.2,
  encountered < 0.5, learning < 0.75, probably_known < 0.9, known otherwise.
  Prestudy counts a key word as new when p < 0.5, and drills p < 0.75.
  New-word admission vetoes words that are known or probably_known, and
  admits on evidence when p <= 0.40.
- Calibration: very few learners have a usable calibration. zh has 1 learner
  state with ability NULL. ja has 2, and only one has an ability (5.49). So the
  preview uses the 5.0 default for almost everyone. The preview does not
  filter `user_calibration_state` by mode, so a pronunciation-mode row could
  be read.

**What is wrong**
1. 846 `dim_vocabulary` rows have no Zipf (zh 241, ja 163, en 442). They
   include 是 7.17, 有 6.83, 不 6.76, 都 6.59 and 很 6.27. They appear in 173
   of 275 linked zh tests (726 test-word links), 54 en tests and 50 ja tests.
   For them the preview uses 0.3, and the first piece of evidence starts from
   0.10.
2. The SQL prior sits below the preview prior: at ability 5, a Zipf-4 word is
   0.55 in the preview but starts at 0.35 in SQL. So positive evidence alone
   can push a word down. 328 of 547 rows with only correct evidence (zh 182,
   ja 71, en 75) sit below the preview prior. 86 of them crossed from "not
   new" to "new".
3. One meaning is stored as several sense rows: definition level (simple or
   standard) times definition language. 是 has six rows, all sense_rank 1.
   - Tests link 926 zh "simple" rows and 6,795 "standard" rows. For 161 zh
     senses, both levels are linked by different tests, so knowledge is split
     across two rows. 很 has two BKT rows for one learner.
   - 56 zh test links point at cross-language gloss rows.
   - The preview's gloss lookup (`services/prestudy._load_senses`) matches only
     (vocab_id, sense_rank). It keeps whichever level PostgREST returns last,
     so the gloss shown is arbitrary.
4. The test account's own evidence is the main reason basic words stay
   unknown for it. In zh it answered word tests on Zipf >= 6 words correctly
   8 of 25 times, and Zipf 4-5 words 10 of 113 times. That looks like
   automated or "I don't know" answering. Other learners score 0.9-1.0 on
   comprehension for the same bands. For the test account, 158 of the 176 new
   words in the tests it passed come from its own BKT rows, not from the
   prior.

## Decision

Combined approach, in this order:

1. **Fix the data first (done in this change, pending review).** Fill every
   NULL `frequency_rank` that wordfreq can score, from the same function that
   wrote all the other rows (`services/vocabulary/frequency_service.get_zipf_score`,
   wordfreq 3.1.1). Applied 2026-11-17 after review: **770 rows** (zh 229,
   en 422, ja 119). 76 stay NULL: 64 wordfreq cannot score (chengyu, rare
   technical words, lemmatiser debris) and 12 ja compounds that wordfreq
   splits into several tokens and scores from the parts with no compound
   penalty (zh compounds get /10 per extra token; ja ones do not), e.g.
   色ごと 4.77, 水のみ 4.99, バットレス 3.86, みず 5.53 - values that would make
   rare words "probably known". Migration:
   `migrations/task994_vocab_frequency_fill.sql`; rollback
   `migrations/task994_vocab_frequency_fill_rollback.sql`.
2. **Frequency-and-ability prior (b) stays the one mechanism** for "a word far
   below the learner's level starts as probably known". Keep the existing
   logistic and its constants (K = 1.5; Zipf = ability gives p = 0.85). Make
   the SQL row-creation prior the same function of (zipf, ability), so evidence
   starts where the preview stands (task P1). There is not enough data to
   re-fit K or the 0.85 anchor: zh has 58 tracked senses from non-test
   learners.
3. **No part-of-speech function-word floor (f).** The closed-class POS tags in
   `dim_vocabulary` include rare literary items such as 有鉴于此, 由此观之,
   截至 and 斯くて, and the core particles (的, 了, は, が) are mostly not linked
   senses. After the fill, frequency already places true function words at
   Zipf >= 6, which gives p >= 0.96 at ability 5.
4. **Implicit evidence (c), calibration sweep (d) and learner self-marking (e)
   are specified as tasks, not built now** (P3 to P5). They change the learning
   model and need the measurement in step 6 first.
5. **Gloss and sense-row consolidation:** the preview picks the gloss at the
   linked sense's own definition level (applied in integration 2026-11-17 in
   `services/prestudy._load_senses`, without the proposed `source='llm_gloss'`
   filter; falls back to standard, then simple; `tests/test_prestudy_gloss_level.py`).
   Test links to "simple" or gloss rows are re-pointed at the native
   "standard" row, or knowledge is keyed per meaning. This is a data and model
   task (P6), not done here.
6. **How we know it is right:** for words the prior classes as probably_known
   or known (p >= 0.75) with no BKT row, track the share answered correctly at
   the learner's first explicit word test (prestudy, dictation, ladder,
   flashcard), by Zipf-minus-ability band. Target: at least 85% correct in the
   band where the prior says 0.85 or more. If it is below 80% over at least
   200 first answers, lower the anchor. If it is above 95% in the
   [ability-1, ability) band, raise it. The test account and other automated
   accounts are excluded from this measurement.

## Consequences

- Easier: about 73 fewer new key words over the 30 tests the test account has
  taken, for a learner with no history (engineer's figure, computed with the
  782-row version; the applied 770-row fill differs only on 12 ja compounds) (measured with the app's own
  `share_plan` on live data plus the filled values). Basic words stop being
  drilled in prestudy for fresh learners, the first evidence for 是 starts at
  0.85 instead of 0.10, and test recommendation (`task748` vocab-aware) and
  new-word admission ordering see real frequencies.
- Unchanged: existing BKT rows. The test account barely changes: 7 flips over
  30 tests, because its own low rows decide. Rows created under the NULL prior
  (42 rows, at most 2 learners per language) keep their too-low start unless
  P2 is approved.
- Side effects of the fill on other readers (measured by the reviewer):
  `selection_vocab_ability` (uvk crossing) moves by at most 0.02 Zipf for the
  5 learner-language pairs that have rows; `bkt_infer_from_frequency` can now
  raise low-evidence rows of the filled words (upward only) when the learner
  masters a rarer word; `calibration_anchor_pool` only picks the filled words
  up on its next manual refresh (`calibration_refresh_anchor_pool()`).
- Risk carried over, not caused, by the fill: with no calibration the prior
  uses ability 5.0, so a Zipf-3.9 word counts as not new (p 0.53). After the
  fill, words such as 学界, 偏好, 触及 join the ~19.7k already-ranked words
  treated that way. The default ability is a separate owner decision.
- Constrained: `frequency_rank` stays wordfreq Zipf. The ja compound scores
  already stored for ranked rows have the same inflation and are not touched
  here (task: score ja multi-token lemmas with a compound penalty, then
  re-measure). Any other source would
  need a separate column. 41 of 999 checked ja katakana rows were stored with
  an older tokenisation (0.4-1.7 lower); left as is.

## Alternatives Considered

- **Fill from the test-transcript corpus:** rejected. 275 zh tests are too
  small a corpus, and topic-biased. The counts would not be on the Zipf scale
  every consumer assumes. wordfreq is already the source of the other ~19.7k
  rows.
- **HSK or JLPT lists:** there is no list file in the repo, and `level_tag` is
  NULL on all 846 rows. A level list is a better input for (e), not for the
  frequency column.
- **Function-word floor by POS (f):** rejected for the reasons in Decision 3.
- **Overriding low BKT rows with the prior for high-frequency words:**
  rejected. It would erase real negative evidence. The test account's misses
  may be automation, but the model cannot know that.
- **How other systems do it, as far as I know (unverified details marked):**
  - Duolingo-style placement tests skip whole units on a pass, which is close
    to (d).
  - LingQ and Readlang let the learner mark words known in bulk, and count a
    word as known when the learner pages past it without a lookup. That is (e)
    plus (c), and is known to over-credit.
  - Anki-family tools import frequency or "known words" decks, which is (e).
  - Research vocabulary-size tests (VST, the LexTALE family) sample frequency
    bands and extrapolate, which is (d). Clearing a band is treated as
    knowing most of it, not all of it.
  - I am not certain of any of these systems' exact thresholds.

## Related Pages
- [[features/test-prestudy]] — "Fixes (2026-11-17)": the preview this prior drives
- [[features/vocabulary-knowledge]] — BKT rows and evidence sources
- [[database/schema.tech]] — `dim_vocabulary.frequency_rank` (Zipf), live changes 2026-11-17
- [[decisions/ADR-002-bkt-per-sense]] — knowledge per word sense
- [[tasklist/fixes-2026-11-16.tasks]] — TASK-994 (done), TASK-1004 (the open proposals)
