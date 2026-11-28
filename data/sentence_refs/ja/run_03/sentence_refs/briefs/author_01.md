# Author brief 01 — ja -> en, arm `sentencewise`

Read `data/sentence_refs/ja/run_03/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/ja/run_03/sentence_refs/docs/<test_id>.en.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/ja/run_03 --tests f1fb217e-5e2f-4173-8752-c6a5a30c47b4`
and fix until every test is `ok`.

## f1fb217e-5e2f-4173-8752-c6a5a30c47b4 — ねるまえのおはなし

Passage (for context, do not translate as a block unless the arm says so):

夜、ねる前に、おかあさんは子どもに物語を読み聞かせします。子どもは、すきな本をえらんで、ベッドの中で聞きます。やさしい声を聞くと、安心して、ねむくなります。

Sentences:

- idx 0: 夜、ねる前に、おかあさんは子どもに物語を読み聞かせします。
- idx 1: 子どもは、すきな本をえらんで、ベッドの中で聞きます。
- idx 2: やさしい声を聞くと、安心して、ねむくなります。
