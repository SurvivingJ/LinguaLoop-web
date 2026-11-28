# Author brief 06 — ja -> en, arm `sentencewise`

Read `data/sentence_refs/ja/run_02/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/ja/run_02/sentence_refs/docs/<test_id>.en.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/ja/run_02 --tests 1863a409-ea39-4aea-8dbd-ffc21b9be474,a5d0c162-a759-4fa9-b7bb-4b62d399d5e0,e1df645c-66b8-4d47-981c-ed43a168b28a,631531cd-f6af-4fdc-b21e-96c17456cb27,3b8bbc1d-5580-450c-aae2-88bbbb25868b,32f65d07-4e25-403e-b6ad-906c58aafa2b,1842d430-455e-4763-9985-6c81a69b3d81,c6e8121a-e8e6-400e-9041-7eafd206102f,770231ae-dd56-45c3-bbbb-5311cba49f3a,dfded4ca-827c-46aa-94a6-b9b8a62220be,ab7e7266-ef6a-48e7-acbb-b89dd6261077,6b763758-8f20-43d7-9ca7-b4b23de62f2a`
and fix until every test is `ok`.

## 1863a409-ea39-4aea-8dbd-ffc21b9be474 — じてんしゃでこうえんへ行こう

Passage (for context, do not translate as a block unless the arm says so):

きのう、ゆうとくんは自転車に乗って、公園へ行きました。いえを出るまえに、ヘルメットをかぶりました。道では、まわりの車をよく見て、ゆっくり走りました。安全に気をつけたので、ぶじに公園へつきました。

Sentences:

- idx 0: きのう、ゆうとくんは自転車に乗って、公園へ行きました。
- idx 1: いえを出るまえに、ヘルメットをかぶりました。
- idx 2: 道では、まわりの車をよく見て、ゆっくり走りました。
- idx 3: 安全に気をつけたので、ぶじに公園へつきました。

## a5d0c162-a759-4fa9-b7bb-4b62d399d5e0 — BMXにのるれんしゅうをしたよ

Passage (for context, do not translate as a block unless the arm says so):

ぼくは、ちかくのこうえんで、BMXの自転車に乗るれんしゅうをしました。トラックは、おかがつづいています。さいしょはこわかったですが、先生におしえてもらいました。そして、じょうずに乗るスキルが少しふえました。

Sentences:

- idx 0: ぼくは、ちかくのこうえんで、BMXの自転車に乗るれんしゅうをしました。
- idx 1: トラックは、おかがつづいています。
- idx 2: さいしょはこわかったですが、先生におしえてもらいました。
- idx 3: そして、じょうずに乗るスキルが少しふえました。

## e1df645c-66b8-4d47-981c-ed43a168b28a — 地下鉄の電車ができるまで

Passage (for context, do not translate as a block unless the arm says so):

地下鉄の電車は、まず工学を学んだ人たちが、どんな形にするかを設計します。次に工場で製造します。そして、乗る人が安全に乗れるように、何回も試験をします。

Sentences:

- idx 0: 地下鉄の電車は、まず工学を学んだ人たちが、どんな形にするかを設計します。
- idx 1: 次に工場で製造します。
- idx 2: そして、乗る人が安全に乗れるように、何回も試験をします。

## 631531cd-f6af-4fdc-b21e-96c17456cb27 — ライドシェアでねだんが変わるのはなぜ？

Passage (for context, do not translate as a block unless the arm says so):

ライドシェアは、車にのりたい人と、のせたい人をつなぎます。のりたい人がおおいと、価格設定のアルゴリズムが、ねだんを高くします。これは経済学で、市場のねだんがかわるしくみです。

Sentences:

- idx 0: ライドシェアは、車にのりたい人と、のせたい人をつなぎます。
- idx 1: のりたい人がおおいと、価格設定のアルゴリズムが、ねだんを高くします。
- idx 2: これは経済学で、市場のねだんがかわるしくみです。

## 3b8bbc1d-5580-450c-aae2-88bbbb25868b — ヘルメットのしょうぼうし

Passage (for context, do not translate as a block unless the arm says so):

消防士は、ヘルメットをかぶって、火事の家に行きます。家の中に、にげられない人がいます。消防士はその人を見つけて、助けます。ヘルメットは、頭をまもります。だから、消防士は安全に救助ができます。

Sentences:

- idx 0: 消防士は、ヘルメットをかぶって、火事の家に行きます。
- idx 1: 家の中に、にげられない人がいます。
- idx 2: 消防士はその人を見つけて、助けます。
- idx 3: ヘルメットは、頭をまもります。
- idx 4: だから、消防士は安全に救助ができます。

## 32f65d07-4e25-403e-b6ad-906c58aafa2b — 空を走る未来の交通：都市型航空モビリティとは

