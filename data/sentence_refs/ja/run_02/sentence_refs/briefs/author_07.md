# Author brief 07 — ja -> en, arm `sentencewise`

Read `data/sentence_refs/ja/run_02/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/ja/run_02/sentence_refs/docs/<test_id>.en.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/ja/run_02 --tests 3f532177-5efe-475b-86eb-888d379ab1c1,6b71a624-1fe6-4abe-8e92-b9cf6ee216d5,546e7b89-51af-48af-a3ee-f9559eade333,6823748c-cd33-41a1-b341-fabce79d078a,38682096-00ec-450d-9447-29b436ea8c89,156da393-98a4-4578-a81c-3229fe394e52,7703e8f6-3df2-45aa-900f-afbf0e58b752,4d73c50b-aa05-47e5-b553-63cdebf839d2,f49ec5ee-93d9-4e79-aa84-81df465b5cee,f201e1dc-dad4-411f-bfc4-cbb5f111d9e1,c2727f45-771a-4877-9ffa-c20d21db3690,85449b98-bb90-481b-84e4-ac16b31ca0ea`
and fix until every test is `ok`.

## 3f532177-5efe-475b-86eb-888d379ab1c1 — にわとりとおじさんのあさ

Passage (for context, do not translate as a block unless the arm says so):

あさ、のうじょうのおじさんは、はやくおきます。おひさまが出ると、にわとりにたべものをやります。にわとりはよろこんで、たくさんたべます。そして、おいしいたまごをうみます。おじさんはそのたまごをもって、いえにかえります。

Sentences:

- idx 0: あさ、のうじょうのおじさんは、はやくおきます。
- idx 1: おひさまが出ると、にわとりにたべものをやります。
- idx 2: にわとりはよろこんで、たくさんたべます。
- idx 3: そして、おいしいたまごをうみます。
- idx 4: おじさんはそのたまごをもって、いえにかえります。

## 6b71a624-1fe6-4abe-8e92-b9cf6ee216d5 — ニワトリのそだちかた

Passage (for context, do not translate as a block unless the arm says so):

養鶏は、家禽のニワトリをそだてる畜産のしごとです。ひよこは、あたたかい小屋で、えさをたくさん食べます。そして、およそ二か月で大きくなります。ニワトリも、牛やぶたと同じ家畜です。

Sentences:

- idx 0: 養鶏は、家禽のニワトリをそだてる畜産のしごとです。
- idx 1: ひよこは、あたたかい小屋で、えさをたくさん食べます。
- idx 2: そして、およそ二か月で大きくなります。
- idx 3: ニワトリも、牛やぶたと同じ家畜です。

## 546e7b89-51af-48af-a3ee-f9559eade333 — たろうさんの はじめての ゆうきやさい作り

Passage (for context, do not translate as a block unless the arm says so):

十五さいの たろうさんは、有機野菜の農場で はたらき はじめました。さいしょは、毎日 土をたがやして、野菜の たねを まきました。いそがしい仕事でしたが、一年たつと、おいしい野菜が たくさん できました。

Sentences:

- idx 0: 十五さいの たろうさんは、有機野菜の農場で はたらき はじめました。
- idx 1: さいしょは、毎日 土をたがやして、野菜の たねを まきました。
- idx 2: いそがしい仕事でしたが、一年たつと、おいしい野菜が たくさん できました。

## 6823748c-cd33-41a1-b341-fabce79d078a — 精密農業でむだなく収穫量を増やす方法

Passage (for context, do not translate as a block unless the arm says so):

精密農業は、畑のようすをくわしく調べる農業です。農家の人は、水や肥料を、必要な場所に必要なだけ使います。これが資源管理です。むだをへらすために、使い方の最適化をします。

Sentences:

- idx 0: 精密農業は、畑のようすをくわしく調べる農業です。
- idx 1: 農家の人は、水や肥料を、必要な場所に必要なだけ使います。
- idx 2: これが資源管理です。
- idx 3: むだをへらすために、使い方の最適化をします。

## 38682096-00ec-450d-9447-29b436ea8c89 — 精密農業が変える小規模農家の収入と農村の仕事

Passage (for context, do not translate as a block unless the arm says so):

精密農業は、機械やセンサーを使って、畑の水や肥料の量を決める方法です。小規模農家が技術導入をすると、むだが減って、収入が増えることがあります。でも、機械の仕事が増えるので、農村経済では人の仕事が変わります。

Sentences:

- idx 0: 精密農業は、機械やセンサーを使って、畑の水や肥料の量を決める方法です。
- idx 1: 小規模農家が技術導入をすると、むだが減って、収入が増えることがあります。
- idx 2: でも、機械の仕事が増えるので、農村経済では人の仕事が変わります。

