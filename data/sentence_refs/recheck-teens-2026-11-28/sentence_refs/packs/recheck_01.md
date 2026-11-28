# Recheck pack 01 — BLIND HALF

You are the second reviewer of references flagged for this reason: 10代 (ages 10-19) was written as "in their/his 10s" or "a teenager in his 10s" because the number check used to reject "teens". It now accepts teens / teenage / teenager for 10代. Render 10代 the natural English way, and add no gender the Japanese does not state.
Rewrite the reference when the reason holds and a more natural, equally faithful
rendering exists; otherwise pass it with a note. Follow `.claude/skills/sentence-reference-review/SKILL.md`
for what to check (meaning, numbers and names, sentence identity, register,
leakage, tightness). The neighbours are context only; judge the TARGET.

Order (hard rule): write `data/sentence_refs/recheck-teens-2026-11-28/sentence_refs/back/01.json` with your blind
back-translation of every TARGET into the studied language BEFORE opening
`recheck_01.gold.md`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "back": "<your L2 version>"}]}

Then open the gold file and write `data/sentence_refs/recheck-teens-2026-11-28/sentence_refs/verdicts/01.json`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "verdict": "pass|rewritten|fail",
      "entailment_ok": true, "l1": "<final reference: unchanged for pass, your rewrite for rewritten>",
      "gold_seen_early": false, "notes": "<one line: why low, what you changed>"}]}

`fail` only for a gold that is itself broken (fragment, leaked preamble, mixed script).
A rewrite stays one sentence, keeps every number and name, adds nothing, and has
no L2 script, notes or parentheses. Never change the gold. Every key gets a verdict.


The gold half is `data/sentence_refs/recheck-teens-2026-11-28/sentence_refs/packs/recheck_01.gold.md`. Do not open it yet.


## 5d23154f-0-en  (English reference -> back-translate into Japanese)

- **TARGET:** The path he chose, a teenager in his 10s who had just graduated from high school, was to work at an organic farm in a rural area.
- context after: The first year was, contrary to the beautiful rural scenery, a succession of harsh manual labor covered in mud.

## d71cadf7-0-en  (English reference -> back-translate into Japanese)

- **TARGET:** Yesterday, Yuuki, who is in their 10s, read a poem in front of everyone for the first time.
- context after: It is a spoken word performance.

## e0400cd5-0-en  (English reference -> back-translate into Japanese)

- **TARGET:** A boy in his 10s performed a guitar solo in front of a large audience for the first time.
- context after: His hands trembled, but he took a deep breath and played slowly.
