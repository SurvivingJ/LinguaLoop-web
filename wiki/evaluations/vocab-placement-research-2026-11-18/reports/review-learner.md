# Learner-side review of the vocabulary placement draft (TASK-1073, review stage)

Written 2026-11-18 by the learner-side product reviewer, working independently of the other reviewer. I read
`placement/draft-design.md` in full (Parts A–E) and the four research reports (`research-literature.md`,
`research-products.md`, `research-audit.md`, `research-simulation.md`). Nothing was written to the wiki, the code or
the database. I ran only read-only SELECTs (quoted in §4) and wrote only under `placement/` (`review-learner.md` and
`review_learner/`).

**Reviewer stance.** I review as a serious learner: JLPT N3 aiming for N2, HSK 4 aiming for HSK 5, and a Japanese-L1
learner of Chinese. I tried to refute the draft on length and fatigue on a phone, how reading items feel, beginner and
advanced frustration, whether the result means anything in the goal-path report, retakes, whether practice changes,
and anything that feels gamified or dishonest.

**Owner decisions taken as fixed:** the adaptive four-option check with a stopping rule; no fake words, pseudowords or
Yes/No self-report; meaning and reading for zh and ja, meaning only for en. None of the findings reopens them.

**Labels.** MEASURED = read from code (file:line), the live database (SQL and output in §4) or a cited report.
ESTIMATE = simulation or arithmetic on stated inputs; simulation results hold only for the research stage's learner
model. INFERENCE = reasoning I did not test.

**Draft line numbers** refer to `placement/draft-design.md` as read on 2026-11-18.

---

## 0. Verdict

**Revise before synthesis.** From the learner side the core mechanics are right and I would keep them: the meaning
item shows characters only, the reading is asked only after a right meaning, there is one combined reveal, scoring is
design-based (ADR-051), placement is its own evidence kind, and every result is a range. Those are the parts a
WaniKani/Pleco-literate learner trusts.

What the learner actually sees and gets afterwards is not ready:

1. **The level line misplaces exactly the learners who want it** (L1, blocker). For learners whose true level is
   HSK 2–5 or N4–N2, the "Most words up to about HSK k" line is within one level for only 6–54% of them, mostly
   placing them two or more levels too low. More items do not fix it.
2. **The headline is a number about the check's own word pool**, usually "Fewer than…" or a range about 1,100 words
   wide (L2).
3. **"End now" produces no result** (L3).
4. **"About 5 minutes" is really about 6–7** (L4).
5. **Beginners tap "I don't know" about 38 times out of ~50** (L5).
6. **The "meaning only" words, the owner's target case, are pushed out of practice** rather than drilled (L6). The
   copy also promises a practice hand-off that may be switched off at launch (L7).
7. **Three item defects** give free credit to the cognate learners the feature is built for:
   - Japanese words with Chinese definitions keep a `——` headword prefix (L8).
   - Japanese reading items can be solved by matching the okurigana, and tone or long-vowel errors are almost never
     tested (L9).

---

## 1. Summary of findings

| # | Severity | Section | Finding |
|---|---|---|---|
| L1 | blocker | tech §5.3, §8; prose 7 and Constraints; ADR-058 d.6; PQ2; TASK-1086 | The level line misplaces mid-level learners (true HSK 2–5 / N4–N2: within one level for 6–54%) |
| L2 | major | prose 7; tech §8 result table; ADR-051 copy | The headline is a pool count: "Fewer than…" for 84% of zh learners below HSK 1 placement, about 1,100-word ranges otherwise |
| L3 | major | tech §5.1 eligibility vs §8 "End now"; §14 close_stale | "End now" and abandoned sessions get no estimate (ADR-051 needs ≥ 10 per band) |
| L4 | major | prose 1, 6; tech §7; E11; PQ10; §17 d.5 | "About 5 minutes" is about 6–7 minutes at the only real learner's measured pace, plus a server round trip per tap |
| L5 | major | prose 6; tech §6 warm-up; §15 entry points; PQ7 | Beginners answer about 50 items, about 77% of them not right; "Beginners usually finish early" is not true |
| L6 | major | tech §10; ADR-059; PQ20; prose 8 | "Meaning only" words are pushed out of practice, and the drill they would reach cannot show pinyin |
| L7 | major | Part D note on TASK-1081; prose 8; §8 next steps | Launch may run with the evidence hook off while the copy says practice uses the answers |
| L8 | major | tech §2 rule 5; E9; TASK-1077 AC; TASK-1091 | The cross-CJK strip misses the ja/zh `headword ——` form: 343 ja/zh items stay answerable by string matching |
| L9 | major | tech §2 rules 3, 4, 6; §8; §16; PQ3, PQ19 | Reading items rarely test the errors target learners make (zh tones about 11%, ja special morae about 4%); 19% of ja kanji+kana items are solvable from the okurigana |
| L10 | major | tech §9 growth, §12 pooling; PQ8 | A retake's headline pools 180 days, so progress shows at roughly half size |
| L11 | minor | tech §3 probes; PQ4 | Probes are unscored and make the reveal misleading; "probes make it uninformative" is false at ≤ 3 per test |
| L12 | minor | prose 1; tech §5.2, §8 intro | "A guess does not change the result on average" is false for informed guesses, and the instruction suppresses partial knowledge |
| L13 | minor | tech §8 goal-path paragraph; §9 | The placement leaves the goal-path level bars unchanged; its only footprint there is the unreliable level line |

---

## 2. Findings

### L1 — blocker — The estimated exam level is wrong for the learners who care about it

**Section.**
- Prose "How It Works" 7, the third bullet (draft:102-103).
- Prose Constraints, "The exam level is an estimate … right within one level for about 4 learners in 5" (draft:131-133).
- Tech §5.3 (draft:417-435) and §8 result table (draft:546).
- ADR-058 decision 6 (draft:1030-1033), PQ2 (draft:1700), E13 (draft:213) and TASK-1086.

**Problem.** The "80–86% within one level" figure is a population average. In the simulation, 58% (zh) and 67% (ja)
of learners have a true "knows the word" level of 0, and the design places them trivially at 0. For the learners who
have an exam goal, the D3S point placement is mostly wrong, and usually wrong downward by two or more levels:

