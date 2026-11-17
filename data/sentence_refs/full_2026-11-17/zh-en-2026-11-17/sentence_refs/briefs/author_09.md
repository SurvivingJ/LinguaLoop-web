# Author brief 09 — zh -> en, arm `sentencewise`

Read `data/sentence_refs/full_2026-11-17/zh/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/full_2026-11-17/zh/sentence_refs/docs/<test_id>.en.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/full_2026-11-17/zh --tests 35742c67-b6e1-4dfa-889c-8ead2f2bf833`
and fix until every test is `ok`.

## 35742c67-b6e1-4dfa-889c-8ead2f2bf833 — 巨龙守护：中国长城的历史与宏伟

Passage (for context, do not translate as a block unless the arm says so):

中国长城是一个非常古老和巨大的建筑。古时候，人们修建长城是为了防御。长城在中国北方，它很长很长。修建长城用了很多人力和很多年的时间。长城就像一条巨龙，在山上蜿蜒。它帮助人们保护自己的国家，不让敌人进来。长城是中国的一个重要象征，很多人都去那里看。

Sentences:

- idx 0: 中国长城是一个非常古老和巨大的建筑。
- idx 1: 古时候，人们修建长城是为了防御。
- idx 2: 长城在中国北方，它很长很长。
- idx 3: 修建长城用了很多人力和很多年的时间。
- idx 4: 长城就像一条巨龙，在山上蜿蜒。
- idx 5: 它帮助人们保护自己的国家，不让敌人进来。
- idx 6: 长城是中国的一个重要象征，很多人都去那里看。
