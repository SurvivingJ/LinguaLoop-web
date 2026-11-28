# Author brief 04 — ja -> en, arm `sentencewise`

Read `data/sentence_refs/ja/run_02/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/ja/run_02/sentence_refs/docs/<test_id>.en.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/ja/run_02 --tests 0bfbb0a3-def5-4f99-a850-10090fa6c24a,ea3bd937-51c2-4605-8cd3-18624b70647f,509f536b-b7c0-4258-bef2-0aaf3eec4b69,d71cadf7-6639-4386-8fde-51ac5ea4ee5d,f6969ac9-6511-414d-8379-ed59733a5c96,1c73c71d-202a-4a61-bd23-baccf1a9b947,9968e60a-bba6-4d14-b839-1e8aeede92b1,bfc9a641-c494-4959-9b36-2872864baeab,05f0bcca-14f8-4db6-8d77-107d066ecdc7,e0400cd5-9d80-489a-9ab3-27ac9e038dd7,fac9f03e-0293-4ea6-8d5c-d8d284b4b0f8,68e30b68-5ac1-4b03-9aab-7d0a873680d8`
and fix until every test is `ok`.

## 0bfbb0a3-def5-4f99-a850-10090fa6c24a — 活版印刷が変えた宗教と人々の伝え方

Passage (for context, do not translate as a block unless the arm says so):

昔のヨーロッパでは、本を手で書いていたので、あまり多くありませんでした。活版印刷で本をたくさん作れるようになり、宗教の新しい考えが広まりました。これが宗教改革で、人々のコミュニケーションも変わりました。

Sentences:

- idx 0: 昔のヨーロッパでは、本を手で書いていたので、あまり多くありませんでした。
- idx 1: 活版印刷で本をたくさん作れるようになり、宗教の新しい考えが広まりました。
- idx 2: これが宗教改革で、人々のコミュニケーションも変わりました。

## ea3bd937-51c2-4605-8cd3-18624b70647f — ローマの水道 とおい山から町へ

Passage (for context, do not translate as a block unless the arm says so):

むかし、ローマの人たちは、とおい山から町まで、水を運ぶ長い道をつくりました。これは、ものをつくる工学の力です。水の道は、高いところから低いところへ、ゆっくり水を流します。人びとが毎日くらすために大切なインフラでした。

Sentences:

- idx 0: むかし、ローマの人たちは、とおい山から町まで、水を運ぶ長い道をつくりました。
- idx 1: これは、ものをつくる工学の力です。
- idx 2: 水の道は、高いところから低いところへ、ゆっくり水を流します。
- idx 3: 人びとが毎日くらすために大切なインフラでした。

## 509f536b-b7c0-4258-bef2-0aaf3eec4b69 — ゆうたくんと高いつみきタワー

Passage (for context, do not translate as a block unless the arm says so):

きょう、ゆうたくんは家で積み木を作ります。ゆうたくんは、たくさんの積み木を高くのせて、大きなタワーを作ります。でも、タワーはとちゅうでたおれました。ゆうたくんは、もう一度ゆっくり積んで、うれしそうに遊びました。

Sentences:

- idx 0: きょう、ゆうたくんは家で積み木を作ります。
- idx 1: ゆうたくんは、たくさんの積み木を高くのせて、大きなタワーを作ります。
- idx 2: でも、タワーはとちゅうでたおれました。
- idx 3: ゆうたくんは、もう一度ゆっくり積んで、うれしそうに遊びました。

## d71cadf7-6639-4386-8fde-51ac5ea4ee5d — ゆうきさんのはじめての詩

Passage (for context, do not translate as a block unless the arm says so):

きのう、10代のゆうきさんは、はじめて みんなの前で 詩を読みました。スポークンワードのパフォーマンスです。ゆうきさんは、どきどきしましたが、大きな声で読みました。さいごに、みんなが大きな拍手をしました。

Sentences:

- idx 0: きのう、10代のゆうきさんは、はじめて みんなの前で 詩を読みました。
- idx 1: スポークンワードのパフォーマンスです。
- idx 2: ゆうきさんは、どきどきしましたが、大きな声で読みました。
- idx 3: さいごに、みんなが大きな拍手をしました。

## f6969ac9-6511-414d-8379-ed59733a5c96 — ソネットってどんなうた？

Passage (for context, do not translate as a block unless the arm says so):

ソネットは、十四の行でできている詩の形式です。むかし、イタリアで生まれました。そして、長い歴史の中で、ほかの国にも広がりました。人びとは、気持ちを短くつたえるために、この形式を使いました。

Sentences:

- idx 0: ソネットは、十四の行でできている詩の形式です。
- idx 1: むかし、イタリアで生まれました。
- idx 2: そして、長い歴史の中で、ほかの国にも広がりました。
- idx 3: 人びとは、気持ちを短くつたえるために、この形式を使いました。