| true level (m+r) | zh within one level | zh 2+ levels below | ja within one level | ja 2+ levels below |
|---|---|---|---|---|
| HSK 2 / N4 | 6% (n 102) | 82% | 21% (n 157) | 67% |
| HSK 3 / N3 | 14% (n 77) | 75% | 36% (n 81) | 41% |
| HSK 4 / N2 | 24% (n 92) | 61% | 48% (n 97) | 52% |
| HSK 5 / N1 | 41% (n 90) | 49% | 82% (n 264) | 18% |
| HSK 6 | 60% (n 141) | 40% | | |

ESTIMATE: D3S at the 60-item snapshot in the research stage's `raw_main.json`, 4,000 learners; script and output in §4.

Ruling out the obvious explanations (all ESTIMATE, 8,000 learners in `review_learner/simout/`):
- **It is not noise.** More items do not help. zh true HSK 3 is within one level for 12% at 40 items, 15% at 60 and
  11% at 90. zh HSK 4 goes 26%, 21%, 21%.
- **It is not only the S8 assumption.** With the exam-level effect switched off (`gamma_max=0`), zh true HSK 2–5 is
  within one level for 12–38% and ja N4–N2 for 28–73%. The errors then split above and below.
- **It is not starved bands, although bands 6–7 are starved.** D3S gives bands 6–7 (which hold most HSK 1–3 words)
  only 2.0–6.0 items. Forcing ≥ 5 items in bands 4–7 changes nothing (zh HSK 3: 15% → 12%).
- **The cause is the rule itself (INFERENCE).** "Number of leading levels whose cumulative share is ≥ 80%" turns a
  share error of a few points (level-share MAE 7.7–10.7 points [SIM Table 4b]) into a jump of several levels for
  anyone whose cumulative shares hover near 80%, which is every mid-level learner.
- **Level strata (D3L) help but are not enough:** zh 39–67% and ja 44–70% for true levels 2–6.

The shown 95% range (lower–upper of §5.3) was never simulated. For these learners it will often read "Up to HSK 5 at
most" (lower = 0), which is true and useless.

**Learner view.** I passed HSK 4. If a five-minute test tells me "Most words up to about HSK 2 (estimate)", I stop
trusting everything else on the page, the range included. The goal path is built around this claim.

**Correction.**
1. Do not ship the threshold level line in v1. Set PQ2's default to "no" and keep TASK-1086 blocked.
2. Replace the evidence in E13, PQ2, the prose Constraints and the ADR-058 Context with the per-true-level table
   above, not the pooled 80–86%.
3. Add a gate to TASK-1087 (V0): within one level ≥ 70% **for every true level 1–6** (zh) and **1–4** (ja), for the
   shown range as well as the point, before any level copy ships.
4. If a level signal is wanted before V5/S8 data exists, the only defensible v1 form is the learner's **goal level
   share with its range** ("HSK 4 words in the check: about 40–70% recognised, estimate"). It uses the S_ℓ and
   Var(S_ℓ) already defined in §5.3, and its error stays visible as a range instead of becoming a level jump. It
   carries the same S8 caveat as OQ34, so it is the owner's call (new PQ). It is not a reason to keep the threshold
   line.

**Evidence.**
- Scripts `review_learner/level_by_true.py` (output `level_by_true_out.txt`), `place_by_len.py`
  (`place_by_len_out.txt`), `compare_floor.py` (`compare_floor_out.txt`), `place_designs.py`
  (`place_designs_out.txt`) and the `gamma_max=0` run (`place_gamma0_out.txt`).
- Placement rule: `sim/sim.py:287-294`. Band × level composition: `sim/out/pool_stats.txt`.

### L2 — major — The headline is a count of the check's word pool that most learners cannot use

**Section.** Prose "How It Works" 7 (draft:97-101), tech §8 headline row (draft:544), §5.1 labels (draft:401-404),
PQ1 and PQ9.

**Problem.** "You recognised the meaning and the reading of about X–Y of the 3,623 Chinese words the check draws
from" has two problems for a learner:
- **The denominator is meaningless to them.** The pool holds about a third of each HSK 1–5 level and 46% unlisted
  words [SIM §2.1], and it will change when the zh pool refresh lands (PQ14).
- **ADR-051 rule 4 often turns the range into a one-sided "Fewer than {hi}".** At the stop point (ESTIMATE, 8,000
  learners):
  - zh learners below HSK 1 placement (58% of the zh population, mean 608 true m+r words): **84%** get "Fewer than…".
  - zh true HSK 1–2: **24–29%** get "Fewer than…".
  - Everyone else gets a "Rough" range about **1,100–1,200 words wide** (zh) or **about 1,000** (ja). For an HSK 4
    learner with ~1,740 true m+r pool words that is roughly "1,150–2,350".

With L1 removed, nothing on the result screen anchors the learner. The draft does not lead with what is concrete and
actionable: *this test's own words*.

**Correction.**
1. Lead the result screen with this test's outcomes, as answers rather than estimates: "Of the 41 words you saw: 14
   meaning and reading · 6 meaning only · 21 new to you". Each group is tappable, with its action ("Practise these
   readings" → L6; "Learn these" → Queue A2).
2. Show the range second, with its label: "Across the check's 3,623 words: about X–Y (rough estimate)". Use a dot
   strip or band [LIT A10-66].
3. When `lo = 0`, phrase it as "Most of the check's words are still new to you (fewer than {hi} of {N})" instead of a
   bare "Fewer than {hi}".
4. Keep the two-range zh/ja display (PQ1), but show the second range only when it differs from the first by more than
   the rounding. For English-L1 learners the two overlapping ~1,100-word ranges are noise [SIM §3: 5–12% of their
   meaning-known words lack the reading].

**Evidence.** `review_learner/labels.py` → `labels_out.txt`. ADR-051 rule 4 (`wiki/decisions/ADR-051-vocabulary-size-from-calibration-frame.md:45-49`).

### L3 — major — "End now" and abandoned sessions give the learner no result

**Section.** Tech §5.1 eligibility amendment (draft:395-401), tech §8 "End now" (draft:537-538), §14
`calibration_placement_close_stale` (draft:725-728), §15 resume.