Passage (for context, do not translate as a block unless the arm says so):

人々は、未来の交通として、町の空を使う都市型航空モビリティを考えています。eVTOL(電動垂直離着陸機)は、電気で動き、まっすぐ上に飛べる小さな乗り物です。安全のために、規制という決まりが必要です。

Sentences:

- idx 0: 人々は、未来の交通として、町の空を使う都市型航空モビリティを考えています。
- idx 1: eVTOL(電動垂直離着陸機)は、電気で動き、まっすぐ上に飛べる小さな乗り物です。
- idx 2: 安全のために、規制という決まりが必要です。

## 1842d430-455e-4763-9985-6c81a69b3d81 — パンやさんのあさ

Passage (for context, do not translate as a block unless the arm says so):

町のパン職人は、毎朝早くおきて、パンをやきます。お店には、おいしいパンがたくさんならびます。町の人たちは、そのパンをかって、家ぞくといっしょにたべます。パン職人は、みんなのえがおを見るのがすきです。

Sentences:

- idx 0: 町のパン職人は、毎朝早くおきて、パンをやきます。
- idx 1: お店には、おいしいパンがたくさんならびます。
- idx 2: 町の人たちは、そのパンをかって、家ぞくといっしょにたべます。
- idx 3: パン職人は、みんなのえがおを見るのがすきです。

## c6e8121a-e8e6-400e-9041-7eafd206102f — たろうさんのさいこうのケーキ

Passage (for context, do not translate as a block unless the arm says so):

わかいパティシエのたろうさんは、まいにちお菓子作りをしています。ケーキのレシピをよくするために、なんども作りなおしました。お店で一番おいしいケーキにしたいからです。

Sentences:

- idx 0: わかいパティシエのたろうさんは、まいにちお菓子作りをしています。
- idx 1: ケーキのレシピをよくするために、なんども作りなおしました。
- idx 2: お店で一番おいしいケーキにしたいからです。

## 770231ae-dd56-45c3-bbbb-5311cba49f3a — パン作りの秘密：発酵とふくらみの工程

Passage (for context, do not translate as a block unless the arm says so):

パン職人は、朝早くからお店でベーキングをします。まず、こねた生地をあたたかい場所に置いて、大きくなるまで待ちます。次に、オーブンで焼くと、パンはさらにふくらみます。この工程が、おいしいパンのために大切です。

Sentences:

- idx 0: パン職人は、朝早くからお店でベーキングをします。
- idx 1: まず、こねた生地をあたたかい場所に置いて、大きくなるまで待ちます。
- idx 2: 次に、オーブンで焼くと、パンはさらにふくらみます。
- idx 3: この工程が、おいしいパンのために大切です。

## dfded4ca-827c-46aa-94a6-b9b8a62220be — 会社を育てるお金のひみつ

Passage (for context, do not translate as a block unless the arm says so):

スタートアップは、新しい会社です。新しいものを作って、イノベーションを起こします。でも、お金が足りません。そこで、資金調達をして、お金を出す会社から助けてもらいます。そのお金で、会社は成長します。

Sentences:

- idx 0: スタートアップは、新しい会社です。
- idx 1: 新しいものを作って、イノベーションを起こします。
- idx 2: でも、お金が足りません。
- idx 3: そこで、資金調達をして、お金を出す会社から助けてもらいます。
- idx 4: そのお金で、会社は成長します。

## ab7e7266-ef6a-48e7-acbb-b89dd6261077 — AIで仕事がかわる！まなびなおそう

Passage (for context, do not translate as a block unless the arm says so):

AIという、かしこいコンピューターが、会社の仕事をふやしています。じどうで書類を作る自動化がすすむと、人の仕事がへるかもしれません。だから、あたらしいことを学ぶリスキリングが大切です。

Sentences:

- idx 0: AIという、かしこいコンピューターが、会社の仕事をふやしています。
- idx 1: じどうで書類を作る自動化がすすむと、人の仕事がへるかもしれません。
- idx 2: だから、あたらしいことを学ぶリスキリングが大切です。

## 6b763758-8f20-43d7-9ca7-b4b23de62f2a — 種から大きく育つまで

Passage (for context, do not translate as a block unless the arm says so):

農家の人が、はたけに種をまいています。まず、土をやわらかくして、小さな穴をあけます。そして、穴に種を一つずつ植えます。水をあげて、おひさまの光があたると、種は大きく育ちます。

Sentences:

- idx 0: 農家の人が、はたけに種をまいています。
- idx 1: まず、土をやわらかくして、小さな穴をあけます。
- idx 2: そして、穴に種を一つずつ植えます。
- idx 3: 水をあげて、おひさまの光があたると、種は大きく育ちます。
