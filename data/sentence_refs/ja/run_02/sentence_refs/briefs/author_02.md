# Author brief 02 — ja -> en, arm `sentencewise`

Read `data/sentence_refs/ja/run_02/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/ja/run_02/sentence_refs/docs/<test_id>.en.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/ja/run_02 --tests 81a5bc60-0a53-43fd-9ab3-bd878c1fa2d3,bc861fa5-0bcd-4d5a-a5cc-717f806a57d7,8c006c75-cdf1-4250-a628-5ba454c4fbbe,f7308ee3-42c8-41d5-8367-f4d5ad4da007,960b69b4-25b7-40b3-b404-a3091d637ab8,9d222c8f-2e16-4560-86d3-aef687f40566,132a3e72-5c4c-4342-a5d5-5312c89dbd85,5316f30b-4c08-4f14-ac80-4a9382745d5c,0883a1fb-f300-4091-8c9b-b6fda3b62643,f84f7d23-0932-4d02-a003-7f9fc634759c,329980c1-b51b-42f8-b71f-9dcdfd358220,abd56f29-c937-4331-b8b6-bfc6a4c4d97b`
and fix until every test is `ok`.

## 81a5bc60-0a53-43fd-9ab3-bd878c1fa2d3 — つみきでタワーをつくろう

Passage (for context, do not translate as a block unless the arm says so):

きょう、たろうくんは、こうえんで積み木を使って遊びました。たろうくんは、高いタワーを作ります。でも、上に積み木をおくと、タワーはたおれました。そして、たろうくんは、もういちど、ゆっくり作りました。

Sentences:

- idx 0: きょう、たろうくんは、こうえんで積み木を使って遊びました。
- idx 1: たろうくんは、高いタワーを作ります。
- idx 2: でも、上に積み木をおくと、タワーはたおれました。
- idx 3: そして、たろうくんは、もういちど、ゆっくり作りました。

## bc861fa5-0bcd-4d5a-a5cc-717f806a57d7 — うさぎのおはなし

Passage (for context, do not translate as a block unless the arm says so):

子どもたちは、就寝前にベッドの上で、お母さんの読み聞かせを聞きます。いちばん好きな物語は、小さなうさぎの話です。やさしい声を聞くと、安心して、すぐに眠くなります。

Sentences:

- idx 0: 子どもたちは、就寝前にベッドの上で、お母さんの読み聞かせを聞きます。
- idx 1: いちばん好きな物語は、小さなうさぎの話です。
- idx 2: やさしい声を聞くと、安心して、すぐに眠くなります。

## 8c006c75-cdf1-4250-a628-5ba454c4fbbe — でんきが つく きえる

Passage (for context, do not translate as a block unless the arm says so):

夜、部屋が暗くなったので、わたしは壁にあるスイッチを押しました。すると、電気がぱっとつきました。本を読み終わったあと、もう一度スイッチを押すと、電気は消えます。電気がつくと明るくなり、消えると部屋はまた暗くなります。だから、寝る前には必ず消します。

Sentences:

- idx 0: 夜、部屋が暗くなったので、わたしは壁にあるスイッチを押しました。
- idx 1: すると、電気がぱっとつきました。
- idx 2: 本を読み終わったあと、もう一度スイッチを押すと、電気は消えます。
- idx 3: 電気がつくと明るくなり、消えると部屋はまた暗くなります。
- idx 4: だから、寝る前には必ず消します。

## f7308ee3-42c8-41d5-8367-f4d5ad4da007 — あかちゃんと おんがく

Passage (for context, do not translate as a block unless the arm says so):

音楽が きこえると、赤ちゃんは うれしそうに 手をたたきます。そして、からだを ゆらして 踊ります。おかあさんも いっしょに わらいます。赤ちゃんは、この時間が とても すきです。

Sentences:

- idx 0: 音楽が きこえると、赤ちゃんは うれしそうに 手をたたきます。
- idx 1: そして、からだを ゆらして 踊ります。
- idx 2: おかあさんも いっしょに わらいます。
- idx 3: 赤ちゃんは、この時間が とても すきです。

## 960b69b4-25b7-40b3-b404-a3091d637ab8 — でんきがつく、きえる

Passage (for context, do not translate as a block unless the arm says so):

夜、くらい部屋で、ゆうとさんが壁のスイッチをおしました。すると、電気がつきました。部屋はあかるくなりました。ねる前に、ゆうとさんはもう一度スイッチをおしました。電気は消えました。

Sentences:

- idx 0: 夜、くらい部屋で、ゆうとさんが壁のスイッチをおしました。
- idx 1: すると、電気がつきました。
- idx 2: 部屋はあかるくなりました。
- idx 3: ねる前に、ゆうとさんはもう一度スイッチをおしました。
- idx 4: 電気は消えました。

## 9d222c8f-2e16-4560-86d3-aef687f40566 — れいぞうこはどうしてつめたいの？

Passage (for context, do not translate as a block unless the arm says so):