**Problem.** These parts of the draft contradict each other:
- §8 promises a result after End now once the warm-up is complete.
- §5.1 says "A placement the learner ended early uses ADR-051's gate unchanged".
- ADR-051's gate is "No estimate below 10 distinct lemmas in any band" (ADR-051:45). A placement has about 2–8
  meaning items per band [§12; `compare_floor_out.txt`], so a learner-ended placement can never pass it unless older
  check answers exist.

So a learner who taps End now at item 45 after four minutes gets "Not enough answers yet". An abandoned session
(phone call, app switched; closed after 2 h) gets no result at all, yet its BKT write still runs (draft:727-728).

The amendment's own justification, that the Jeffreys interval stays honest at small n, holds at short lengths too.
D3S 90% coverage (ESTIMATE, 8,000 learners) is 92%/95% (zh, meaning / m+r) and 90%/92% (ja) at 20 items, and
88–94% at 25–35 items. The intervals are just wider: ±24–27% at 20 items.

**Correction.**
1. Extend the eligibility amendment to `stop_reason ∈ {learner, abandoned}` once the warm-up is complete and at least
   20 items are answered. Label by ADR-051 rule 4 as usual and add "You ended early, so the range is wider".
2. Compute and freeze the result for abandoned sessions at close, and show it on the next visit.
3. Lengthen resume from 2 h to 24 h. Phone sessions get interrupted.
4. Add a unit case to §19: End now at 20/30/45 items returns a result.

**Evidence.** Draft lines cited above. `review_learner/short_cover.py` → `short_cover_out.txt`.

### L4 — major — "About 5 minutes" is about 6–7 minutes at measured pace

**Section.** Prose 1 and 6 (draft:79-80, 94-96), tech §7 expected-length table (draft:517-524), E11 (draft:211),
PQ10, §17 decision 5 (draft:822-824), §19 latency (draft:866-867).

**Problem.** The 5-minute figure comes from the simulation's time model (`sim/sim.py:37-38`):
- per-item latency plus an assumed 1.5 s after a miss;
- meaning latencies pooled with 110fb390, the account [AUD §3.1] judges automated ([SIM §7] query 1 lists both users).

The only real learner's measured **cycle** (gap between consecutive answers, gaps ≤ 60 s, which includes reading the
reveal and tapping on) is MEASURED at **6.57 s per meaning item** (median 5.03 s) and **7.50 s per reading item**
(median 5.39 s); Q1 in §4. The simulation used 4.55–5.84 s and 4.04–8.62 s.

At the simulation's item mix this gives (ESTIMATE):

| learners | approx. minutes at measured cycle |
|---|---|
| zh/ja intermediate and advanced | 6.6–7.0 |
| English-L1 beginners (who sometimes stop early) | 5.7 |
| English, 40 meaning items | about 4.4, not "3–4" (INFERENCE; en not simulated) |

That learner is the developer. A newcomer is probably slower (INFERENCE).

On top of that, every answer waits for a server round trip, because the next item is built after the answer (§17
decision 5), and the draft itself notes "host jitter 20–50× is known" (draft:866-867). On a phone a visible stall
after every tap is the most irritating thing a quiz can do (INFERENCE).

**Correction.**
1. Make the copy honest: "about 7 minutes" for zh/ja and "about 4–5" for en. Or keep "about 5" and cap by time:
   no new word after 5 minutes elapsed or 50 items. Cost (ESTIMATE, interpolating [SIM §3.2]): the D3S m+r 90%
   half-width goes from about ±12% to about ±13.3% of the pool.
2. Show "about N minutes left" rather than "items / cap", because reading items appear unpredictably.
3. Remove the per-tap wait. With each item, the server pre-computes both possible next items: if right, the reading
   item; if not right, the next meaning item under the not-right tallies. The client then renders the next item
   instantly. A response row is inserted only when an item is actually served, so §17's reason for rejecting prefetch
   (unanswered rows) does not apply.
4. Recompute E11 and §7 from de6fd05b-only cycle times (Q1) and re-run TASK-1087 timing with them.

**Evidence.** Q1 (§4). `review_learner/learner_view.py` → `learner_view_out.txt` ("min (wall clock)" column).

### L5 — major — Beginners face about 50 items, most of them "I don't know"

**Section.** Prose 6, "Beginners usually finish early" (draft:94-96); tech §6.1 warm-up "bands in random order"
(draft:484); §15 entry points and onboarding (draft:789-792); PQ7.

**Problem.** ESTIMATE, D3S, 4,000 learners:
- English-L1 zh beginners answer **23%** of meaning items right, guesses included. That is **about 38 of 49 meaning
  items not right**.
- Only **56%** of them stop before the cap, and those stop at about 51 items on average. ja English-L1: 52% stop
  early, mean 51 items.
- Cognate-L1 beginners (ja-L1 learning zh, zh-L1 learning ja) **almost never stop early (1%)**.

So "Beginners usually finish early" is not true. Two tweaks do not help:
- Letting the precision exit fire from 20 items changes the mean by about one item (50.9 vs 51.2), because the
  absolute ±12% rule rarely fires early.
- A one-sided "floor exit" saves only 2–5 items, and its bound holds for just 72–88% of learners.

Two more things make it worse:
- With the warm-up in random band order, a beginner's **first** word can be a Zipf < 3 word.
- PQ7 offers the placement during onboarding, so for many new users this is their **first experience of the
  product**.

**Correction.**
1. Onboarding asks first: "Have you studied {language} before?" If the answer is "No" or "Only a few words", skip the
   placement, record "just starting" with no estimate, and offer the placement after a few practice sessions.
2. Run the warm-up's first pass from the commonest band to the rarest (7 → 1) and randomise only the second pass.
   This does not affect the estimator: draws within a band stay uniform and the bands' tallies are unchanged.
3. Delete "Beginners usually finish early" and state the real length.
4. With L3 fixed, End now gives beginners an honest early exit. Make it visible after the warm-up as "Stop here and
   see your result".

**Evidence.** `review_learner/learner_view.py`, `early_exit.py`, `floor_exit.py` and their `_out.txt` files.
Product precedent: start easy [PROD D1]. Information argument for erring easy [LIT B3-9].

