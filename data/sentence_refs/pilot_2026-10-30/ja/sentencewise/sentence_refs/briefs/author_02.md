# Author brief 02 — ja -> en, arm `sentencewise`

Read `data/sentence_refs/pilot_2026-10-30/ja/sentencewise/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/pilot_2026-10-30/ja/sentencewise/sentence_refs/docs/<test_id>.en.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/pilot_2026-10-30/ja/sentencewise --tests 520baddb-75c0-4429-9ec1-306ddce0e998,7e1103fb-5935-4c36-9ba0-f1a70266e51c,309431d5-5c6f-4af1-bbf2-c0b6f877f093,9b8ceffb-a291-43f3-97df-302077de7c46,c9616207-3e2c-445c-ac82-929257157fdf,c79c4b8e-9cfe-46bb-af84-b04ec84c67f8`
and fix until every test is `ok`.

## 520baddb-75c0-4429-9ec1-306ddce0e998 — 体の一部をあげよう

Passage (for context, do not translate as a block unless the arm says so):

お医者さんが、病気の人の体に、他の人の体の一部を入れる医療の手順があります。これは移植です。病気を治すために、他の人が提供します。

Sentences:

- idx 0: お医者さんが、病気の人の体に、他の人の体の一部を入れる医療の手順があります。
- idx 1: これは移植です。
- idx 2: 病気を治すために、他の人が提供します。

## 7e1103fb-5935-4c36-9ba0-f1a70266e51c — からだにぴったりのくすり

Passage (for context, do not translate as a block unless the arm says so):

病院での薬の選び方は、昔と今で違います。昔はみんな同じ薬です。今は一人一人の体に合う薬です。医者は体を調べて薬を決めます。

Sentences:

- idx 0: 病院での薬の選び方は、昔と今で違います。
- idx 1: 昔はみんな同じ薬です。
- idx 2: 今は一人一人の体に合う薬です。
- idx 3: 医者は体を調べて薬を決めます。

## 309431d5-5c6f-4af1-bbf2-c0b6f877f093 — せかいのゲーム

Passage (for context, do not translate as a block unless the arm says so):

私はゲームの世界であそびます。「主権」は私の番です。「国家性」のバッジをつけます。「国際関係」の「外交」をします。

Sentences:

- idx 0: 私はゲームの世界であそびます。
- idx 1: 「主権」は私の番です。
- idx 2: 「国家性」のバッジをつけます。
- idx 3: 「国際関係」の「外交」をします。

## 9b8ceffb-a291-43f3-97df-302077de7c46 — はじめてのステージ

Passage (for context, do not translate as a block unless the arm says so):

十代の人が初めてステージに立ちます。マイクを持って詩を読みます。これはスポークンワードというパフォーマンスです。

Sentences:

- idx 0: 十代の人が初めてステージに立ちます。
- idx 1: マイクを持って詩を読みます。
- idx 2: これはスポークンワードというパフォーマンスです。

## c9616207-3e2c-445c-ac82-929257157fdf — おてがみものがたり

Passage (for context, do not translate as a block unless the arm says so):

手紙の書簡体の物語は、おもしろい小説です。誰が、どこで、何を、なぜ、どのように書くか、その技法が進化します。

Sentences:

- idx 0: 手紙の書簡体の物語は、おもしろい小説です。
- idx 1: 誰が、どこで、何を、なぜ、どのように書くか、その技法が進化します。

## c79c4b8e-9cfe-46bb-af84-b04ec84c67f8 — 汗滴る畑の営み：地域の子供へ紡ぐ農家の静かな情熱

Passage (for context, do not translate as a block unless the arm says so):

経験豊富な農家は、広大な畑の土壌を丁寧に耕し、野菜の種を植える。彼がこれらを大切に育てる理由は、地域の子供たちに安全な給食を安定的に提供するためだ。毎朝の天気予報を確認し、気温や湿度に合わせて水を調整する。過酷な自然環境と向き合いながら、彼は今日も黙々と作業を続け、やがて訪れる豊かな実りの季節を心待ちにしている。汗が滴る中でも、その表情は穏やかだ。

Sentences:

- idx 0: 経験豊富な農家は、広大な畑の土壌を丁寧に耕し、野菜の種を植える。
- idx 1: 彼がこれらを大切に育てる理由は、地域の子供たちに安全な給食を安定的に提供するためだ。
- idx 2: 毎朝の天気予報を確認し、気温や湿度に合わせて水を調整する。
- idx 3: 過酷な自然環境と向き合いながら、彼は今日も黙々と作業を続け、やがて訪れる豊かな実りの季節を心待ちにしている。
- idx 4: 汗が滴る中でも、その表情は穏やかだ。
