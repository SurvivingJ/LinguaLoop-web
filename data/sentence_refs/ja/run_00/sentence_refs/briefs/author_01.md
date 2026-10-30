# Author brief 01 — ja -> en, arm `sentencewise`

Read `data/sentence_refs/ja/run_00/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/ja/run_00/sentence_refs/docs/<test_id>.en.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/ja/run_00 --tests 6eb4ff60-ebb8-40b1-aa80-f6a24a8312f0,9b8ceffb-a291-43f3-97df-302077de7c46`
and fix until every test is `ok`.

## 6eb4ff60-ebb8-40b1-aa80-f6a24a8312f0 — 手作りアクセサリーで収入を得る、オンラインビジネス

Passage (for context, do not translate as a block unless the arm says so):

趣味で手作りしたアクセサリーを収入につなげたいなら、オンラインビジネスの構築が有効です。まずはインターネットで販売を開始しましょう。成功の鍵は、商品の魅力を伝える写真の工夫と、ターゲット層に届けるマーケティングです。誰に何を求めているか分析し、適切な言葉で発信することで、小さくても確実なファンを獲得できます。

Sentences:

- idx 0: 趣味で手作りしたアクセサリーを収入につなげたいなら、オンラインビジネスの構築が有効です。
- idx 1: まずはインターネットで販売を開始しましょう。
- idx 2: 成功の鍵は、商品の魅力を伝える写真の工夫と、ターゲット層に届けるマーケティングです。
- idx 3: 誰に何を求めているか分析し、適切な言葉で発信することで、小さくても確実なファンを獲得できます。

## 9b8ceffb-a291-43f3-97df-302077de7c46 — はじめてのステージ

Passage (for context, do not translate as a block unless the arm says so):

十代の人が初めてステージに立ちます。マイクを持って詩を読みます。これはスポークンワードというパフォーマンスです。

Sentences:

- idx 0: 十代の人が初めてステージに立ちます。
- idx 1: マイクを持って詩を読みます。
- idx 2: これはスポークンワードというパフォーマンスです。