### L6 — major — "Meaning only" words are pushed out of practice, and the drill cannot show their pinyin

**Section.** Tech §10 (draft:577-600), ADR-059 (draft:1078-1088), PQ20 (draft:1718), prose 8 (draft:109-111).

**Problem.** The feature exists to find words a learner understands but cannot read (owner decision 3), yet nothing
routes those words to practice:
- **ADR-059 writes the meaning answer as BKT "correct"**, while readings are never written (draft:596-598). One right
  meaning answer lifts `p_known` above 0.40 for every word with Zipf ≥ 3 (ESTIMATE from the live constants [AUD
  §1.6, A.2]: prior 0.15 → 0.43; 0.35 → 0.69; 0.65 → 0.88).
- **Queue A2 admits only wrong or skipped calibration answers** (`services/practice/new_word_admission.py:631-655`, rule at `:652`)
  and vetoes `known`/`probably_known` (`:666-673`).
- **Queue A1 needs ≥ 2 pieces of evidence or `p_known ≤ 0.40`** (`services/practice/constants.py:37-38`;
  `new_word_admission.py:926-933`).
- So a meaning-right, reading-missed word is admitted by neither queue, and its raised `p_known` defers it. PQ20 sends
  these words to a **Pro-only manual list**.

The drills already exist: `hanzi_to_pinyin`, `pinyin_to_hanzi`, `tone_id_word` (zh) and `kanji_to_reading`,
`reading_to_kanji` (ja) (`services/vocabulary_ladder/config.py:505-509`). 87% of zh and 81% of ja pool words have a
reading exercise on some sense, and 93%/92% have ≥ 3 active exercises (MEASURED, Q6). But the hand-off is broken in
three places for the missed words too:
- **Admission uses the calibration `anchor_sense_id`.** For zh/en and ja/en that is the English-gloss row, which has
  **0 active exercises for all 3,623 zh and 3,175 ja pool words** (MEASURED, Q6).
- **The supply gate counts exercises on that exact sense id** (`new_word_admission.py:762-811`, threshold at `:809`), so the words get in
  only through the intro-drill bypass (`new_word_admission.py:500-504`; `NEW_WORD_DRILL_ENABLED` defaults to True,
  `services/intro_drill.py:31`).
- **The intro drill shows a zh reading only if it carries a numbered `(…)` part** (`services/intro_drill.py:248-249`).
  `dim_vocabulary.reading` is empty for all 3,682 zh pool words (MEASURED, Q7), gloss rows carry no reading [AUD
  §2.3], and 82% of zh native readings have lost the numbered part [AUD §1.3]. So for nearly every placement-admitted
  zh word the intro drill drops its pinyin formats (INFERENCE from the code path; not executed end to end).

**Correction.**
1. For reading-ready zh/ja words, write the evidence from the **pair** outcome, consistent with ADR-058:
   - meaning ✓ reading ✓ → BKT correct (placement counters);
   - meaning ✓ reading ✗/skip → **no BKT "correct"**. Record `placement_meaning_only` and admit the word to a
     "reading gap" queue (A2r) whose first exercises are the ladder's reading drills;
   - meaning ✗/skip → A2 as drafted.
2. Map `anchor_sense_id` to the **native rank-1 sense of the same `vocab_id`** before admission and before the supply
   gate.
3. Fix `intro_drill._reading` for diacritic-only pinyin. It has the same root cause as TASK-1074; add it there or as
   its own task, and make it a launch dependency for zh.
4. Change PQ20's default: "Practise these readings" on the result screen in v1 for every tier.
5. Acceptance: after a scripted zh placement with five meaning-only words, the next practice session contains
   `hanzi_to_pinyin` or `tone_id_word` items for them.

**Evidence.** Code lines above; Q6, Q7 (§4); [AUD §1.3, §1.6, §2.3].

### L7 — major — The copy promises a practice hand-off that may be off at launch

**Section.** The Part D note under the master list (draft:1689-1691), TASK-1081 status (draft:1350), prose 8
(draft:109-111), §8 next steps "Start today's session" (draft:549).

**Problem.** The draft allows launch "with the evidence hook disabled (no BKT write, no new-word queue intake)". The
learner-facing prose and result screen still say "the learner's daily practice uses the answers: missed words become
candidates to learn". That would be untrue, and "Start today's session" would show none of the words just missed.