## 156da393-98a4-4578-a81c-3229fe394e52 — あかいドアのちいさないえ

Passage (for context, do not translate as a block unless the arm says so):

もりのなかに、小さい家があります。その家のドアは、赤いです。まいあさ、おばあさんがドアをあけて、そとに出ます。おばあさんは、にわの花にみずをあげます。花はとてもきれいです。

Sentences:

- idx 0: もりのなかに、小さい家があります。
- idx 1: その家のドアは、赤いです。
- idx 2: まいあさ、おばあさんがドアをあけて、そとに出ます。
- idx 3: おばあさんは、にわの花にみずをあげます。
- idx 4: 花はとてもきれいです。

## 7703e8f6-3df2-45aa-900f-afbf0e58b752 — ゆいさんのひみつきち作り

Passage (for context, do not translate as a block unless the arm says so):

ゆいさんは、家の庭に小さなプレイハウスを作ります。まず、紙に設計図をかいて、まどのデザインを考えました。お父さんといっしょに、木で作ります。友だちとあそびたいからです。

Sentences:

- idx 0: ゆいさんは、家の庭に小さなプレイハウスを作ります。
- idx 1: まず、紙に設計図をかいて、まどのデザインを考えました。
- idx 2: お父さんといっしょに、木で作ります。
- idx 3: 友だちとあそびたいからです。

## 4d73c50b-aa05-47e5-b553-63cdebf839d2 — すっきり広いわたしの部屋

Passage (for context, do not translate as a block unless the arm says so):

わたしのアパートは、モダンなインテリアデザインです。ミニマルな部屋には、白いつくえとソファだけがあります。ものが少ないので、そうじがかんたんで、部屋も広く見えます。

Sentences:

- idx 0: わたしのアパートは、モダンなインテリアデザインです。
- idx 1: ミニマルな部屋には、白いつくえとソファだけがあります。
- idx 2: ものが少ないので、そうじがかんたんで、部屋も広く見えます。

## f49ec5ee-93d9-4e79-aa84-81df465b5cee — 石のうでで支える大聖堂のひみつ

Passage (for context, do not translate as a block unless the arm says so):

中世のヨーロッパで、職人たちがゴシックの大聖堂を建設しました。高くて重い石の屋根が落ちないように、外に石のうでをつけて支えました。これは、むかしの工学の工夫です。

Sentences:

- idx 0: 中世のヨーロッパで、職人たちがゴシックの大聖堂を建設しました。
- idx 1: 高くて重い石の屋根が落ちないように、外に石のうでをつけて支えました。
- idx 2: これは、むかしの工学の工夫です。

## f201e1dc-dad4-411f-bfc4-cbb5f111d9e1 — ブルータリズム建築が変えた都市の住まいと暮らし

Passage (for context, do not translate as a block unless the arm says so):

ブルータリズムは、コンクリートをそのまま見せる建物の作り方です。都市計画で、たくさんの人が住む住宅をこの方法で建てました。安くて早く作れましたが、暗くて冷たいと感じる人もいました。町の人の暮らしに、社会的影響がありました。

Sentences:

- idx 0: ブルータリズムは、コンクリートをそのまま見せる建物の作り方です。
- idx 1: 都市計画で、たくさんの人が住む住宅をこの方法で建てました。
- idx 2: 安くて早く作れましたが、暗くて冷たいと感じる人もいました。
- idx 3: 町の人の暮らしに、社会的影響がありました。

## c2727f45-771a-4877-9ffa-c20d21db3690 — 数字でかわる町づくりの形

Passage (for context, do not translate as a block unless the arm says so):

パラメトリックデザインは、数字を変えると形が変わるやり方です。都市計画では、アルゴリズム、つまりコンピューターの決まった手順で、道や建物の案を生成します。そのため、たくさんの案をくらべられます。

Sentences:

- idx 0: パラメトリックデザインは、数字を変えると形が変わるやり方です。
- idx 1: 都市計画では、アルゴリズム、つまりコンピューターの決まった手順で、道や建物の案を生成します。
- idx 2: そのため、たくさんの案をくらべられます。

## 85449b98-bb90-481b-84e4-ac16b31ca0ea — あかいクレヨンのおひさま

Passage (for context, do not translate as a block unless the arm says so):

きょう、わたしは赤いクレヨンで大きくて丸い太陽を描きました。画用紙いっぱいに、ゆっくり円をかきました。赤い色は、あつい夏の日のようです。太陽を見ていると、うれしい気もちになりました。

Sentences:

- idx 0: きょう、わたしは赤いクレヨンで大きくて丸い太陽を描きました。
- idx 1: 画用紙いっぱいに、ゆっくり円をかきました。
- idx 2: 赤い色は、あつい夏の日のようです。
- idx 3: 太陽を見ていると、うれしい気もちになりました。
