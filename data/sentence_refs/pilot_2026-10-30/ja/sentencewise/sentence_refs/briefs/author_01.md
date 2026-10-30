# Author brief 01 — ja -> en, arm `sentencewise`

Read `data/sentence_refs/pilot_2026-10-30/ja/sentencewise/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/pilot_2026-10-30/ja/sentencewise/sentence_refs/docs/<test_id>.en.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/pilot_2026-10-30/ja/sentencewise --tests 4b76f183-7c33-48da-b8e5-ff4d3873f331,b228d2e6-dcee-4718-817e-c86296c179bf,175a0043-c10d-40bb-b45d-e281517e2dc9,073114a4-815c-441f-90a2-7bfa56c6d393,3bc2a517-2f6d-4f2a-a1c4-80b94562b700,29dc5058-f525-4b32-b467-a2fc4e12013c`
and fix until every test is `ok`.

## 4b76f183-7c33-48da-b8e5-ff4d3873f331 — おともだちロボット

Passage (for context, do not translate as a block unless the arm says so):

あたらしいロボットは、おうちでいろいろなてつだいをします。みんなのことばがわかります。これからのともだちになれるでしょうか。

Sentences:

- idx 0: あたらしいロボットは、おうちでいろいろなてつだいをします。
- idx 1: みんなのことばがわかります。
- idx 2: これからのともだちになれるでしょうか。

## b228d2e6-dcee-4718-817e-c86296c179bf — わたしのすきなTシャツ

Passage (for context, do not translate as a block unless the arm says so):

わたしは、うちで青いTシャツをきています。この服はわたしのお気に入りです。くまの絵がすきです。わたしは毎日、このTシャツをきます。

Sentences:

- idx 0: わたしは、うちで青いTシャツをきています。
- idx 1: この服はわたしのお気に入りです。
- idx 2: くまの絵がすきです。
- idx 3: わたしは毎日、このTシャツをきます。

## 175a0043-c10d-40bb-b45d-e281517e2dc9 — ローマの木の馬

Passage (for context, do not translate as a block unless the arm says so):

ローマの子供は、木の馬のおもちゃで楽しい遊びをします。長い紐を引くと、馬は元気に走ります。とても速いです。

Sentences:

- idx 0: ローマの子供は、木の馬のおもちゃで楽しい遊びをします。
- idx 1: 長い紐を引くと、馬は元気に走ります。
- idx 2: とても速いです。

## 073114a4-815c-441f-90a2-7bfa56c6d393 — ながいおしろをつくろう

Passage (for context, do not translate as a block unless the arm says so):

中国には、とてもながい城壁があります。たくさんの人が、いっしょに建設をしています。みんなの町を、しっかり防衛します。

Sentences:

- idx 0: 中国には、とてもながい城壁があります。
- idx 1: たくさんの人が、いっしょに建設をしています。
- idx 2: みんなの町を、しっかり防衛します。

## 3bc2a517-2f6d-4f2a-a1c4-80b94562b700 — ローマのみずのはし

Passage (for context, do not translate as a block unless the arm says so):

ローマの ひとたちは、おおきな まちで たかい はしを つくります。みずを はこぶ ためです。いしを つんで つくります。

Sentences:

- idx 0: ローマの ひとたちは、おおきな まちで たかい はしを つくります。
- idx 1: みずを はこぶ ためです。
- idx 2: いしを つんで つくります。

## 29dc5058-f525-4b32-b467-a2fc4e12013c — スポーツのばんそうこう

Passage (for context, do not translate as a block unless the arm says so):

高校生は学校でスポーツをします。外傷が出ます。救急処置のキットをカバンに入れます。絆創膏も入れます。

Sentences:

- idx 0: 高校生は学校でスポーツをします。
- idx 1: 外傷が出ます。
- idx 2: 救急処置のキットをカバンに入れます。
- idx 3: 絆創膏も入れます。