**Correction.** Make TASK-1081 (with L6's changes) a hard dependency of TASK-1088. If launch must happen without it:
- remove the practice claim from the copy;
- relabel the next step "Start today's session (your placement answers will feed practice soon)";
- add an i18n parity test that the copy follows the flag.

**Evidence.** Draft lines cited above.

### L8 — major — Japanese words with Chinese definitions keep their headword: about 11% answerable by matching characters

**Section.** Tech §2 rule 5 (draft:273-274), E9 (draft:209), TASK-1077 acceptance criterion (draft:1243), TASK-1091.

**Problem.** Rule 5 strips "the text up to the first `；` or `;`". For zh/ja (Chinese word, Japanese definition) that
works: after the strip, **1** of 3,623 rank-1 keys still contains the prompt (MEASURED, Q4). ja/zh keys (Japanese
word, Chinese definition, used by Chinese-L1 learners of Japanese, an owner target group) mostly use a different
separator: "行李 —— 出行时用来装衣物和物品…", "重点 —— 事物中特别应该重视的部分".

MEASURED (Q4, Q5):
- **2,478 of 3,175** ja/zh keys start with `headword ——`, and in **453** the headword is the Japanese lemma itself.
- After the draft's strip, **470** keys still contain the lemma, and in **343 (10.8%)** none of the three served
  foils contains it, so the item is answerable by string matching.
- TASK-1077's criterion ("no `headword；` prefix") would pass while this remains.
- The audit's figure (ja/zh: 700 prefixed) used a `；` pattern and missed this form [AUD §2.4, A.7].

**Correction.**
1. Rule 5: strip a leading segment of 1–12 characters ended by `；`, `;`, `——` or `—`, with surrounding spaces, from
   all four options.
2. Replace TASK-1077's and TASK-1091's criterion with a measured one: "share of rank-1 anchors whose key contains
   the prompt lemma while no served foil does, after stripping, ≤ 1% for zh/ja and for ja/zh", using Q4.
3. Exclude any residual anchors from the placement for those pairs.

**Evidence.** Q4, Q5 (§4).

### L9 — major — Reading items rarely test the errors target learners make, and some can be solved without knowing the reading

**Section.**
- Tech §2 rules 3, 4 and 6 (draft:266-280).
- §8 item card "Choose the reading (with tones)" (draft:534) and §16 `.choose_reading_zh` (draft:798).
- Prose 3 and Constraints "Tones are part of the reading" (draft:84-87, 129-130).
- PQ3 and PQ19.

**Problem.** "Meaning and reading" is the headline claim, so the reading item has to be hard in the right way:
- **zh tones.** A tone-only foil exists for **10.9%** of zh anchors [AUD §2.4]. With about 19 reading items per test,
  about 2 offer one. On the other ~89% the learner can pick the right pinyin from the syllables alone.
  - Tones are where even advanced learners fail [LIT A8-50], and they are my own weakest point at HSK 4.
  - The prompt "(with tones)" and the result line "{tone_only} only the tone" (typically 0–1 per test) imply tone was
    tested throughout.
- **ja special morae.** Chinese-L1 learners' typical reading errors are vowel length, っ, ん and voicing [LIT A7-47].
  Only **298 of 17,592** cached ja foils (1.7%) are such variants of the key, even with a generous detector. They sit
  on 12% of anchors and appear in about **4%** of served items (MEASURED, Q3). The foils are other words' readings
  (船 ふね: ふく | やね | ふた | つね [AUD §2.3]).
- **ja okurigana tell.**
  - 488 of 2,243 ja reading anchors are written in kanji+kana. On average **55%** of their cached foils contradict the
    kana already visible in the word.
  - **199 (41%)** always serve at least one foil that can be eliminated that way.
  - **91 (19%)** can be answered by matching okurigana alone: 考え かんがえ against かんがい | かんけい | かんたん…;
    教え おしえ against じしん | たしか | おおく… (MEASURED, Q2).
- **The effect.** The m+r estimate is biased up for exactly the cognate learners decision 3 targets: +2.4..+3.8% of
  the pool with partial reading knowledge [SIM §4 `partial`]. Some "meaning and reading ✓" credits are recognition by
  elimination.

**Correction.**
1. New rule 3b: a ja reading foil must match the lemma's visible-kana pattern (`'^' || regexp_replace(lemma,
   '[^ぁ-ゟー]+', '.+', 'g') || '$'`). Anchors with fewer than 3 consistent cached foils are not reading-ready until the
   cache is refilled with okurigana-consistent candidates. Count this in TASK-1075's readiness gate.
2. A ja analogue of rule 4: include the cached special-mora or voicing variant when one exists. That goes from about
   4% to 12% of items at no cost.
3. Copy:
   - zh prompt "Choose the pinyin" without "(with tones)";
   - show "pinyin right, tone not yet" only when at least 5 tone-only items were served in the pooled window;
   - the method note says tones were checked on only some words.
4. Put PQ3 to the owner **before launch**, not after V6, because V6 cannot measure what the items do not test.

   The learner argument for PQ3: a wrong tone on the right syllables, or a dropped long vowel, is the error a
   learner actually makes with this real word. It is not a made-up word. JLPT 漢字読み items use exactly such
   near-miss readings as distractors (INFERENCE from my knowledge of the exam, not verified this session; the item
   type itself is [LIT A7-42]).

**Evidence.** Q2, Q3 (§4); [AUD §2.3, §2.4]; [LIT A7-47, A8-50, A8-51]; [SIM §4].

### L10 — major — A retake shows progress at roughly half size

**Section.** Tech §9 "Growth" (draft:574-575), §12 pooling (draft:619-626), §5.1 A_m/A_p, PQ8.

**Problem.** The result screen shows the pooled range: the latest answer per lemma over 180 days. Retakes are
disjoint, so three months later the old placement's words still count at full weight. ESTIMATE (arithmetic, equal
answer counts and nothing else in the window): if my true share rose by Δ, the headline moves by about Δ/2.

Retaking is how a learner checks progress [PROD lesson 7], and attrition argues for re-placement [LIT B6-23]. The
growth comparison of consecutive placements (ADR-053) is in the report, not on the retake result.

**Correction.** On a retake, the result screen leads with **this placement's own range** next to the previous
placement's, and the verdict of ADR-053's "clearly changed" rule ("clearly up" / "not clearly different"). The pooled
range follows as "Combined with your earlier answers (narrower)". The rule that the placement and My vocabulary
agree still holds for the pooled line.

**Evidence.** Draft lines cited above.

### L11 — minor — Probes are unscored and make the reveal misleading

**Section.** Tech §3 (draft:317-327), PQ4.

**Problem.** The draft says a reading item's appearance "is harmless … and probes make it uninformative". About 19
reading items follow right meanings and at most 3 follow wrong ones, so a reading item means "your meaning was right"
about 86% of the time (19/22). Learners will learn that within a few words (INFERENCE).

On a probe the learner believes the meaning was right, then the reveal says meaning ✗. If they answer the reading
correctly, that answer counts for nothing on their result. Probes cost up to 3 items (about 20 s at 7.5 s each).

**Correction.** Either label probes visibly ("Extra: reading only, not scored") or drop them from v1 and collect V4
data later through an opt-in reading check. Delete "probes make it uninformative" from §3.

**Evidence.** Draft lines cited above. Cycle time from Q1.

### L12 — minor — The guessing instruction is not quite true and suppresses partial knowledge

**Section.** Prose 1 (draft:79-81), tech §5.2 (draft:410-413), §8 intro (draft:533).

**Problem.** "A guess does not change the result on average" holds only for blind guesses. Guesses are more often
informed than uninformed, and the bilingual + IDK format (ours) had the weakest validity [LIT A2-15]. Informed
guessing biases m+r up by +2.4..+3.8% for cognate learners [SIM §4]. Meanwhile "Choose I don't know rather than
guess" makes cautious learners discard partial knowledge [LIT A2-13].

**Correction.** Intro copy: "If you have no idea, choose I don't know. If you think you know it, answer. A blind
guess only makes your result less precise." Drop "does not change the result on average".

**Evidence.** [LIT A2-13, A2-15], [SIM §4 `partial`].

### L13 — minor — The goal path does not change after a placement

**Section.** Tech §8 goal-path paragraph (draft:553-556), §9 evidence state (draft:568-571).

**Problem.** The goal-path level bars are built from measured buckets: rated known, seen, new to you, not in app.
That is visible in the demo copy in `wiki/demos/knowledge-report-goal-path.html`, e.g. the legend "Rated known /
Seen / New to you" and "{n} known · {n} seen · {n} not yet seen · {n} not in app". ADR-059 says placement answers
never make a word rated known, and the placement's per-word state appears only in the Pro list.

So after a six-minute placement the bars look the same. The only placement footprint on the goal card is the level
line, which L1 removes. The demo's hero copy also still says "After about 70 answers you get a range".

**Correction.**
1. Add a bar segment "answered in a placement, not yet checked", following Hack Chinese's "assumed known, not yet
   checked" segment [PROD H5]. Show it to every tier, alongside the per-word groups of L2.
2. It will be small (about 41 words per placement), but it is real and visible.
3. Update the hero copy for the placement path.

**Evidence.** Demo copy strings (extracted from the page's script); draft lines cited above.

---

## 3. What must be in v1, and what can wait

| v1 (must) | why |
|---|---|
| Characters-only meaning item, conditional reading, one combined reveal, design-based scoring (as drafted) | the trustworthy core |
| Rule 5 with `——`; rule 3b okurigana-consistent foils; ja special-mora foil preference; same-count foils (as drafted) | L8, L9: no free credit for cognate learners |
| A result for End now and abandoned sessions after the warm-up and ≥ 20 items; 24 h resume | L3 |
| Honest duration copy or a 5-minute time cap; instant next item (pre-built branches) | L4 |
| Onboarding "studied before?" gate; easy-first warm-up; no "beginners finish early" claim | L5 |
| Result screen led by this test's word groups with actions; range second; "Fewer than" phrased for beginners | L2 |
| Pair-based evidence write, native-sense admission, a reading-gap queue, the intro-drill pinyin fix, "Practise these readings" for all tiers; TASK-1081 a launch dependency | L6, L7 |
| A retake result showing this test vs the previous one (ADR-053 rule) | L10 |
| Honest guessing and tone copy | L9, L12 |

| Later | condition |
|---|---|
| Any exam-level output (threshold line or per-level shares) | per-true-level gate in TASK-1087 (L1) and V5/S8 data; owner PQ |
| Generated tone and special-mora foils (TASK-1092) | owner PQ3, which I would ask **before** launch (L9) |
| Probes (V4) | labelled, or opt-in (L11) |
| Tone-only count on the result | ≥ 5 tone-only items in the pooled window (L9) |
| Placement segment in the goal-path bars | can ship with v1 if cheap (L13) |
| IRT v2, level strata | as drafted |

---

## 4. Evidence: scripts, outputs and queries

All scripts were run with `python3 -I` and live in `placement/review_learner/`. Simulation inputs are the research
stage's outputs, read only.

| script | input | output | what it shows |
|---|---|---|---|
| `learner_view.py` | `sim/out/raw_main.json` (4,000 learners) | `learner_view_out.txt` | D3S by ability group: meaning and reading items, share of meaning items right (zh), stop point, minutes (sim latency and measured cycle), level exact / ±1 |
| `level_by_true.py` | same | `level_by_true_out.txt` | D3S m+r placement by true level (L1 table) |
| `place_designs.py` | `raw_main.json` + `raw_main_rho.json` | `place_designs_out.txt` | D0, D1S, D3S, D3L by true level (the D3 row is double-counted across the two files; not cited) |
| `simcopy/sim.py` (copy of `sim/sim.py`, patched: per-band counts in snapshots; design `D3Sf` = floor of 5 items in bands 4–7) | scratchpad exports | `simout/raw_floor.json` (1,000 per population, D3S + D3Sf), `simout/raw_gamma0.json` (D3S, `gamma_max=0`) | runs of 21–30 s |
| `compare_floor.py` | `raw_floor.json` | `compare_floor_out.txt` | items per band; placement by true level, D3S vs D3Sf; count MAE and coverage |
| `place_by_len.py` | `raw_floor.json`, `raw_gamma0.json` | `place_by_len_out.txt`, `place_gamma0_out.txt` | placement at 40/60/90 items; with no exam-level effect |
| `early_exit.py`, `floor_exit.py` | `raw_floor.json` | `early_exit_out.txt`, `floor_exit_out.txt` | earliest stop 20 vs 40; one-sided floor exit |
| `short_cover.py` | `raw_floor.json` | `short_cover_out.txt` | coverage and width at 20–40 items |
| `labels.py` | `raw_floor.json` | `labels_out.txt` | ADR-051 rule-4 label of the headline by true level |

Read-only SQL on project kpfqrjtfxmujzolwsvdq, 2026-11-18. Users are identified only by the first 8 characters of
their id.

**Q1 — de6fd05b cycle time and latency.** Output: definition, all: n 178, latency mean (capped 30 s) 4,722 ms, gap
mean **6.57 s** (median 5.03, n 170). Correct 6.70 s, skip 6.40 s, wrong 6.68 s. Pronunciation, all: n 99, latency
5,018 ms, gap mean **7.50 s** (median 5.39). Correct 5.68 s, skip 10.02 s.
```sql
WITH r AS (SELECT s.mode, r.session_id, r.answered_at, r.latency_ms, r.is_correct, (r.chosen_sense_id IS NULL) AS skipped,
                  lag(r.answered_at) OVER (PARTITION BY r.session_id ORDER BY r.answered_at) AS prev_at
           FROM calibration_responses r JOIN calibration_sessions s ON s.id = r.session_id
           WHERE left(r.user_id::text, 8) = 'de6fd05b' AND r.answered_at IS NOT NULL AND r.is_correct IS NOT NULL)
