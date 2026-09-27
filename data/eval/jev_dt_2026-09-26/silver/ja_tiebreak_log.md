# JA Silver Tie-Break Log — 3-rater adjudication (7 disputed items)

Raters: **draft** (drafter), **review** (reviewer), **tiebreak** (blind third rater, this session —
labels frozen in `ja_tiebreak.json` before `ja_draft.json`/`ja_review.json` were opened).
Decision rule: 2-of-3 majority per field (error count+location, subtype, severity, naturalness,
range). No field lacked a majority on any of these 7 items, so **none were dropped**. Every kept
item differed from the draft in at least one field, so all 7 were rebuilt with
`scripts/dt_gold_seed_helper.py` (`build_item` + `derive_bands(offline=True)`) using the majority
labels and the draft's edit spans — spans/reproductions verify byte-identical to the draft's.

---

## ja_silver_13

| Field | draft | review | tiebreak | Majority |
|---|---|---|---|---|
| has error | yes (verb_conjugation, major) | no | no | **no error** (2/3) |
| naturalness | 4 | 4 | 4 | 4 |
| range | 4 | 4 | 4 | 4 |

**Outcome:** KEPT, rebuilt as `kind: clean`, 0 expected_errors. 学ぶ→学べる (dictionary vs.
potential form before 機会) judged an acceptable near-synonymous paraphrase by 2 of 3 raters.

## ja_silver_15

| Field | draft | review | tiebreak | Majority |
|---|---|---|---|---|
| subtype | topic_comment | topic_comment | particle_wa_ga | **topic_comment** (2/3) |
| severity | major | minor | major | **major** (2/3) |
| naturalness | 4 | 3 | 3 | **3** (2/3) |
| range | 4 | 4 | 4 | 4 |

**Outcome:** KEPT, rebuilt: topic_comment / major / naturalness 3 / range 4. Draft's naturalness
was outvoted.

## ja_silver_16

| Field | draft | review | tiebreak | Majority |
|---|---|---|---|---|
| subtype | topic_comment | topic_comment | particle_wa_ga | **topic_comment** (2/3) |
| severity | major | minor | major | **major** (2/3) |
| naturalness | 4 | 3 | 3 | **3** (2/3) |
| range | 4 | 4 | 4 | 4 |

**Outcome:** KEPT, rebuilt: topic_comment / major / naturalness 3 / range 4 (same pattern as
ja_silver_15 — is/wa dropped before the same predicate).

## ja_silver_24

| Field | draft | review | tiebreak | Majority |
|---|---|---|---|---|
| subtype | collocation | word_choice | word_choice | **word_choice** (2/3) |
| severity | minor | minor | minor | minor |
| naturalness | 3 | 4 | 4 | **4** (2/3) |
| range | 4 | 3 | 3 | **3** (2/3) |

**Outcome:** KEPT, rebuilt: word_choice / minor / naturalness 4 / range 3. Draft's subtype,
naturalness, and range were all outvoted (格別→高い read by 2/3 raters as a lexical
sophistication/range loss rather than a naturalness-breaking collocation).

## ja_silver_25

| Field | draft | review | tiebreak | Majority |
|---|---|---|---|---|
| subtype | collocation | collocation | collocation | collocation |
| severity | minor | minor | minor | minor |
| naturalness | 2 | 3 | 3 | **3** (2/3) |
| range | 4 | 4 | 4 | 4 |

**Outcome:** KEPT, rebuilt: collocation / minor / naturalness 3 / range 4. Draft's naturalness=2
was outvoted to 3 (力を養う vs. 力を育てる judged a single mild collocation slip, not a
"visibly non-native" band-2 error).

## ja_silver_27

| Field | draft | review | tiebreak | Majority |
|---|---|---|---|---|
| subtype | cohesion_connective | cohesion_connective | cohesion_connective | cohesion_connective |
| severity | major | major | major | major |
| naturalness | 2 | 3 | 3 | **3** (2/3) |
| range | 4 | 4 | 4 | 4 |

**Outcome:** KEPT, rebuilt: cohesion_connective / major / naturalness 3 / range 4. Draft's
naturalness=2 outvoted to 3 (しかし for そして introduces a false contrast — a real logical
defect, hence severity stays major — but 2/3 raters judged one isolated connective swap short of
a band-2 "visibly non-native" naturalness hit).

## ja_silver_29

| Field | draft | review | tiebreak | Majority |
|---|---|---|---|---|
| subtype | word_choice | word_choice | word_choice | word_choice |
| severity | minor | minor | minor | minor |
| naturalness | 4 | 4 | 4 | 4 |
| range | 2 | 3 | 3 | **3** (2/3) |

**Outcome:** KEPT, rebuilt: word_choice / minor / naturalness 4 / range 3. Draft's range=2
outvoted to 3 (理解する手助けになります→わかるようになります flattens structure/register but
2/3 raters judged it a single moderate simplification, not the "leans on a few structures and
generic vocabulary throughout" band-2 profile).

---

## Summary

- **Kept:** 7/7. **Dropped:** 0/7 (every field reached a 2-of-3 majority on all 7 items).
- **Pairwise exact-label agreement across draft/review/tiebreak on these 7 items** (field-by-field,
  counted item-by-item; severity is counted only over the 6 items where the compared pair of
  raters both posited an error):
  - has-error / subtype: draft-review 5/7, draft-tiebreak 3/7, review-tiebreak 5/7
  - severity: draft-review 4/6, draft-tiebreak 6/6, review-tiebreak 4/6
  - naturalness: draft-review 2/7, draft-tiebreak 2/7, review-tiebreak 7/7
  - range: draft-review 5/7, draft-tiebreak 5/7, review-tiebreak 7/7
  - Reviewer and tiebreak (produced fully independently of each other and of each other's
    reasoning) agree exactly on naturalness and range on all 7 items, and mostly agree on
    subtype/severity; the draft is the consistent outlier on naturalness (draft skews toward the
    band-2 extreme on ja_silver_25/27) and range (draft skews toward band-2 on ja_silver_29), and
    is alone in calling ja_silver_13 an error at all.
- Rebuilt items verified with `verify_item()` (span integrity, normalization survival, kind/error
  count sanity) — zero problems. All 7 rebuilt reproductions are byte-identical to the draft's.
- Output: `silver/ja_final3.json` = `ja_final.json` (25 items, untouched) + these 7 majority-labeled
  items (32 total).
