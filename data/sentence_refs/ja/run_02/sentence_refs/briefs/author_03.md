# Author brief 03 — ja -> en, arm `sentencewise`

Read `data/sentence_refs/ja/run_02/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/ja/run_02/sentence_refs/docs/<test_id>.en.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/ja/run_02 --tests 6164b2db-a7d0-4947-b885-81eff7a13895,239c7a76-13e2-42c5-bcf2-6487217ceab2,b20398e6-3904-465c-b6a1-4c94b6119ffb,714a679b-07bc-481b-99c1-4aa03d0c1f34,0de9beb7-bf32-4e1e-b647-f4a528e6bf8b,0d81e75c-a3c1-4443-bc22-9897a41485c0,f3b75592-31fa-4941-8034-f474cf5c0584,03046796-36db-48d4-86fa-6daf3d2a1d6f,bad7bc3d-cf96-482a-aaa3-724efddcedd6,3bf63eb0-95f8-400a-8841-438af64cfa41,677541b8-1130-4ebb-ac56-e85a2c78548f,4382a234-3e80-4a93-98dc-aeeef504e118`
and fix until every test is `ok`.

## 6164b2db-a7d0-4947-b885-81eff7a13895 — パンやさんのあさごはん

Passage (for context, do not translate as a block unless the arm says so):

町のパン職人は、まいあさ早くおきて、お店でパンを焼きます。町の人たちに、あたたかいパンを食べてほしいからです。パンのいいにおいがすると、人がたくさん来ます。みんなは、わらってパンを買います。

Sentences:

- idx 0: 町のパン職人は、まいあさ早くおきて、お店でパンを焼きます。
- idx 1: 町の人たちに、あたたかいパンを食べてほしいからです。
- idx 2: パンのいいにおいがすると、人がたくさん来ます。
- idx 3: みんなは、わらってパンを買います。

## 239c7a76-13e2-42c5-bcf2-6487217ceab2 — 自前運用AIは2026年の手本となるか

Passage (for context, do not translate as a block unless the arm says so):

自分のパソコンやサーバーで動かせるAIエージェントが、注目を集めている。特定のAIモデルに縛られず、好きなモデルを選べるのが特徴だ。データを外部に預けずに済むため、プライバシーを守りやすい。一方で、設定や管理は利用者自身の仕事になり、知識が必要である。2026年の手本になるかは、使いやすさ次第だろう。

Sentences:

- idx 0: 自分のパソコンやサーバーで動かせるAIエージェントが、注目を集めている。
- idx 1: 特定のAIモデルに縛られず、好きなモデルを選べるのが特徴だ。
- idx 2: データを外部に預けずに済むため、プライバシーを守りやすい。
- idx 3: 一方で、設定や管理は利用者自身の仕事になり、知識が必要である。
- idx 4: 2026年の手本になるかは、使いやすさ次第だろう。

## b20398e6-3904-465c-b6a1-4c94b6119ffb — AIで しごとが かわる？みんなの みらい

Passage (for context, do not translate as a block unless the arm says so):

AIという新しいコンピューターのしくみが、はやく上手になっています。そのため、会社で仕事をなくす人がふえています。みんなは、あたらしい仕事のしかたをまなぶ時間がひつようです。国は、お金をみんなにわけて、助けることができるでしょうか。

Sentences:

- idx 0: AIという新しいコンピューターのしくみが、はやく上手になっています。
- idx 1: そのため、会社で仕事をなくす人がふえています。
- idx 2: みんなは、あたらしい仕事のしかたをまなぶ時間がひつようです。
- idx 3: 国は、お金をみんなにわけて、助けることができるでしょうか。

## 714a679b-07bc-481b-99c1-4aa03d0c1f34 — 青いセーターのふわふわテディベア

Passage (for context, do not translate as a block unless the arm says so):

青いセーターを着たクマのおもちゃがいます。このクマは、ふわふわで、とてもやわらかいです。ゆきちゃんは、毎晩このクマをだいて、ねます。なぜなら、あたたかくて、あんしんするからです。

Sentences:

- idx 0: 青いセーターを着たクマのおもちゃがいます。
- idx 1: このクマは、ふわふわで、とてもやわらかいです。
- idx 2: ゆきちゃんは、毎晩このクマをだいて、ねます。
- idx 3: なぜなら、あたたかくて、あんしんするからです。

## 0de9beb7-bf32-4e1e-b647-f4a528e6bf8b — 星のついた青いTシャツ

Passage (for context, do not translate as a block unless the arm says so):

わたしのお気に入りの服は、青いTシャツです。となりの町のお店で、お母さんといっしょに買いました。胸に大きな星の絵があります。毎週の日曜日に着て、公園で友だちと遊びます。この前、そのTシャツを着て写真をとりました。

Sentences:

- idx 0: わたしのお気に入りの服は、青いTシャツです。
- idx 1: となりの町のお店で、お母さんといっしょに買いました。
- idx 2: 胸に大きな星の絵があります。
- idx 3: 毎週の日曜日に着て、公園で友だちと遊びます。
- idx 4: この前、そのTシャツを着て写真をとりました。