SELECT mode, CASE WHEN is_correct THEN 'correct' WHEN skipped THEN 'skip' ELSE 'wrong' END AS outcome, count(*) AS n,
  round(avg(least(latency_ms, 30000))) AS latency_mean_cap30s,
  count(*) FILTER (WHERE prev_at IS NOT NULL AND answered_at - prev_at <= interval '60 seconds') AS n_gap,
  round(avg(extract(epoch FROM answered_at - prev_at)) FILTER (WHERE prev_at IS NOT NULL AND answered_at - prev_at <= interval '60 seconds')::numeric, 2) AS gap_mean_s,
  round((percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM answered_at - prev_at)) FILTER (WHERE prev_at IS NOT NULL AND answered_at - prev_at <= interval '60 seconds'))::numeric, 2) AS gap_median_s
FROM r GROUP BY ROLLUP (mode, 2) ORDER BY 1, 2;
```

**Q2 — ja okurigana tell** (rank-1, unblocked reading anchors). Output: 2,243 reading lemmas; 488 written in
kanji+kana; 486 with ≥ 3 options; 199 with fewer than 3 kana-consistent foils; 91 with every foil eliminable; mean
share of foils eliminable 0.550. Examples (from the same query without the rank and blocklist filters, which give the
same counts): 考え かんがえ (かんがい | かんけい | かんたん | かんぜん | おんがく | かんれん | かんせい | かんかく), 教え おしえ
(じしん | たしか | おおく | おもに | おわり | しえん | いしき | おおい). The 88 multi-token lemmas such as "言う ます た" that the
unfiltered query also showed are **all blocklisted** (88 of 88), so they are not served.
```sql
WITH sp AS (SELECT p.vocab_id, p.lemma, s.sense_rank, EXISTS (SELECT 1 FROM calibration_anchor_blocklist b WHERE b.sense_id = p.sense_id) AS blocked
            FROM calibration_anchor_pool p JOIN dim_word_senses s ON s.id = p.sense_id
            WHERE p.word_language_id = 3 AND p.definition_language_id = 3 AND p.has_pronunciation AND p.lemma ~ '\s'),
