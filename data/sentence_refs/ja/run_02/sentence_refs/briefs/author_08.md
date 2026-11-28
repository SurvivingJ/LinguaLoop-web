# Author brief 08 — ja -> en, arm `sentencewise`

Read `data/sentence_refs/ja/run_02/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/ja/run_02/sentence_refs/docs/<test_id>.en.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/ja/run_02 --tests 84ad0d1e-100e-4447-bb4e-07b9aa1c1b85,36d2ad28-6b57-40ad-b687-76b0a27cfdc8,27f67de9-9c06-4ace-bfee-45ccff67fd67,6dc7b01b-3883-4c78-b85b-5ed32d8f9cc2,f202bfa7-dd27-48d3-bcd0-947ba3886e3c,f8093879-9e69-497e-9e1a-8d77dd3a381a,5c037be1-1dea-4807-9acc-48051be5c773,c73e7969-fea9-40e6-9de1-7fea90df842f,8cdd5ff6-e5f7-42b7-bc58-fd598078a5f3,d6dd04d3-9e7e-4435-866f-5cb3b691ea80,bfb1c906-03bd-4328-b7d7-98be909dee54,cf4bb36e-1661-4593-80a5-ba7276563647`
and fix until every test is `ok`.

## 84ad0d1e-100e-4447-bb4e-07b9aa1c1b85 — 公園でクレヨンのお絵かき

Passage (for context, do not translate as a block unless the arm says so):

きのう、わたしは公園でクレヨンを使って絵を描きました。あかやきいろなど、たくさんの色をえらびました。大きな花をかくと、ともだちが「きれいだね」と言ってくれました。うれしかったです。

Sentences:

- idx 0: きのう、わたしは公園でクレヨンを使って絵を描きました。
- idx 1: あかやきいろなど、たくさんの色をえらびました。
- idx 2: 大きな花をかくと、ともだちが「きれいだね」と言ってくれました。
- idx 3: うれしかったです。

## 36d2ad28-6b57-40ad-b687-76b0a27cfdc8 — ぎたーのTシャツをつくろう

Passage (for context, do not translate as a block unless the arm says so):

わたしは、ちいさなバンドのTシャツをデザインしました。ぎたーの絵をグラフィックスにして、白いTシャツに印刷します。みんなに見てもらいたいからです。

Sentences:

- idx 0: わたしは、ちいさなバンドのTシャツをデザインしました。
- idx 1: ぎたーの絵をグラフィックスにして、白いTシャツに印刷します。
- idx 2: みんなに見てもらいたいからです。

## 27f67de9-9c06-4ace-bfee-45ccff67fd67 — うきよえができるまで

Passage (for context, do not translate as a block unless the arm says so):

日本の浮世絵は、木の板で作る印刷の芸術です。同じ絵をたくさん作れます。まず、ほる人が、板に絵をほります。つぎに、する人が色をかえて、紙に何回もおします。みんなで作る、日本の大切な工芸です。

Sentences:

- idx 0: 日本の浮世絵は、木の板で作る印刷の芸術です。
- idx 1: 同じ絵をたくさん作れます。
- idx 2: まず、ほる人が、板に絵をほります。
- idx 3: つぎに、する人が色をかえて、紙に何回もおします。
- idx 4: みんなで作る、日本の大切な工芸です。

## 6dc7b01b-3883-4c78-b85b-5ed32d8f9cc2 — 色でつたえるお店の気持ち

Passage (for context, do not translate as a block unless the arm says so):

お店の人は、ロゴの色をえらぶとき、よく考えます。赤は元気な気持ちになり、青はおちついた気持ちになるからです。お客さんは、色を見て、そのお店のことをおぼえます。

Sentences:

- idx 0: お店の人は、ロゴの色をえらぶとき、よく考えます。
- idx 1: 赤は元気な気持ちになり、青はおちついた気持ちになるからです。
- idx 2: お客さんは、色を見て、そのお店のことをおぼえます。

## f202bfa7-dd27-48d3-bcd0-947ba3886e3c — みんなで見る、建物のいいところ

Passage (for context, do not translate as a block unless the arm says so):

建築の批評とは、建物を見て、よい点やわるい点を話すことです。ある先生は、一つの理論、つまり一つの考え方だけで建物を見ません。なぜなら、人によって見方がちがうからです。学校で、みんなの意見を聞いて、考えます。

Sentences:

- idx 0: 建築の批評とは、建物を見て、よい点やわるい点を話すことです。
- idx 1: ある先生は、一つの理論、つまり一つの考え方だけで建物を見ません。
- idx 2: なぜなら、人によって見方がちがうからです。
- idx 3: 学校で、みんなの意見を聞いて、考えます。

## f8093879-9e69-497e-9e1a-8d77dd3a381a — あついひのレモネードや

Passage (for context, do not translate as a block unless the arm says so):

