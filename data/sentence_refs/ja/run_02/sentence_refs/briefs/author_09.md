# Author brief 09 — ja -> en, arm `sentencewise`

Read `data/sentence_refs/ja/run_02/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/ja/run_02/sentence_refs/docs/<test_id>.en.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/ja/run_02 --tests 9d129d07-5ee9-4273-9d13-e992b621b955,835ec6fa-b813-4374-a35e-89abbc33720c,0a74180c-9cdc-4af3-ad90-7e9a28d4311c,40fbca90-fc4e-4846-aa2d-aed595d6cbec`
and fix until every test is `ok`.

## 9d129d07-5ee9-4273-9d13-e992b621b955 — ピーナッツバターとジャムのサンドイッチ

Passage (for context, do not translate as a block unless the arm says so):

きょうのひるごはんは、サンドイッチです。まず、パンにピーナッツバターをぬります。つぎに、ほかのパンにジャムをぬります。そして、二まいのパンをあわせます。さいごに、ぱんを半分にきります。とてもおいしいです。

Sentences:

- idx 0: きょうのひるごはんは、サンドイッチです。
- idx 1: まず、パンにピーナッツバターをぬります。
- idx 2: つぎに、ほかのパンにジャムをぬります。
- idx 3: そして、二まいのパンをあわせます。
- idx 4: さいごに、ぱんを半分にきります。
- idx 5: とてもおいしいです。

## 835ec6fa-b813-4374-a35e-89abbc33720c — はじめてのサワードウパン作り

Passage (for context, do not translate as a block unless the arm says so):

わたしは、はじめてサワードウのパンを作りました。イーストを使わないので、小麦粉と水を数日おいて、元気な種を作ります。台所でていねいにこねて、オーブンでやくと、いいにおいがしました。ベーキングはたのしいです。

Sentences:

- idx 0: わたしは、はじめてサワードウのパンを作りました。
- idx 1: イーストを使わないので、小麦粉と水を数日おいて、元気な種を作ります。
- idx 2: 台所でていねいにこねて、オーブンでやくと、いいにおいがしました。
- idx 3: ベーキングはたのしいです。

## 0a74180c-9cdc-4af3-ad90-7e9a28d4311c — サワードウパンのつくりかた

Passage (for context, do not translate as a block unless the arm says so):

サワードウのパンを作ります。まず、小麦粉と水でスターターを作ります。あたたかいところに置くと、あわが出て大きくなります。これを発酵といいます。次に、生地をオーブンでベーキングします。

Sentences:

- idx 0: サワードウのパンを作ります。
- idx 1: まず、小麦粉と水でスターターを作ります。
- idx 2: あたたかいところに置くと、あわが出て大きくなります。
- idx 3: これを発酵といいます。
- idx 4: 次に、生地をオーブンでベーキングします。

## 40fbca90-fc4e-4846-aa2d-aed595d6cbec — パンがふくらむ　はっこうのふしぎ

Passage (for context, do not translate as a block unless the arm says so):

主食のパンは、発酵という方法でつくります。発酵とは、小さな生きものが、あたたかい所でじかんをかけて粉を変えることです。すると、パンの栄養がふえて、風味もよくなります。

Sentences:

- idx 0: 主食のパンは、発酵という方法でつくります。
- idx 1: 発酵とは、小さな生きものが、あたたかい所でじかんをかけて粉を変えることです。
- idx 2: すると、パンの栄養がふえて、風味もよくなります。
