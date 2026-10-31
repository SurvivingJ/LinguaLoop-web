---
name: sentence-reference-authoring
description: Author sentence-level native-language (L1) references for test transcripts — export a worklist of tests, brief author subagents (Sonnet) that write one aligned JSON document per test per L1 from files only, run the deterministic checks until clean, then hand off to sentence-reference-review in a fresh context. Use when asked to generate dual-translation references, back-fill test sentence translations, run the sentence-reference pilot, or prepare the Produce stage of test prestudy. No hosted model API is called; OpenRouter is for live grading only.
---

# Sentence-Reference Authoring

One JSON document per test per L1, written by an author subagent, reviewed by
a different subagent in a fresh context, then pushed through the unchanged
upload path. You orchestrate: you run the commands, spawn the authors, relay
check output, and hand off the review. You never write or review a document.

Runner: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py <cmd> …`
(logic in `services/dual_translation/sentence_refs.py`, tests in
`tests/test_sentence_refs.py`). **No step calls a hosted model API.** Every
model call is a Claude subagent. Decision record: ADR-037.

## Size first

Agree the slice with the user before exporting. **Default: 8 tests, one
language, one L1, one arm.** Each test is about one author turn; six tests per
brief. The pilot (TASK-907) is 30 tests per language, both arms, which is a
scope conversation, not a default.

## The chain

| # | step | who |
|---|---|---|
| 0 | `export --language ja --l1 en --limit 8 --arm aligned --out-dir data/sentence_refs/ja/run_NN` (needs `test_sentences` live; `--fixture FILE` for offline work) | you |
| 1 | `brief RUN [--width 6]` → `RUN/sentence_refs/briefs/author_NN.md` + `rules_authoring.md` | you |
| 2 | author the documents, one subagent per brief, **Sonnet** | **author subagents** |
| 3 | `check RUN`: fix loop until `0 failed` | you + authors |
| 4 | `review-pack RUN`, then hand off | **sentence-reference-review** (fresh subagent) |
| 5 | `tightness RUN`, `check RUN --source reviewed`, `assemble RUN` | you |
| 6 | `python scripts/upload_sentence_references.py RUN --dry-run`, then `--apply` (pilot arms: `--no-activate`) | you |

`status RUN` shows where every test stands.

## Step 2: spawning the authors

One subagent per brief file. They are independent, so launch them together in
the background, model Sonnet. The prompt is the brief's path and nothing about
other briefs:

> You are authoring native-language reference translations of test sentences
> for LinguaLoop. Work only from files; make no API calls.
>
> Read `RUN/sentence_refs/briefs/author_NN.md` and the rules file it names.
> For every test in the brief write `RUN/sentence_refs/docs/<test_id>.<l1>.json`
> in the document shape the rules give, following the arm the brief states.
> Put your model id in a top-level `"author_model"` field.
>
> Then run `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check RUN --tests <id1,id2,…>` (comma-separated, no spaces)
> and fix until every test is `ok`. Report the final check line.

If the subagent's Bash is denied, run `check` yourself and send the output back
to **the same subagent** with SendMessage; a fresh agent would re-derive the
passage.

## The two arms

- `sentencewise`: the author re-reads the whole passage, then translates one
  sentence per entry. Tends to be tighter; may read choppy as a passage.
- `aligned`: the author translates the passage as prose, then splits it into
  the aligned array and adjusts each entry to stand alone. Tends to read
  better; may drift from sentence boundaries.

The brief names the arm. The pilot compares them; after the pilot, use the
winner recorded in ADR-037.

## Rules the authors follow (summary; the runner writes the full file)

Faithful and tight over pretty: one entry per sentence, same count and order,
every number, name, negation, tense and politeness marker kept, nothing added,
no notes inside `l1`, no L2 script in `l1`, loanwords back to their source
form, digits stay digits, terminators match the sentence type. CJK → en keeps
sentence boundaries even where English would merge. en → zh/ja and zh ↔ ja
follow the gloss conventions in the `cross-language-glosses` skill.

## Deterministic checks (what `check` rejects)

`count_mismatch`, `idx_order`, `l2_changed`, `empty_l1`, `l2_script_leak:<chars>`,
`missing_number:<n>`, `preamble`, `length_ratio:<r>`, `duplicate_sentence`.
Warnings (go to the reviewer, do not block): `author_note_in_l1`.

## Hard rules

- You do not write documents. You do not review them.
- Never edit `l2`; never reorder `idx`.
- Reviewed documents are the only thing that reaches `assemble`.
- Pilot runs are uploaded with `--no-activate`; activation is TASK-908.