冷蔵庫は、キッチンにある家電です。中には冷たい風が入っていて、食べ物を冷たくします。冷たいと、牛乳や野菜は長い間おいしいままです。だから、わたしたちは毎日、冷蔵庫を使います。

Sentences:

- idx 0: 冷蔵庫は、キッチンにある家電です。
- idx 1: 中には冷たい風が入っていて、食べ物を冷たくします。
- idx 2: 冷たいと、牛乳や野菜は長い間おいしいままです。
- idx 3: だから、わたしたちは毎日、冷蔵庫を使います。

## 132a3e72-5c4c-4342-a5d5-5312c89dbd85 — あかいくるまでぶーん

Passage (for context, do not translate as a block unless the arm says so):

日曜日の朝、小さな男の子が赤い車に乗って、家の前の通りを走っていました。この車は、おじいさんが誕生日にプレゼントしてくれたものです。男の子はうれしくて、何度も同じ通りを行ったり来たりしました。すると、近所の人たちが手をふってくれたので、男の子は笑顔で手をふりかえしました。

Sentences:

- idx 0: 日曜日の朝、小さな男の子が赤い車に乗って、家の前の通りを走っていました。
- idx 1: この車は、おじいさんが誕生日にプレゼントしてくれたものです。
- idx 2: 男の子はうれしくて、何度も同じ通りを行ったり来たりしました。
- idx 3: すると、近所の人たちが手をふってくれたので、男の子は笑顔で手をふりかえしました。

## 5316f30b-4c08-4f14-ac80-4a9382745d5c — たろうくんのゴール

Passage (for context, do not translate as a block unless the arm says so):

きょう、たろうくんは、こうえんでサッカーをしました。たろうくんは、ボールを足でつよく蹴りました。ボールは、ゴールのネットにはいりました。たろうくんは、とてもうれしくて、ともだちとわらいました。

Sentences:

- idx 0: きょう、たろうくんは、こうえんでサッカーをしました。
- idx 1: たろうくんは、ボールを足でつよく蹴りました。
- idx 2: ボールは、ゴールのネットにはいりました。
- idx 3: たろうくんは、とてもうれしくて、ともだちとわらいました。

## 0883a1fb-f300-4091-8c9b-b6fda3b62643 — ボールでキャッチボール

Passage (for context, do not translate as a block unless the arm says so):

きのう、公園でともだちとサッカーのボールを使って遊びました。ボールを足でけらないで、手でキャッチしました。ボールが高くとんだので、みんなで走りました。とても楽しかったです。

Sentences:

- idx 0: きのう、公園でともだちとサッカーのボールを使って遊びました。
- idx 1: ボールを足でけらないで、手でキャッチしました。
- idx 2: ボールが高くとんだので、みんなで走りました。
- idx 3: とても楽しかったです。

## f84f7d23-0932-4d02-a003-7f9fc634759c — あかいくるまのおとこのこ

Passage (for context, do not translate as a block unless the arm says so):

きょう、赤い車に乗った男の子が、家の前の通りを走っています。男の子は、車のハンドルをしっかりもっています。となりの道には、犬がいます。男の子は、犬を見て、にこにこ笑いました。

Sentences:

- idx 0: きょう、赤い車に乗った男の子が、家の前の通りを走っています。
- idx 1: 男の子は、車のハンドルをしっかりもっています。
- idx 2: となりの道には、犬がいます。
- idx 3: 男の子は、犬を見て、にこにこ笑いました。

## 329980c1-b51b-42f8-b71f-9dcdfd358220 — たろうさんのBMXれんしゅう

Passage (for context, do not translate as a block unless the arm says so):

たろうさんは、町のトラックで、BMXの自転車に乗るれんしゅうをしました。道には、小さな山がたくさんあります。たろうさんは、からだをひくくして、ゆっくり走りました。ともだちに教えてもらって、少しずつスキルが上がりました。

Sentences:

- idx 0: たろうさんは、町のトラックで、BMXの自転車に乗るれんしゅうをしました。
- idx 1: 道には、小さな山がたくさんあります。
- idx 2: たろうさんは、からだをひくくして、ゆっくり走りました。
- idx 3: ともだちに教えてもらって、少しずつスキルが上がりました。

## abd56f29-c937-4331-b8b6-bfc6a4c4d97b — ヘルメットのしょうぼうし

Passage (for context, do not translate as a block unless the arm says so):

消防士は、ヘルメットをかぶって、火事の家に行きます。家の中に、助けをまっている人がいます。消防士は、その人を見つけて、外へ出します。ヘルメットは、あたまを守ります。だから、安心して救助ができます。

Sentences:

- idx 0: 消防士は、ヘルメットをかぶって、火事の家に行きます。
- idx 1: 家の中に、助けをまっている人がいます。
- idx 2: 消防士は、その人を見つけて、外へ出します。
- idx 3: ヘルメットは、あたまを守ります。
- idx 4: だから、安心して救助ができます。