## 0d81e75c-a3c1-4443-bc22-9897a41485c0 — せっけんで手をきれいに洗おう

Passage (for context, do not translate as a block unless the arm says so):

ごはんの前に、わたしは台所で手を洗います。まず、水で手をぬらして、石けんをつけます。次に、手をよくこすります。石けんは、目に見えない小さい細菌をおとして、手をきれいにします。

Sentences:

- idx 0: ごはんの前に、わたしは台所で手を洗います。
- idx 1: まず、水で手をぬらして、石けんをつけます。
- idx 2: 次に、手をよくこすります。
- idx 3: 石けんは、目に見えない小さい細菌をおとして、手をきれいにします。

## f3b75592-31fa-4941-8034-f474cf5c0584 — けがをしたときの おうきゅうセット

Passage (for context, do not translate as a block unless the arm says so):

スポーツをすると、けがをすることがあります。だから、わたしは学校のかばんに、応急処置のセットを入れます。セットには、ばんそうこうと冷たい水が入っています。けがをしたら、すぐに使います。

Sentences:

- idx 0: スポーツをすると、けがをすることがあります。
- idx 1: だから、わたしは学校のかばんに、応急処置のセットを入れます。
- idx 2: セットには、ばんそうこうと冷たい水が入っています。
- idx 3: けがをしたら、すぐに使います。

## 03046796-36db-48d4-86fa-6daf3d2a1d6f — いのちをつなぐ臓器のていきょう

Passage (for context, do not translate as a block unless the arm says so):

病気で、からだのなかの大切なところがうごかなくなった人がいます。ほかの人が、じぶんの臓器をあげることを、提供といいます。医者は手術をして、その臓器を病気の人のからだに入れます。これが移植で、大切な医療です。

Sentences:

- idx 0: 病気で、からだのなかの大切なところがうごかなくなった人がいます。
- idx 1: ほかの人が、じぶんの臓器をあげることを、提供といいます。
- idx 2: 医者は手術をして、その臓器を病気の人のからだに入れます。
- idx 3: これが移植で、大切な医療です。

## bad7bc3d-cf96-482a-aaa3-724efddcedd6 — おなかの小さな生きものと体を守る力

Passage (for context, do not translate as a block unless the arm says so):

おなかの中には、マイクロバイオームという小さな生きものがたくさんいます。腸の健康がよいと、免疫が病気から体を守ります。自己免疫は、体が自分をまちがえてこうげきすることです。

Sentences:

- idx 0: おなかの中には、マイクロバイオームという小さな生きものがたくさんいます。
- idx 1: 腸の健康がよいと、免疫が病気から体を守ります。
- idx 2: 自己免疫は、体が自分をまちがえてこうげきすることです。

## 3bf63eb0-95f8-400a-8841-438af64cfa41 — 薬理ゲノム学が拓く、個別化医療の現在と未来

Passage (for context, do not translate as a block unless the arm says so):

薬理ゲノム学は、人によって薬のききかたがちがう理由を、遺伝学で調べる勉強です。病院では、薬物療法を始める前に体質を調べる医者がふえています。これが個別化医療で、その人に合う薬を選びます。これから、もっとふえるでしょう。

Sentences:

- idx 0: 薬理ゲノム学は、人によって薬のききかたがちがう理由を、遺伝学で調べる勉強です。
- idx 1: 病院では、薬物療法を始める前に体質を調べる医者がふえています。
- idx 2: これが個別化医療で、その人に合う薬を選びます。
- idx 3: これから、もっとふえるでしょう。

## 677541b8-1130-4ebb-ac56-e85a2c78548f — ローマのこどものきうま

Passage (for context, do not translate as a block unless the arm says so):

むかし、ローマの子どもたちは、木でつくった馬のおもちゃで遊びました。子どもたちは、馬にのって、前と後ろにゆらしました。家の中でも外でも、友だちといっしょに楽しく遊びました。

Sentences:

- idx 0: むかし、ローマの子どもたちは、木でつくった馬のおもちゃで遊びました。
- idx 1: 子どもたちは、馬にのって、前と後ろにゆらしました。
- idx 2: 家の中でも外でも、友だちといっしょに楽しく遊びました。

## 4382a234-3e80-4a93-98dc-aeeef504e118 — 古代ローマの子どもたちのまいにちのおてつだい

Passage (for context, do not translate as a block unless the arm says so):

古代ローマの子どもたちは、毎日、家のしごとをしました。朝は水をくんで、へやをそうじしました。そして、食べものをはこんで、お母さんをてつだいました。家の人がたすけあうことは、日常生活でたいせつだったからです。

Sentences:

- idx 0: 古代ローマの子どもたちは、毎日、家のしごとをしました。
- idx 1: 朝は水をくんで、へやをそうじしました。
- idx 2: そして、食べものをはこんで、お母さんをてつだいました。
- idx 3: 家の人がたすけあうことは、日常生活でたいせつだったからです。