夏のあつい日に、男の子はレモネードを売っています。レモネードは一ぱい百円です。たくさんの人が来て、買ってくれました。男の子はお金をもらって、とてもうれしそうです。

Sentences:

- idx 0: 夏のあつい日に、男の子はレモネードを売っています。
- idx 1: レモネードは一ぱい百円です。
- idx 2: たくさんの人が来て、買ってくれました。
- idx 3: 男の子はお金をもらって、とてもうれしそうです。

## 5c037be1-1dea-4807-9acc-48051be5c773 — りんごをかったよ

Passage (for context, do not translate as a block unless the arm says so):

きのう、ゆうとくんは母と市場へ行きました。ゆうとくんは、お金を持って、赤いりんごを買いに行きました。りんごの屋台で、おじさんに「二つください」と言いました。おじさんは、大きなふくろにりんごを入れてくれました。ゆうとくんは、うれしくてわらいました。

Sentences:

- idx 0: きのう、ゆうとくんは母と市場へ行きました。
- idx 1: ゆうとくんは、お金を持って、赤いりんごを買いに行きました。
- idx 2: りんごの屋台で、おじさんに「二つください」と言いました。
- idx 3: おじさんは、大きなふくろにりんごを入れてくれました。
- idx 4: ゆうとくんは、うれしくてわらいました。

## c73e7969-fea9-40e6-9de1-7fea90df842f — 手作りジュエリーで始めるオンラインビジネス入門

Passage (for context, do not translate as a block unless the arm says so):

ハンドメイドのアクセサリーを売りたい人は、まずオンラインビジネスを始めます。写真をきれいにとって、ネットで販売します。そして、たくさんの人に見てもらうために、SNSでマーケティングをします。

Sentences:

- idx 0: ハンドメイドのアクセサリーを売りたい人は、まずオンラインビジネスを始めます。
- idx 1: 写真をきれいにとって、ネットで販売します。
- idx 2: そして、たくさんの人に見てもらうために、SNSでマーケティングをします。

## 8cdd5ff6-e5f7-42b7-bc58-fd598078a5f3 — スタートアップのはじまりから会社を売るまで

Passage (for context, do not translate as a block unless the arm says so):

スタートアップは、新しい会社です。たとえば、ゆうきさんは新しいアプリを作るために、人からお金を集めます。これを資金調達といいます。会社が成長すると、ほかの大きな会社に会社を売ります。これが出口戦略です。

Sentences:

- idx 0: スタートアップは、新しい会社です。
- idx 1: たとえば、ゆうきさんは新しいアプリを作るために、人からお金を集めます。
- idx 2: これを資金調達といいます。
- idx 3: 会社が成長すると、ほかの大きな会社に会社を売ります。
- idx 4: これが出口戦略です。

## d6dd04d3-9e7e-4435-866f-5cb3b691ea80 — お金を出して新しい会社を助けるしくみ

Passage (for context, do not translate as a block unless the arm says so):

テック業界の小さな新しい会社は、お金が足りないことがよくあります。ベンチャーキャピタルは、その会社にお金を出して、助けます。これがスタートアップの資金調達です。新しい物を作ることを、イノベーションといいます。

Sentences:

- idx 0: テック業界の小さな新しい会社は、お金が足りないことがよくあります。
- idx 1: ベンチャーキャピタルは、その会社にお金を出して、助けます。
- idx 2: これがスタートアップの資金調達です。
- idx 3: 新しい物を作ることを、イノベーションといいます。

## bfb1c906-03bd-4328-b7d7-98be909dee54 — お金をたくさん出すと物の値段は？

Passage (for context, do not translate as a block unless the arm says so):

国は、お金の動かし方を決める金融政策をします。国の債務、つまり借りたお金が多いとき、市場にお金をたくさん出します。すると、物の値段が上がるインフレになることがあります。

Sentences:

- idx 0: 国は、お金の動かし方を決める金融政策をします。
- idx 1: 国の債務、つまり借りたお金が多いとき、市場にお金をたくさん出します。
- idx 2: すると、物の値段が上がるインフレになることがあります。

## cf4bb36e-1661-4593-80a5-ba7276563647 — ゆうたさんと赤いりんご

Passage (for context, do not translate as a block unless the arm says so):

きょう、ゆうたさんは公園で赤いりんごを食べています。りんごは果物です。ゆうたさんは「あまくて、おいしいです」と言いました。りんごはとても大きいので、ゆうたさんはゆっくり食べます。そして、とてもうれしそうです。

Sentences:

- idx 0: きょう、ゆうたさんは公園で赤いりんごを食べています。
- idx 1: りんごは果物です。
- idx 2: ゆうたさんは「あまくて、おいしいです」と言いました。
- idx 3: りんごはとても大きいので、ゆうたさんはゆっくり食べます。
- idx 4: そして、とてもうれしそうです。
