# Recheck pack 01 — BLIND HALF

You are the second reviewer of references flagged for this reason: an older automatic check compared digit strings, so the author wrote numbers and dates unnaturally (e.g. 1020000 instead of 1,020,000 or 1.02 million; a decade spelled out with its century). Numbers may now be written the way English writes them, as digits or words.
Rewrite the reference when the reason holds and a more natural, equally faithful
rendering exists; otherwise pass it with a note. Follow `.claude/skills/sentence-reference-review/SKILL.md`
for what to check (meaning, numbers and names, sentence identity, register,
leakage, tightness). The neighbours are context only; judge the TARGET.

Order (hard rule): write `data/sentence_refs/full_2026-11-17/recheck-numbers-2026-11-17/sentence_refs/back/01.json` with your blind
back-translation of every TARGET into the studied language BEFORE opening
`recheck_01.gold.md`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "back": "<your L2 version>"}]}

Then open the gold file and write `data/sentence_refs/full_2026-11-17/recheck-numbers-2026-11-17/sentence_refs/verdicts/01.json`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "verdict": "pass|rewritten|fail",
      "entailment_ok": true, "l1": "<final reference: unchanged for pass, your rewrite for rewritten>",
      "gold_seen_early": false, "notes": "<one line: why low, what you changed>"}]}

`fail` only for a gold that is itself broken (fragment, leaked preamble, mixed script).
A rewrite stays one sentence, keeps every number and name, adds nothing, and has
no L2 script, notes or parentheses. Never change the gold. Every key gets a verdict.


The gold half is `data/sentence_refs/full_2026-11-17/recheck-numbers-2026-11-17/sentence_refs/packs/recheck_01.gold.md`. Do not open it yet.


## 3574dd04-2-en  (English reference -> back-translate into Chinese)

- context before: Its design is like a circle of green arrows, indicating that waste can be reused.
- **TARGET:** The history of this symbol can be traced back to the 1970s of the 20th century.
- context after: At that time, people began to care about the problem of environmental pollution.

## 61f4125b-1-en  (English reference -> back-translate into Chinese)

- context before: In business reports and news coverage, misleading charts are a common sight, and the most common technique among them is truncating the vertical axis.
- **TARGET:** Suppose a company announces its sales for two years: last year was 980000 yuan and this year is 1020000 yuan, an actual increase of only about 4%.
- context after: However, if the chart maker does not let the vertical axis start from zero but starts marking from 970000 yuan, the heights of the two bars will differ greatly, this year's bar will look about five times last year's, and a tiny fluctuation is thereby exaggerated into a startling leap.

## 61f4125b-2-en  (English reference -> back-translate into Chinese)

- context before: Suppose a company announces its sales for two years: last year was 980000 yuan and this year is 1020000 yuan, an actual increase of only about 4%.
- **TARGET:** However, if the chart maker does not let the vertical axis start from zero but starts marking from 970000 yuan, the heights of the two bars will differ greatly, this year's bar will look about five times last year's, and a tiny fluctuation is thereby exaggerated into a startling leap.
- context after: The root of the problem is that a bar chart relies on the length of the bars to convey quantity, and length should be proportional to value; once the vertical axis is truncated, the visual proportion and the true proportion are completely disconnected, and the reader's intuition is misled along with it.
