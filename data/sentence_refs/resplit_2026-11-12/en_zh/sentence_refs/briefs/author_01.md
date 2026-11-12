# Author brief 01 — en -> zh, arm `sentencewise`

Read `data/sentence_refs/resplit_2026-11-12/en_zh/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/resplit_2026-11-12/en_zh/sentence_refs/docs/<test_id>.zh.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/resplit_2026-11-12/en_zh --tests 3ddb9c3a-494b-45cb-8a74-610e95be311a`
and fix until every test is `ok`.

## 3ddb9c3a-494b-45cb-8a74-610e95be311a — Good App Training Data

Passage (for context, do not translate as a block unless the arm says so):

A company makes a helpful app. It helps people learn new things. The app uses big lists of words. These lists help the app know what to teach. People give the app words to learn. This is "training data." The app must be good. It must not cheat. The company must tell people about the words. This is "disclosure." The app must show how it learns. This is "transparency." The company must be good and fair. They want people to like the app.

Sentences:

- idx 0: A company makes a helpful app.
- idx 1: It helps people learn new things.
- idx 2: The app uses big lists of words.
- idx 3: These lists help the app know what to teach.
- idx 4: People give the app words to learn.
- idx 5: This is "training data."
- idx 6: The app must be good.
- idx 7: It must not cheat.
- idx 8: The company must tell people about the words.
- idx 9: This is "disclosure."
- idx 10: The app must show how it learns.
- idx 11: This is "transparency."
- idx 12: The company must be good and fair.
- idx 13: They want people to like the app.