a AS (SELECT p.vocab_id, p.sense_id, p.lemma, p.zipf_band, calibration_display_pronunciation(s.pronunciation, 3::smallint) AS key_disp,
             '^' || regexp_replace(p.lemma, '[^ぁ-ゟー]+', '.+', 'g') || '$' AS pat
      FROM calibration_anchor_pool p JOIN dim_word_senses s ON s.id = p.sense_id
      WHERE p.word_language_id = 3 AND p.definition_language_id = 3 AND p.has_pronunciation AND s.sense_rank = 1
        AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist b WHERE b.sense_id = p.sense_id)),
m AS (SELECT * FROM a WHERE lemma ~ '[ぁ-ゟ]' AND lemma ~ '[^ぁ-ゟー]'),
o AS (SELECT m.vocab_id, m.zipf_band, count(x.option_text) AS n_opt, count(x.option_text) FILTER (WHERE x.option_text !~ m.pat) AS n_elim
      FROM m LEFT JOIN LATERAL calibration_cached_options('pronunciation', m.sense_id) x ON true GROUP BY 1, 2)
SELECT (SELECT count(*) FROM sp) multi_token_rows, (SELECT count(*) FILTER (WHERE blocked) FROM sp) multi_token_blocked,
       (SELECT count(DISTINCT vocab_id) FROM a) ja_reading_lemmas_rank1_unblocked, count(*) mixed,
       count(*) FILTER (WHERE n_opt >= 3) mixed_ready, count(*) FILTER (WHERE n_opt >= 3 AND n_opt - n_elim < 3) lt3_consistent,
       count(*) FILTER (WHERE n_opt >= 3 AND n_elim = n_opt) all_eliminable,
       round(avg(n_elim::numeric / nullif(n_opt,0)) FILTER (WHERE n_opt >= 3), 3) mean_share_elim
FROM o;
```

**Q3 — ja special-mora and voicing foils** (generous detector: drop dakuten and handakuten, っ, ん, ー, う and い from
both strings and compare). Output: 2,230 anchors with a cache; 267 (12.0%) have at least one such foil; 298 of 17,592
cached foils; approximate chance that one of the 3 served is such a foil: 0.043.
```sql
WITH a AS (SELECT p.sense_id, calibration_display_pronunciation(s.pronunciation, 3::smallint) AS k
           FROM calibration_anchor_pool p JOIN dim_word_senses s ON s.id = p.sense_id
           WHERE p.word_language_id = 3 AND p.definition_language_id = 3 AND p.has_pronunciation AND s.sense_rank = 1
             AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist b WHERE b.sense_id = p.sense_id)),
o AS (SELECT a.sense_id, a.k, x.option_text AS f,
             regexp_replace(normalize(a.k, NFD), '[゙゚っんーうい]', '', 'g') AS nk,
             regexp_replace(normalize(x.option_text, NFD), '[゙゚っんーうい]', '', 'g') AS nf
      FROM a CROSS JOIN LATERAL calibration_cached_options('pronunciation', a.sense_id) x),
per AS (SELECT sense_id, count(*) AS n_opt, count(*) FILTER (WHERE nk = nf AND k <> f) AS n_mora FROM o GROUP BY 1)
SELECT count(*), count(*) FILTER (WHERE n_mora >= 1), round(100.0 * count(*) FILTER (WHERE n_mora >= 1) / count(*), 1),
       sum(n_mora), sum(n_opt), round(avg(1 - (1 - n_mora::numeric / nullif(n_opt, 0))^3), 3) FROM per;
```

**Q4 — the prompt still in the key after the draft's rule 5.** Output: zh/ja 3,623 rank-1 anchors, 1 residual (可能);
**ja/zh 3,175 anchors, 470 keys still contain the lemma, 343 answerable by string matching** (行李, 重点, PLA).
```sql
WITH a AS (SELECT p.word_language_id w, p.definition_language_id d, p.sense_id, p.lemma,
                  regexp_replace(p.definition, '^[^；;]{1,12}[；;]\s*', '') AS key_stripped
           FROM calibration_anchor_pool p JOIN dim_word_senses s ON s.id = p.sense_id
           WHERE s.sense_rank = 1 AND p.has_embedding AND (p.word_language_id, p.definition_language_id) IN ((1,3),(3,1))
             AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist b WHERE b.sense_id = p.sense_id)),
