# ja_silver disagreements (draft vs. blind review)

7 of 32 items dropped. All disagreements are band-level (naturalness/range) or an
error-existence call, not gross taxonomy mismatches — every dropped item's draft
error(s), where present, at least overlapped in span and matched or shared a
dimension with the reviewer's independent read.

---

## ja_silver_13 — error-existence disagreement

- **Draft:** 1 error — `verb_conjugation`, major, `学べる良い機会になります` → `学ぶ良い機会になります`.
- **Review:** 0 errors (clean). Judged 学ぶ→学べる (dictionary vs. potential form) as a
  natural, near-synonymous paraphrase before 機会, not a conjugation mistake.
- **Why dropped:** error count mismatch (1 vs. 0) — draft treats a verb-form choice as
  wrong; review treats it as acceptable variation.

## ja_silver_15 — severity + naturalness disagreement

- **Draft:** `topic_comment`, **major**, naturalness **4**.
- **Review:** `topic_comment`, **minor**, naturalness **3** (topic-marker は omission,
  scored against the gold-set precedent ja_seed_11, which is minor/naturalness 3).
- **Why dropped:** severity differs (major vs. minor) and naturalness differs (4 vs. 3).

## ja_silver_16 — severity + naturalness disagreement

- **Draft:** `topic_comment`, **major**, naturalness **4**.
- **Review:** `topic_comment`, **minor**, naturalness **3** (same は-omission pattern as
  ja_silver_15/gold ja_seed_11).
- **Why dropped:** severity and naturalness both differ, same reasoning as ja_silver_15.

## ja_silver_24 — subtype dimension + naturalness + range disagreement

- **Draft:** `collocation` (dimension naturalness), minor, naturalness **3**, range **4**.
- **Review:** `word_choice` (dimension fidelity), minor, naturalness **4**, range **3**.
- **Why dropped:** subtypes are neither identical nor same-dimension (naturalness vs.
  fidelity), and naturalness/range are swapped between the two labels — both agree
  something is off with 達成感は高い vs. 格別 but disagree on which axis absorbs it.

## ja_silver_25 — naturalness disagreement

- **Draft:** `collocation`, minor, naturalness **2**.
- **Review:** `collocation`, minor, naturalness **3**.
- **Why dropped:** subtype/severity match, but naturalness differs (2 vs. 3) — draft
  treats 力が育てられます as more jarring/non-native than the review does.

## ja_silver_27 — naturalness disagreement

- **Draft:** `cohesion_connective`, major, naturalness **2**.
- **Review:** `cohesion_connective`, major, naturalness **3**.
- **Why dropped:** subtype/severity match on the しかし misuse, but naturalness differs
  (2 vs. 3) — same disagreement pattern as ja_silver_25.

## ja_silver_29 — range disagreement

- **Draft:** `word_choice`, minor, range **2**.
- **Review:** `word_choice`, minor, range **3**.
- **Why dropped:** subtype/severity/naturalness match, but range differs (2 vs. 3) —
  draft judges the わかるようになります flattening more severe than the review does.
