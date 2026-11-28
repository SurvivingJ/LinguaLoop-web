# Author brief 05 — ja -> en, arm `sentencewise`

Read `data/sentence_refs/ja/run_02/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/ja/run_02/sentence_refs/docs/<test_id>.en.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/ja/run_02 --tests e8991934-711a-4540-91be-b50888ee9dd1,5e5e612f-63ee-4e9b-b60c-65cf037b5cd0,73630133-6abb-4d9d-bea4-4a6b11eed5b8,6299d8c2-3fed-41c9-86c5-dba4f1d147a4,01ffc7b8-49ad-42b7-bc6b-f82f6748baf7,8c5b276b-fee0-4b07-ab4d-f2ca383995c7,30cb438b-c540-4cb3-82df-4fa2d18904fa,a8b09c1c-5135-469a-9760-f0409d341584,3f06eaef-bd77-49ef-baaf-fb1c8e4b7add,98578c2e-415c-4b6c-8cf2-cc3b8d7f8dd2,6cb0a068-cf04-4ded-bee6-588a825aa0b9,e76f5de8-a46c-427c-87bb-48831d1b4a91`
and fix until every test is `ok`.

## e8991934-711a-4540-91be-b50888ee9dd1 — あかりを つけて、けして

Passage (for context, do not translate as a block unless the arm says so):

へやが くらいので、ゆうたさんは かべの スイッチを おして、あかりを つけました。ねる じかんに なると、またスイッチを おして、あかりを けします。あかりが きえると、へやは しずかに なります。

Sentences:

- idx 0: へやが くらいので、ゆうたさんは かべの スイッチを おして、あかりを つけました。
- idx 1: ねる じかんに なると、またスイッチを おして、あかりを けします。
- idx 2: あかりが きえると、へやは しずかに なります。

## 5e5e612f-63ee-4e9b-b60c-65cf037b5cd0 — れいぞうこはなぜ冷たいの？

Passage (for context, do not translate as a block unless the arm says so):

台所にある冷蔵庫は、家電の一つです。冷蔵庫の中には、冷たい風が出てきます。だから、食べ物はあたたかくならないで、長い間、冷たいままです。ドアをあけたままにすると、中があたたかくなります。

Sentences:

- idx 0: 台所にある冷蔵庫は、家電の一つです。
- idx 1: 冷蔵庫の中には、冷たい風が出てきます。
- idx 2: だから、食べ物はあたたかくならないで、長い間、冷たいままです。
- idx 3: ドアをあけたままにすると、中があたたかくなります。

## 73630133-6abb-4d9d-bea4-4a6b11eed5b8 — 3Dプリンターで物を作るしくみ

Passage (for context, do not translate as a block unless the arm says so):

メイカースペースで、ゆうきさんは3Dプリントをしました。パソコンでデザインを書いて、機械に送ります。機械は、薄いプラスチックを一枚ずつ重ねて、物を作ります。このテクノロジーで、ものづくりが楽しくなります。

Sentences:

- idx 0: メイカースペースで、ゆうきさんは3Dプリントをしました。
- idx 1: パソコンでデザインを書いて、機械に送ります。
- idx 2: 機械は、薄いプラスチックを一枚ずつ重ねて、物を作ります。
- idx 3: このテクノロジーで、ものづくりが楽しくなります。

## 6299d8c2-3fed-41c9-86c5-dba4f1d147a4 — 風でまわる！風力発電のひみつ

Passage (for context, do not translate as a block unless the arm says so):

風力発電は、風の力で電気をつくります。風が大きなはねをまわすと、中の機械もまわり、電気ができます。このエネルギー生産は、なくならない再生可能エネルギーです。機械工学の人が、じょうぶな形を考えます。

Sentences:

- idx 0: 風力発電は、風の力で電気をつくります。
- idx 1: 風が大きなはねをまわすと、中の機械もまわり、電気ができます。
- idx 2: このエネルギー生産は、なくならない再生可能エネルギーです。
- idx 3: 機械工学の人が、じょうぶな形を考えます。

## 01ffc7b8-49ad-42b7-bc6b-f82f6748baf7 — 冷めたスープはもう熱くならない

Passage (for context, do not translate as a block unless the arm says so):

女の子が、熱いスープを台所の机に置きました。しばらくすると、スープの熱が空気に広がって、スープは冷めます。冷めたスープは、どれだけ待っても、ひとりでは熱くなりません。

Sentences:

- idx 0: 女の子が、熱いスープを台所の机に置きました。
- idx 1: しばらくすると、スープの熱が空気に広がって、スープは冷めます。
- idx 2: 冷めたスープは、どれだけ待っても、ひとりでは熱くなりません。

## 8c5b276b-fee0-4b07-ab4d-f2ca383995c7 — AIが町のくらしを守るには

Passage (for context, do not translate as a block unless the arm says so):