## 1c73c71d-202a-4a61-bd23-baccf1a9b947 — 手紙から広がる小説の世界：書簡体の語りの進化

Passage (for context, do not translate as a block unless the arm says so):

むかし、人は手紙の形で小説を書きました。これを書簡体といいます。手紙を書く人が、自分の気持ちを語ります。この技法は、時間がたつと、いろいろな形に進化しました。

Sentences:

- idx 0: むかし、人は手紙の形で小説を書きました。
- idx 1: これを書簡体といいます。
- idx 2: 手紙を書く人が、自分の気持ちを語ります。
- idx 3: この技法は、時間がたつと、いろいろな形に進化しました。

## 9968e60a-bba6-4d14-b839-1e8aeede92b1 — あかちゃんとおんがく

Passage (for context, do not translate as a block unless the arm says so):

日曜日の朝、赤ちゃんはリビングで音楽を聞いています。音楽が大きくなると、赤ちゃんはうれしそうに手をたたきます。おかあさんも赤ちゃんの前で踊ります。赤ちゃんはそれを見て、もっと大きく手をたたきます。

Sentences:

- idx 0: 日曜日の朝、赤ちゃんはリビングで音楽を聞いています。
- idx 1: 音楽が大きくなると、赤ちゃんはうれしそうに手をたたきます。
- idx 2: おかあさんも赤ちゃんの前で踊ります。
- idx 3: 赤ちゃんはそれを見て、もっと大きく手をたたきます。

## bfc9a641-c494-4959-9b36-2872864baeab — うそを見つける図書室の読書

Passage (for context, do not translate as a block unless the arm says so):

図書室で、ゆうきさんは小説を読んでいます。語りの声は、ときどきうそを言います。ゆうきさんは先生に聞いた理論、つまり考え方を使って、うそを見つけます。なぜなら、本当のことを知りたいからです。

Sentences:

- idx 0: 図書室で、ゆうきさんは小説を読んでいます。
- idx 1: 語りの声は、ときどきうそを言います。
- idx 2: ゆうきさんは先生に聞いた理論、つまり考え方を使って、うそを見つけます。
- idx 3: なぜなら、本当のことを知りたいからです。

## 05f0bcca-14f8-4db6-8d77-107d066ecdc7 — ゆいさんのピアノ練習

Passage (for context, do not translate as a block unless the arm says so):

ゆいさんは、まいにちピアノの練習をします。きのうは、学校から帰ってから三十分、音楽の先生に教えてもらった曲をひきました。ゆいさんは、うまくなりたいので、ゆっくり学習します。

Sentences:

- idx 0: ゆいさんは、まいにちピアノの練習をします。
- idx 1: きのうは、学校から帰ってから三十分、音楽の先生に教えてもらった曲をひきました。
- idx 2: ゆいさんは、うまくなりたいので、ゆっくり学習します。

## e0400cd5-9d80-489a-9ab3-27ac9e038dd7 — はじめてのギターソロ、ドキドキ！

Passage (for context, do not translate as a block unless the arm says so):

10代の男の子が、はじめてたくさんの観客の前で、ギターのソロを演奏しました。手がふるえましたが、大きく息をすって、ゆっくりひきました。さいごに、みんながたくさん拍手をしてくれました。

Sentences:

- idx 0: 10代の男の子が、はじめてたくさんの観客の前で、ギターのソロを演奏しました。
- idx 1: 手がふるえましたが、大きく息をすって、ゆっくりひきました。
- idx 2: さいごに、みんながたくさん拍手をしてくれました。

## fac9f03e-0293-4ea6-8d5c-d8d284b4b0f8 — あたらしい音をさがす無調音楽

Passage (for context, do not translate as a block unless the arm says so):

20世紀の音楽には、無調音楽があります。これは、クラシック音楽の中で、中心になる音をきめない音楽です。作る人たちは、哲学、つまりものごとを深く考えることから、新しい音をさがしました。

Sentences:

- idx 0: 20世紀の音楽には、無調音楽があります。
- idx 1: これは、クラシック音楽の中で、中心になる音をきめない音楽です。
- idx 2: 作る人たちは、哲学、つまりものごとを深く考えることから、新しい音をさがしました。

## 68e30b68-5ac1-4b03-9aab-7d0a873680d8 — ソナタ形式をこわして物語をつくる現代音楽

Passage (for context, do not translate as a block unless the arm says so):

クラシック音楽の作曲には、ソナタ形式というきまりがあります。いまの作曲家は、そのきまりをわざとこわして、曲を作ります。でも、話のようにつながって聞こえるように、くふうしています。

Sentences:

- idx 0: クラシック音楽の作曲には、ソナタ形式というきまりがあります。
- idx 1: いまの作曲家は、そのきまりをわざとこわして、曲を作ります。
- idx 2: でも、話のようにつながって聞こえるように、くふうしています。