f AS (SELECT a.*, (SELECT count(*) FROM (SELECT x.option_text FROM calibration_cached_options('definition', a.sense_id) x LIMIT 3) y
                   WHERE strpos(regexp_replace(y.option_text, '^[^；;]{1,12}[；;]\s*', ''), a.lemma) > 0) AS foils_with_lemma
      FROM a WHERE length(a.lemma) >= 2 AND strpos(a.key_stripped, a.lemma) > 0)
SELECT a.w, a.d, count(*), (SELECT count(*) FROM f WHERE f.w = a.w AND f.d = a.d),
       (SELECT count(*) FROM f WHERE f.w = a.w AND f.d = a.d AND f.foils_with_lemma = 0)
FROM a GROUP BY a.w, a.d ORDER BY 1;
```

**Q5 — prefix forms per pair.** Output: ja/zh 3,175 anchors, `；` prefix 693, **`——` prefix 2,478**, `——` prefix equal to
the lemma 453. zh/ja: `；` prefix 3,623, `——` 0. zh/zh: `；` 117. ja/ja: none.
```sql
SELECT p.word_language_id w, p.definition_language_id d, count(*),
       count(*) FILTER (WHERE p.definition ~ '^[^；;—]{1,12}[；;]'),
       count(*) FILTER (WHERE p.definition ~ '^[^；;—]{1,12}\s*——'),
       count(*) FILTER (WHERE p.definition ~ '^[^；;—]{1,12}\s*——' AND split_part(p.definition, '——', 1)
                        ~ ('^\s*' || regexp_replace(p.lemma, '([.*+?^${}()|\[\]\\])', '\\\1', 'g') || '\s*$'))
FROM calibration_anchor_pool p JOIN dim_word_senses s ON s.id = p.sense_id
WHERE s.sense_rank = 1 AND p.has_embedding AND (p.word_language_id, p.definition_language_id) IN ((1,3),(3,1),(1,1),(3,3))
  AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist b WHERE b.sense_id = p.sense_id)
GROUP BY 1, 2 ORDER BY 1, 2;
```

**Q6 — exercise supply for placement words.** Output:

| | rank-1 meaning anchors (definition language en) | anchor (gloss) sense with ≥ 3 active exercises | any sense of the word with ≥ 3 | any sense with a reading drill |
|---|---|---|---|---|
| zh | 3,623 | **0** | 3,386 | 3,161 |
| ja | 3,175 | **0** | 2,935 | 2,582 |

```sql
WITH r1 AS (SELECT DISTINCT ON (p.word_language_id, p.vocab_id) p.word_language_id w, p.vocab_id, p.sense_id
            FROM calibration_anchor_pool p JOIN dim_word_senses s ON s.id = p.sense_id
            WHERE s.sense_rank = 1 AND p.has_embedding AND p.definition_language_id = 2 AND p.word_language_id IN (1, 3)
              AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist b WHERE b.sense_id = p.sense_id)
            ORDER BY p.word_language_id, p.vocab_id),
ex AS (SELECT e.word_sense_id, count(*) AS n_active,
              count(*) FILTER (WHERE e.exercise_type IN ('hanzi_to_pinyin','pinyin_to_hanzi','tone_id_word','kanji_to_reading','reading_to_kanji')) AS n_reading
       FROM exercises e WHERE e.is_active GROUP BY 1),
vx AS (SELECT s.vocab_id, sum(ex.n_active) AS n_active, sum(ex.n_reading) AS n_reading
       FROM ex JOIN dim_word_senses s ON s.id = ex.word_sense_id GROUP BY 1)
SELECT r1.w, count(*), count(*) FILTER (WHERE coalesce(ex.n_active, 0) >= 3),
       count(*) FILTER (WHERE coalesce(vx.n_active, 0) >= 3), count(*) FILTER (WHERE coalesce(vx.n_reading, 0) >= 1)
FROM r1 LEFT JOIN ex ON ex.word_sense_id = r1.sense_id LEFT JOIN vx ON vx.vocab_id = r1.vocab_id GROUP BY 1 ORDER BY 1;
```

**Q7 — `dim_vocabulary.reading` for zh pool words.** Output: 3,682 words, **0** with a reading.
```sql
WITH v AS (SELECT DISTINCT p.vocab_id FROM calibration_anchor_pool p WHERE p.word_language_id = 1 AND p.definition_language_id = 2 AND p.has_embedding)
SELECT count(*), count(*) FILTER (WHERE d.reading IS NOT NULL AND btrim(d.reading) <> ''),
       count(*) FILTER (WHERE d.reading ~ '\(.*[1-5].*\)\s*$') FROM v JOIN dim_vocabulary d ON d.id = v.vocab_id;
```

**Q8 — same-lemma (homograph) reading foils.** Output: 0 for zh (3,566 anchors) and 0 for ja (2,230). This is **not
a finding**; I checked it because a valid alternative reading offered as a "wrong" option would be a serious learner
complaint. (Query: join each cached pronunciation option's `vocab_id` to `dim_vocabulary.lemma` and compare with the
anchor lemma.)

---

## 5. Not verified, and limits

- **The simulation's learner model is an assumption** [SIM §8]. The L1 table holds for that model. The `gamma_max=0`
  run shows the problem survives the main contested assumption (S8), but not every assumption.
- **The shown level range was never simulated**, by the research stage or by me. Only point placement was.
- **Cycle times come from one real learner, the developer**, 277 answers in Readings and Meanings mode sessions, not
  paired items. The paired design's combined reveal may save time; pre-fetching wait is not included.
- **The intro-drill path for placement-admitted words (L6) was traced in code, not executed.** I did not trace how
  `status` (`known`/`probably_known`) is set from `p_known`.
- **The JLPT distractor style claim (L9)** is my own knowledge of the exam and was not verified this session.
- **The okurigana detector (Q2)** treats every non-hiragana run as "any reading". The special-mora detector (Q3) is
  deliberately generous, so its 4% is an upper bound.
- **No literature or product page was opened.** Literature and product claims are as the research reports state them.