「AI倫理」とは、AIを正しく使うための考え方です。町の水道や電気などのインフラを、自律システムが人の助けなしで動かすことがあります。でも、まちがえると、みんながこまります。だから、国は規制をつくって、人が見はることにしました。

Sentences:

- idx 0: 「AI倫理」とは、AIを正しく使うための考え方です。
- idx 1: 町の水道や電気などのインフラを、自律システムが人の助けなしで動かすことがあります。
- idx 2: でも、まちがえると、みんながこまります。
- idx 3: だから、国は規制をつくって、人が見はることにしました。

## 30cb438b-c540-4cb3-82df-4fa2d18904fa — ゴールにシュート！

Passage (for context, do not translate as a block unless the arm says so):

きのう、たろうくんは公園でサッカーをしました。たろうくんは、大きなボールを足でけりました。ボールは、ゴールのあみの中にはいりました。たろうくんは、うれしくて、友だちとジャンプしました。

Sentences:

- idx 0: きのう、たろうくんは公園でサッカーをしました。
- idx 1: たろうくんは、大きなボールを足でけりました。
- idx 2: ボールは、ゴールのあみの中にはいりました。
- idx 3: たろうくんは、うれしくて、友だちとジャンプしました。

## a8b09c1c-5135-469a-9760-f0409d341584 — ボールをなげてキャッチ！

Passage (for context, do not translate as a block unless the arm says so):

きのう、たろうさんと公園でサッカーのボールを使って遊びました。たろうさんがボールを高くなげて、わたしが手でキャッチしました。ボールが手に入ると、とてもうれしかったです。二人でたくさん笑いました。

Sentences:

- idx 0: きのう、たろうさんと公園でサッカーのボールを使って遊びました。
- idx 1: たろうさんがボールを高くなげて、わたしが手でキャッチしました。
- idx 2: ボールが手に入ると、とてもうれしかったです。
- idx 3: 二人でたくさん笑いました。

## 3f06eaef-bd77-49ef-baaf-fb1c8e4b7add — バスケのまもりかたが変わった

Passage (for context, do not translate as a block unless the arm says so):

バスケットボールのディフェンスには、いろいろな戦略があります。むかしは、一人が一人の相手を守りました。でも、今は、五人でコートの場所を分けて守る戦術もあります。そうすると、ボールを持つ人がシュートしにくくなります。

Sentences:

- idx 0: バスケットボールのディフェンスには、いろいろな戦略があります。
- idx 1: むかしは、一人が一人の相手を守りました。
- idx 2: でも、今は、五人でコートの場所を分けて守る戦術もあります。
- idx 3: そうすると、ボールを持つ人がシュートしにくくなります。

## 98578c2e-415c-4b6c-8cf2-cc3b8d7f8dd2 — 数字でさがす野球の星

Passage (for context, do not translate as a block unless the arm says so):

野球のチームは、たくさんの数字を見て、よい子をさがします。これをデータ分析といいます。スカウティングでは、足の速さやボールの強さを見ます。そして、入った子をゆっくり育てます。それが育成です。

Sentences:

- idx 0: 野球のチームは、たくさんの数字を見て、よい子をさがします。
- idx 1: これをデータ分析といいます。
- idx 2: スカウティングでは、足の速さやボールの強さを見ます。
- idx 3: そして、入った子をゆっくり育てます。
- idx 4: それが育成です。

## 6cb0a068-cf04-4ded-bee6-588a825aa0b9 — データで強いチームをつくる野球

Passage (for context, do not translate as a block unless the arm says so):

野球のチームは、データ分析をして、戦略を考えます。たとえば、どの選手がよく打つかを数字で調べます。そして、マネジメントをする人は、その数字を見て、試合に出る人を決めます。なぜなら、強いチームにしたいからです。

Sentences:

- idx 0: 野球のチームは、データ分析をして、戦略を考えます。
- idx 1: たとえば、どの選手がよく打つかを数字で調べます。
- idx 2: そして、マネジメントをする人は、その数字を見て、試合に出る人を決めます。
- idx 3: なぜなら、強いチームにしたいからです。

## e76f5de8-a46c-427c-87bb-48831d1b4a91 — あかいくるまのおとこのこ

Passage (for context, do not translate as a block unless the arm says so):

あかい車に乗っている男の子がいます。男の子は、まっすぐな通りを走っています。車はとても小さくて、足でゆっくり進みます。道の左がわには、きれいな花がさいています。男の子は、花を見て、にこにこしています。

Sentences:

- idx 0: あかい車に乗っている男の子がいます。
- idx 1: 男の子は、まっすぐな通りを走っています。
- idx 2: 車はとても小さくて、足でゆっくり進みます。
- idx 3: 道の左がわには、きれいな花がさいています。
- idx 4: 男の子は、花を見て、にこにこしています。
