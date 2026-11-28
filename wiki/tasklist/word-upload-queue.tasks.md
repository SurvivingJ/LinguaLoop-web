---
title: "Word-Upload Queue — Task Breakdown"
feature: word-upload-queue
prose_page: ../features/word-upload-queue.md
tech_page: ../features/word-upload-queue.tech.md
total_tasks: 2
done: 0
---

# Word-Upload Queue — Task Breakdown

---

## TASK-1276: Queue uploaded words for offline asset building

**Status:** [?] Done (repo) 2026-11-28, awaiting live apply of `migrations/word_upload_queue.sql`
**Feature:** word-upload-queue
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** none

**Description:**
Owner: "Ideally they get put into a queue db table and then I can run ai LLM over them to
build the assets etc." — keep the inline path as an option, build every asset, no credits.
Built per [[decisions/ADR-069-word-upload-queue]] and [[features/word-upload-queue.tech]].

**Acceptance Criteria:**
- [x] `word_upload_queue` table with RLS on, service role only (migration lint passes).
- [x] Submit queues words and answers 202 with no LLM call; inline path behind `WORD_LIST_INLINE_GENERATION=true`.
- [x] Lookup-only advance after submit and hourly; operator `export` writes scoped worklists and `plan.md`.
- [x] A word finishes only when all eight checklist keys are present; one watchlist row per learner; match sweep runs.
- [x] `/word-list` shows queued words.
- [ ] Migration applied live; post-checks in the file header pass.

**Files to Create / Modify:** see the tech page's dependencies.

**Verification:**
Apply `migrations/word_upload_queue.sql` (VERIFY BEFORE / AFTER in its header), deploy, submit
a fully built word and a new word on `/word-list`: the first reaches the watchlist within
seconds; `python scripts/word_upload_queue.py status` lists the second as building.

---

## TASK-1277: Japanese inflection and CJK compounds in the shared word resolver

**Status:** [ ] Not Started
**Feature:** word-upload-queue
**Type:** bug
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
`services/vocabulary/word_resolver._tokenize_single_word` turns 食べた into the lemma
`食べる た` and お茶 into `御 茶`, so the inline upload path (and any other caller) creates
junk `dim_vocabulary` rows for inflected Japanese input. The queue's resolver
(`queue._Tokenizer`) already strips trailing `助動詞` and falls back to the raw word for
split CJK words; move that logic into the shared resolver so both paths agree.

**Acceptance Criteria:**
- [ ] `_tokenize_single_word('食べた', 'ja')['lemma'] == '食べる'`; `走ります` → `走る`.
- [ ] A split CJK word without a single content token keeps the surface form as its lemma.
- [ ] `queue._Tokenizer` calls the shared function (no second copy); existing resolver tests pass.

**Files to Create / Modify:**
- `services/vocabulary/word_resolver.py` — the two rules.
- `services/word_list_import/queue.py` — drop the local copy.
- `tests/test_word_resolver.py` — cases above.

**Verification:** `pytest tests/test_word_resolver.py tests/test_word_upload_queue.py`.

---
