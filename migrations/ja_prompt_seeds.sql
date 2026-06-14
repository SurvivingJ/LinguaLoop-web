-- ja_prompt_seeds.sql — Japanese (language_id=3) prompt_templates seeds.
-- Source of truth: wiki/features/exercise-generation-v2.md §6.6.
-- TASK-508 (Exercise Generation v2, Phase 0).
--
-- Seeds every prompt_templates row JA generation needs, structurally cloned from
-- the live ZH (language_id=1) set, all on provider='openrouter',
-- model='qwen/qwen3.7-plus' (the established JA generation model; qwen-max is
-- delisted — do NOT use it). anthropic/claude-sonnet-4-6 is the planned
-- Model-Arena challenger before scale-up (§6.6), seeded later, not here.
--
-- Tasks seeded here (one active v1 JA row each):
--   vocab_prompt1_core, vocab_prompt2_exercises, vocab_prompt3_transforms,
--   ladder_p1_sentence_judge, ladder_l1_distractor_judge,
--   ladder_collocation_judge, ladder_sentence_validity_judge,
--   exercise_sentence_generation
-- Plus: activate the pre-existing cloze_distractor_generation lang=3 v1 row.
--
-- Idempotency: prompt_templates has NO unique (task_name,language_id,version)
-- constraint (only PK on id), so each INSERT is guarded by
-- `WHERE NOT EXISTS (... task_name=? AND language_id=3)`. Re-running is a no-op.
-- get_template_config() selects is_active=true ORDER BY version DESC and requires
-- model+provider non-null; all rows below satisfy that.
--
-- ===========================================================================
-- JA P1 (vocab_prompt1_core) numeric-key OUTPUT SCHEMA — documented per
-- acceptance criterion. Keys map via PROMPT1_KEY_MAP / SENTENCE_KEY_MAP /
-- MORPH_FORM_KEY_MAP in services/vocabulary_ladder/config.py:
--   "1"  pos               (品詞, 日本語ラベル)
--   "2"  semantic_class    (RATIFIED ENUM TOKEN, English:
--                           concrete|abstract|action|property|function|proper —
--                           the JA legacy-label map is empty, so emit the
--                           canonical token directly so normalize_semantic_class
--                           passes it through cleanly)
--   "3"  definition        (語義, 日本語)
--   "4"  primary_collocate (固定連語の相手 or null)
--   "5"  pronunciation     (見出し語のかな読み — "readings"; e.g. "たべる")
--   "6"  ipa               (IPA)
--   "7"  syllable_count    (モーラ数, integer)
--   "8"  sentences[]       each: {"1":文,"2":対象語原文,"3":"corpus"|"generated",
--                           "4":難易度,"5":その文のふりがな(furigana)} — per-sentence
--                           "readings per occurrence"
--   "9"  morphological_forms[] each: {"1":形,"2":ラベル} — for CONCRETE NOUNS the
--                           COUNTER (助数詞) appears here as a form with label
--                           "助数詞" (the JA analogue of ZH rule 18's measure word)
--   "10" register          (KEIGO level → dim_word_senses.register:
--                           plain|polite|honorific|humble|formal|casual)
--   "11" sense_fingerprint (義項指紋, 日本語)
-- ===========================================================================


-- ---------------------------------------------------------------------------
-- 1. vocab_prompt1_core (JA)
-- ---------------------------------------------------------------------------
INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'vocab_prompt1_core', 3, 1, true, 'openrouter', 'qwen/qwen3.7-plus',
       'JA P1 core asset generator (TASK-508) — cloned from ZH P1 with keigo register, per-sentence furigana, and 助数詞 counter additions',
$t$役割：あなたは日本語の語彙学習者向けに基礎言語素材を生成する、専門の計算言語学者です。

対象語：{word}
既存の語義：{existing_definition}
義項番号（任意）：{sense_id}
義項の語義（任意）：{sense_definition}
学習者レベル：{complexity_tier}

承認済みコーパス例文（そのまま使用し、変更しないこと）：
{corpus_sentences_json}

課題：この語の「一つの義項」についてのみ、基礎言語素材を生成してください。

学習者レベル較正（必ず遵守）
{complexity_tier} を以下の厳格な制約に対応させます。学習者向けに生成するテキストはこれを超えてはいけません。

| レベル | 名称 | 年齢の目安 | 文の最大長（かな・漢字） | 文法の上限 | 主題 / 語域 | 抽象表現 |
|------|------|---------|----------------------|---------|-----------|---------|
| T1 | 幼児 | 4–5歳 | 10字 | 常体（plain）、主語＋述語、活用は辞書形・ます形まで | 家・動物・食べ物・具体的動作 | 禁止 |
| T2 | 小学生 | 8–9歳 | 16字 | 丁寧体（です・ます）＋過去形（た形） | 学校・家族・趣味・身近な場所 | 禁止 |
| T3 | 中学生 | 13–14歳 | 22字 | て形・ている・可能形、簡単な助詞の対比 | 感情・意見・社会的な活動 | ごく少し |
| T4 | 高校生 | 16–17歳 | 30字 | 受身・使役・条件（ば／たら／と／なら） | 学術・メディア・抽象的社会問題 | 可 |
| T5 | 大学生 | 19–21歳 | 40字 | 複文・連体修飾節・敬語（尊敬／謙譲） | 大学・職業・技術 | 想定内 |
| T6 | 教養ある成人 | 30歳以上 | 上限なし | あらゆる構造、文語・専門的含蓄を含む | 技術・文学・高度に繊細 | 全領域 |

厳格なルール：
1. すべての出力値は日本語で記述し、英語を混ぜないこと（IPA フィールドの音声記号、および semantic_class の規定トークンを除く）。
2. 有効な JSON のみを出力し、キーは数字文字列を使うこと。
3. 品詞（"1"）は次のいずれかを返す：
   名詞、動詞、い形容詞、な形容詞、副詞、助詞、助動詞、接続詞、代名詞、連体詞、感動詞、接頭辞、接尾辞。
4. 意味類（"2"）は、下流ルーティングのため次の「規定トークン（英語）」のいずれかをそのまま返す：
   concrete（具体名詞）、abstract（抽象名詞）、action（動作動詞）、property（性質・形容）、function（機能語）、proper（固有名詞）。
   日本語ではなく、この英語トークンをそのまま出力すること。
5. 義項の固定：
   - 一つの義項についてのみ素材を生成する。
   - {sense_id} または {sense_definition} が与えられていれば、その義項に固定する。
   - そうでなければ承認済み例文から推定する。例文が複数義項を含む場合は多数派の義項を採用し、すべての生成内容をそれに一致させる。
6. 学習者レベルに適した語義（日本語）を返す：
   - {existing_definition} が選んだ義項とレベルに十分正確ならそのまま使う。
   - そうでなければ同一義項を保ちつつ、より簡潔・正確に書き直す。
7. （対象語，連語相手）が「固定連語（コロケーション）」を成す場合にのみ、主要連語相手（"4"）を返す。固定連語とは：
   - 相手語を類義語に置き換えると、多くの文脈で不自然になる（例：「水を飲む」→「水を吸う」は不自然）。
   - その語対の共起頻度が偶然をはるかに超える。
   単に同じ主題領域で頻出するだけでは不十分。確信が持てなければ null を返すこと。誤判定は下流の練習を汚染する。
8. 語域（"10"，敬語レベル）は次のいずれかを返す：
   plain（常体・タメ口）、polite（丁寧・です/ます）、honorific（尊敬語）、humble（謙譲語）、formal（書き言葉・硬い）、casual（くだけた話し言葉）。
   この語義が最も自然に用いられる語域を選ぶ。
9. 例文（"8"）は合計でちょうど 10 文返す：
   - 与えられたコーパス例文はそのまま使う。
   - さらにちょうど {sentences_needed} 文を生成し、合計を 10 にする。
10. 10 文すべてが：
   - 同一の義項を表し、
   - 学習者レベルの文長・文法の上限を守り、
   - ルール 8 で決めた語域に従うこと。
11. 統語的多様性：
   - 10 文の中で、対象語は少なくとも 3 種類の異なる統語的役割・構造で現れること（例：述語、連体修飾、主語／目的語、受身・使役の中など）。
   - 同一構造は最大 4 回まで。
12. 各例文について、その文に実際に現れた対象語の文字列（"2"）を返す。
   - {word} と完全に一致する形で連続して現れること。
   - 活用する語の場合、活用形が現れてよいが、語幹が対象語と一致すること。
13. 義項マッチ審査（必須・英語版の「全単語審査」に相当）：
   - 出力前に各文を確認する：対象語が {word} の表記で現れ、その文中の統語／意味役割が固定した義項と一致すること。
   - 反例（却下して書き直す）：対象語が複合語や別語の一部として埋め込まれ、単独の語として当該義項を担っていない。
   - 反例：同形異義（漢字は同じだが別の読み・別義）。
   - 合格：対象語が独立した語として、固定した義項どおりに機能している。
14. 連語カバレッジ（主要連語相手が null でない場合のみ）：
   - 10 文のうち少なくとも 1 文は、主要連語相手を独立した語として対象語と同時に含むこと。
   - 下流の練習に余地を持たせるため 2–3 文に入れるとよい。
   - レベル制約内で自然に書けない場合は主要連語相手を null にする。
15. 読み（"5"）：見出し語のかな読みをひらがなで返す（例：「たべる」「がっこう」）。
16. ふりがな（各例文の "5"）：その文に含まれる漢字語の読みをひらがなで返す（語ごとにスペース区切り、または対象語のふりがなのみでも可）。漢字がない文は空文字列でよい。
17. IPA（"6"）：広い音声表記を返す。確信がなければ簡略でよい。
18. モーラ数（"7"）：整数。見出し語のモーラ（拍）数（例：「がっこう」=4、促音・長音も 1 拍）。
19. 形態変化形（"9"）：3–5 項を返す（該当なしなら空配列）。各項のラベルは次のいずれか：
    - 助数詞：具体名詞に対し、その名詞を数える際の助数詞（例：本→「冊」、紙→「枚」、人→「人(にん)」）。ZH のルール 18（量詞）に相当する JA の追加。
    - 活用：その動詞・形容詞の主要活用形（例：「食べる」→「食べた／食べて／食べない／食べられる」）。
    - 派生：その語が作る派生・複合（例：「考える」→「考え／考え方」）。
    - 敬語形：尊敬・謙譲の対応形（例：「食べる」→「召し上がる／いただく」）。
20. 義項指紋（"11"）：下流プロンプト用に、選んだ義項を一意に識別する短い日本語文字列。
    形式："[品詞] | [10–18字の義項概要]"
21. 出力前の自己点検：
    - JSON が有効か。
    - 例文がちょうど 10 文か。
    - 各文がレベル制約（文長・文法・語域）を満たすか。
    - 各文が義項マッチ審査（ルール 13）を通るか。
    - 主要連語相手が null でなければ、少なくとも 1 文が対象語と連語相手を同時に含むか。

出力スキーマ：
"1" = 品詞（文字列）
"2" = 意味類（規定トークン：concrete/abstract/action/property/function/proper）
"3" = 語義（文字列、日本語）
"4" = 主要連語相手（文字列または null）— null が既定。ルール 7 を満たす場合のみ文字列。
"5" = 読み（文字列、ひらがな）
"6" = IPA（文字列）
"7" = モーラ数（整数）
"8" = 例文オブジェクト配列。各項：
      "1": 完全な文（文字列），"2": 対象語の原文（文字列），"3": 出所（"corpus" または "generated"），"4": 難易度（文字列），"5": ふりがな（文字列、漢字がなければ ""）
"9" = 形態変化形配列。各項：
      "1": 形（文字列），"2": ラベル（文字列、助数詞/活用/派生/敬語形）
"10" = 語域（plain/polite/honorific/humble/formal/casual）
"11" = 義項指紋（文字列、日本語）

JSON のみを返すこと。他のテキストは返さず、コードブロックも使わないこと。$t$
WHERE NOT EXISTS (
    SELECT 1 FROM prompt_templates WHERE task_name='vocab_prompt1_core' AND language_id=3
);


-- ---------------------------------------------------------------------------
-- 2. vocab_prompt2_exercises (JA)
-- ---------------------------------------------------------------------------
INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'vocab_prompt2_exercises', 3, 1, true, 'openrouter', 'qwen/qwen3.7-plus',
       'JA P2 exercise generator (TASK-508) — L1 (listening, audio-confusable distractors) / L3 / L5 / L6',
$t$役割：あなたは日本語の語彙学習者向けに練習問題を生成する、専門の計算言語学者です。

対象語：{word}
品詞：{pos}
意味類：{semantic_class}
学習者レベル：{complexity_tier}
語義：{definition}
主要連語相手：{primary_collocate}

基礎例文：
{sentences_json}

次に挙げる練習レベルのみを生成する：{active_levels_json}

共通ルール：
1. すべての出力値は日本語で記述し、英語を混ぜないこと。
2. 有効な JSON のみを出力し、キーは数字文字列を使う。
3. 各選択肢の形式："1" = 選択肢テキスト，"2" = 真/偽（正解かどうか、JSON の真偽値 true/false），"3" = 短い教育的解説（日本語）。
4. 解説は短く・明確で、教育的価値のあるものにする。
5. 対象語は一つの完全な語として扱う。L3・L5・L6 において、ディストラクターや代替文中の対象語は、固定した義項と同じ統語／意味役割を担うこと（対象語の文字を別語の断片として使ってはいけない。P1 ルール 13 参照）。

L1（聞き取り — リスニング練習）：
- 場面：学習者は対象語の「音声」を聞き、4 つの書記選択肢から正しい表記を選ぶ。
- 4 つの選択肢を返す。1 つが正解 = 対象語、3 つがディストラクター。
- ディストラクターは「聴覚的に紛らわしい」語でなければならない（視覚的に似ているだけの語は禁止）。次の音声的混同を優先：
  - 長短母音の対立（例：「おばさん」↔「おばあさん」、「ビル」↔「ビール」）。
  - 清濁の対立（濁点・半濁点。例：「かす」↔「がす」、「はし」↔「ばし」）。
  - 促音・撥音の有無（例：「きて」↔「きって」、「かこ」↔「かんこ」）。
  - 高低アクセントのみが異なる同音語（例：「はし(箸)」↔「はし(橋)」）。
- ディストラクターはすべて実在する語で、対象語の同義語であってはならない。
- 表記だけが似て読みが異なる語（聴覚で区別できてしまう形近語）は使わないこと（これはリスニング練習を壊す）。
- 解説："2"=false の各項について、対象語と「音のどこが」紛らわしいか（長音・濁音・促音・アクセント等）を述べる。

L3（文脈穴埋め）：
- 文インデックス {level_3_sentence_index} の文を使う。
- 正解 = その文に現れた対象語の形（その文の文字列と完全一致）。
- ディストラクター 3 つ：品詞が同じで、文法的にはその空所に入りうるが、意味／文脈上は不適切な語。
- 対象語の同音・近音語は使わない（音の混同は L1 に任せる）。
- 各ディストラクターはルール 5 の義項／役割一致を満たすこと。
- 必須の項目別自己点検（各ディストラクターを出す前に）：
  (a) 失効次元 — 各ディストラクターに、その文で失効する理由を次の 5 類から一つだけ付す：
        - "意味"   : 指す概念・カテゴリーが誤り
        - "連語"   : 周囲の語との結びつきが不自然
        - "アスペクト" : テンス・アスペクト（た／ている／てある等）が不整合
        - "語域"   : 丁寧度・領域・社会的場面がその文に不適合
        - "項構造" : 自他・格助詞・補語の取り方が誤り
      このラベルを選択肢 "3"（解説）の先頭に付す。例："意味：……"。
  (b) 置換監査 — 対象語をその一般的な類義語に心の中で置き換え、その上で問う：その類義語に替えたとき、このディストラクターは正解になりうるか？ なるなら直ちに却下して別のものに替える。
- 3 つのディストラクターは少なくとも 2 つの異なる失効次元をカバーすること。
- 最終点検：各ディストラクターを空所に入れて音読する。自然に通る項があれば直ちに差し替える。

L5（連語穴埋め）— 含まれる場合のみ生成：
- 文インデックス {level_5_sentence_index} の文を使う。
- 正解 = 主要連語相手（その文に連語として現れる）。
- ディストラクター 3 つ：正解の連語相手と品詞が同じで意味も近いが、対象語と結びつくと不自然になるか義項が変わる語。
- 解説：連語相手と対象語の固定的関係を指摘する。

L6（意味弁別）：
- 文インデックス {level_6_sentence_index} の文を正しい文として使う。
- 新たに 3 文を生成する。各文は対象語を使い、文法的には正しいが、意味／語用／連語の上で不自然または誤りであるようにする。誤り型は次から選ぶ（各文できるだけ別の型を）：
  - 助数詞の誤り（名詞類の対象語向け。例：「一冊の犬」→ 正しくは「一匹の犬」）；
  - 助詞の混同（は／が、に／で、を／が 等の取り違え）；
  - 活用・アスペクトの誤り（た／ている／てある 等の選択・位置の誤り）；
  - 語順・係り受けの誤り（時の副詞句の位置、主題—解説構造の破壊）。
- 各誤り文は対象語 {word} を含み、ルール 5 の義項／役割一致を満たすこと（誤りは他の構造層にある）。
- フィールド："1": テキスト，"2": 解説（具体的な誤り型と理由を指摘）。

出力スキーマ：
最上位キーはレベル番号の文字列。
L1 / L3 / L5 の値は 4 つの選択肢オブジェクト配列：[{"1": テキスト, "2": 真/偽, "3": 解説}, ...]
L6 の値は：{"1": 正しい文のインデックス, "2": [3 つの誤り文オブジェクト {"1": テキスト, "2": 解説}]}

JSON のみを返すこと。コードブロックは使わないこと。$t$
WHERE NOT EXISTS (
    SELECT 1 FROM prompt_templates WHERE task_name='vocab_prompt2_exercises' AND language_id=3
);


-- ---------------------------------------------------------------------------
-- 3. vocab_prompt3_transforms (JA)
-- ---------------------------------------------------------------------------
INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'vocab_prompt3_transforms', 3, 1, true, 'openrouter', 'qwen/qwen3.7-plus',
       'JA P3 structure/grammar generator (TASK-508) — L4 (conjugation/particle slot) / L7 / L8',
$t$役割：あなたは日本語の語彙学習者向けに構造・文法練習を生成する、専門の計算言語学者です。

対象語：{word}
品詞：{pos}
意味類：{semantic_class}
学習者レベル：{complexity_tier}
主要連語相手：{primary_collocate}

基礎例文：
{sentences_json}

利用可能な形態変化形：
{morphological_forms_json}

次に挙げる練習レベルのみを生成する：{active_levels_json}

共通ルール：
1. すべての出力値は日本語で記述し、英語を混ぜないこと。
2. 有効な JSON のみを出力し、キーは数字文字列を使う。
3. 各選択肢の形式："1" = 選択肢テキスト，"2" = 真/偽（JSON 真偽値 true/false），"3" = 短い教育的解説（日本語）。
4. 対象語の文字は、すべての文・選択肢で固定した義項と同じ統語／意味役割を担うこと（P1 ルール 13 参照）。

L4（形態スロット — 活用形・接辞・助数詞の選択）：
- 文インデックス {level_4_sentence_index} の文を使う。その文は対象語の「活用形」または対象語を伴う固定的な形態（助数詞＋名詞など）を含むこと。
- その形態の一部（活用語尾、または名詞を数える助数詞）を空所にし、正解 = 原文での形。
- ディストラクター 3 つ：置き換えると実在の形にはなるが、その文脈では不適切なもの。
  - 動詞・形容詞の対象語：正解の活用形に対し、別の活用形（時制・態・アスペクト違い。例：正解「食べた」、ディストラクター「食べる／食べて／食べられた」）。
  - 具体名詞の対象語：正解の助数詞に対し、別の実在の助数詞（例：正解「冊」、ディストラクター「枚／本／個」）。
- フィールド：4 つの選択肢配列に加え、"4": 基本形（対象語またはその形態），"5": 形式ラベル（形態変化形より。例「活用」「助数詞」），"6": 文インデックス。
- 対象語とその形態変化形がこの練習を支えられない場合（純粋な助詞・感動詞など）は null を返す（描画層が L4 をスキップする）。

L7（誤った文を見つける）：
- {level_7_correct_indices} のインデックスの文を 3 つの正しい文として使う。
- 新たに誤り文を 1 つ生成する：対象語を含み、学習者がよく犯す明確な構造的誤りを「一つだけ」持つ。誤り型は次から選ぶ：
  - 助数詞の誤り（例：「一匹の本」）；
  - 助詞の混同（は／が、に／で、へ／に、を／が）；
  - 活用・アスペクトの誤り（た／ている／てある の選択・位置）；
  - 語順・係り受けの誤り。
- 誤りはレベル {complexity_tier} の母語話者が即座に気づける程度であること（隠れすぎ・母語話者も迷う誤りは不可）。
- フィールド："1": 誤り文（文字列），"2": 正しい文（文字列），"3": 誤りの説明（誤り型と正しい形を日本語で），"4": 正しい文のインデックス配列。

L8（連語修復）— 含まれる場合のみ生成：

学習者が特定の文脈で「{word}」の自然な連語相手を知っているかを試す選択問題を作る。

元の文（文インデックス {level_8_sentence_index}）：
  「{level_8_sentence_text}」

この文での「{word}」の自然で正しい連語相手はちょうど：
  「{level_8_collocate_word}」

4 つの選択肢を提示する：
  - 選択肢 1（正解）：テキストは「{level_8_collocate_word}」と文字レベルで完全一致。"2": true。
  - 選択肢 2・3・4（ディストラクター）：あなたが生成する 3 つの異なる語。各ディストラクターは：
      * 「{level_8_collocate_word}」と品詞が同じ；
      * 学習者にとってもっともらしい（荒唐無稽でない）；
      * この文脈で「{word}」と結びつくと不自然；
      * 同義語であってはならない（別の成立する自然な連語であってはならない）。
    "2": false。

各選択肢の "3" は短い教育的解説（日本語）：
  - 正解：「{word}」＋「{level_8_collocate_word}」がなぜここで自然な連語かを説明。
  - 各ディストラクター：「{word}」とこの文脈でなぜ不自然かを具体的に述べる。

L8 厳格ルール：
- 選択肢 1 のテキストは「{level_8_collocate_word}」と文字レベルで完全一致。
- ちょうど 1 つの選択肢が "2": true、残り 3 つが "2": false。
- 「{level_8_collocate_word}」と完全に同じディストラクターを返さないこと。

出力スキーマ：
最上位キーはレベル番号の文字列。
L4：4 つの選択肢配列 + "4": 基本形 + "5": 形式ラベル + "6": 文インデックス（支えられない場合は null）
L7：{"1": 誤り文, "2": 正しい文, "3": 誤りの説明, "4": [正しい文のインデックス配列]}
L8：4 つの選択肢配列 + "4": 文インデックス + "5": 誤った連語語（あなたが生成したディストラクターの一つ）

JSON のみを返すこと。コードブロックは使わないこと。$t$
WHERE NOT EXISTS (
    SELECT 1 FROM prompt_templates WHERE task_name='vocab_prompt3_transforms' AND language_id=3
);


-- ---------------------------------------------------------------------------
-- 4. ladder_p1_sentence_judge (JA)
-- ---------------------------------------------------------------------------
INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'ladder_p1_sentence_judge', 3, 1, true, 'openrouter', 'qwen/qwen3.7-plus',
       'JA P1 sentence corpus judge (TASK-508) — sense-match / keigo register / whole-word',
$t$あなたは日本語語彙コースの厳格なコーパス編集者です。生成器がある対象語の特定の一義項について基礎例文を産出しました。すべての下流練習がこれらの文を再利用するため、欠陥のある文は多くの練習を汚染します。文ごとに採点してください。

対象語：{lemma}
固定義項（教えている唯一の義項）：{definition}
義項指紋（曖昧さ解消のための語義／典型連語）：{sense_fingerprint}
宣言された語域（敬語レベル）：{register}

文：
{sentences_numbered}

上記の固定義項について、3 つの観点で各文を評価する：
1. 義項マッチ — 文中の対象語が固定義項を担い、同形異義や別義になっていないこと。（例：義項が「はかる＝計測する」なのに「諮る／謀る」の意で使われていれば不合格。）
2. 語域 — 文の丁寧度・文体が宣言された語域（plain/polite/honorific/humble/formal/casual）と一致すること。明らかに丁寧すぎる／くだけすぎは部分的不合格。
3. 全単語／全義 — 対象語が当該義項の統語役割を担う完全な語として現れること。より長い語の文字断片であってはならず、義項を変える慣用句に取り込まれてもいけない。

各文を 1–5 で採点：
5 ＝ 3 観点すべて clean、理想的な教育文。
4 ＝ 義項正しく全単語で現れ、軽微な語域のずれのみ。
3 ＝ 使えるが弱い：語域が境界、やや不自然、または義項は正しいがやや曖昧。
2 ＝ 義項が誤り、対象語が全単語／全義で現れない、または明確な語域逸脱。
1 ＝ 使用不可：義項誤り、非文法的、対象語欠落、または対象語を実際に使っていない。

JSON のみを返す。1 始まりの文番号をキーとし、各値は整数 "rating"（1–5）と短い "reason"（15字以内、失敗観点を指摘するか "clean" と記す）のオブジェクト：
{"1": {"rating": 5, "reason": "clean"}, "2": {"rating": 2, "reason": "義項：別義で使用"}}

すべての文を採点する。JSON 以外のテキストは出力せず、コードブロックも使わないこと。$t$
WHERE NOT EXISTS (
    SELECT 1 FROM prompt_templates WHERE task_name='ladder_p1_sentence_judge' AND language_id=3
);


-- ---------------------------------------------------------------------------
-- 5. ladder_l1_distractor_judge (JA) — audio confusability
-- ---------------------------------------------------------------------------
INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'ladder_l1_distractor_judge', 3, 1, true, 'openrouter', 'qwen/qwen3.7-plus',
       'JA L1 listening-distractor judge (TASK-508) — keep only audio-confusable distractors',
$t$あなたは「聞き取り」語彙練習の厳格な評価者です。学習者は対象語の音声を聞き、4 つの書記選択肢から正しい表記を選びます。3 つのディストラクターは実在する語で、対象語と「聴覚的に」紛らわしく（長短母音・清濁・促音撥音・高低アクセントの差）、意味は異なる必要があります。各候補ディストラクターを項目ごとに判定してください。

対象語（音声）：{target}
候補ディストラクター：
{distractors_numbered}

各ディストラクターについて判定する：
- "keep" ＝ 実在する語で、対象語と聴覚的に確かに混同しうる（長短母音の対立、清濁の対立、促音・撥音の有無、または高低アクセントのみの差という最小対立）。かつ対象語の同義語でない。
- "reject" ＝ 次のいずれかに該当：
  * 実在しない語；
  * 対象語の同義語・類義語（音を聞いた学習者が合理的に選びうる）；
  * 表記だけが似て読みが異なる語（純粋な形近語 — 聴覚で区別でき、リスニング練習を壊す）；
  * 対象語と完全に同音同アクセント（聴覚で区別不能）、または対象語そのもの；
  * 表記でも読みでも無関係。

厳しく判定すること：聴覚で区別できないディストラクターは無意味。両者が聴覚的に混同しうるか確信が持てなければ reject。

JSON のみを返す。1 始まりのインデックスをキーとし、各値は {"verdict": "keep|reject", "reason": "12字以内"}：
{"1": {"verdict": "keep", "reason": "長音差：ビル/ビール"}, "2": {"verdict": "reject", "reason": "対象語の同義語"}, "3": {"verdict": "reject", "reason": "形近だが読み別"}}

JSON 以外のテキストは出力せず、コードブロックも使わないこと。$t$
WHERE NOT EXISTS (
    SELECT 1 FROM prompt_templates WHERE task_name='ladder_l1_distractor_judge' AND language_id=3
);


-- ---------------------------------------------------------------------------
-- 6. ladder_collocation_judge (JA)
-- ---------------------------------------------------------------------------
INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'ladder_collocation_judge', 3, 1, true, 'openrouter', 'qwen/qwen3.7-plus',
       'JA collocation judge (TASK-508) — rate how clearly a candidate is a NON-collocate',
$t$あなたは日本語の「連語（コロケーション）」の厳格な評価者です。下の文では、対象語が連語相手と組んで空所に入ります。正しい連語相手は与えられています。各候補について、それが対象語とこの文で自然で地道な連語を成すか、それとも明らかに連語にならない（対象語と組むと不自然・誤り）かを判定してください。

文：{sentence}
対象語：{target}
正しい連語相手（既定の答え）：{correct_collocate}
候補：
{candidates_numbered}

各候補について、この文で対象語の「非連語」としてどれだけ明確か — すなわち「候補＋対象語」が母語話者にとってどれだけ明らかに不自然・誤りか — を 1–5 で評価する：
5 ＝ 明らかに連語にならない；組み合わせが明白に不自然・誤り（理想的な誤答選択肢）。
4 ＝ おそらく連語にならない；不自然だが荒唐無稽ではない。
3 ＝ 境界；どちらとも言える。
2 ＝ おそらく許容される連語；母語話者も使うかもしれない（別の正解の可能性）。
1 ＝ 対象語と完全に地道・自然な連語で、既定の答えと同様に正しく、誤答選択肢にしてはならない。

文法だけでなく「連語として自然か」を判定する：文法的に正しくても 5（連語不自然）になりうる。動詞と格助詞の結びつき、動詞のアスペクト（た／ている）、サ変名詞＋する、慣用的結合の固さに特に注意する。ある一般的な相手語が許容されるか確信が持てなければ低く（1–2）評価する — 境界の誤答を一つ捨てる方が、実は正しい選択肢を見逃すよりよい。

JSON のみを返す。1 始まりのインデックスをキーとし、各値は {"rating": <1-5>, "reason": "12字以内"}：
{"1": {"rating": 5, "reason": "連語が不自然"}, "2": {"rating": 1, "reason": "これも地道な連語"}}

JSON 以外のテキストは出力せず、コードブロックも使わないこと。$t$
WHERE NOT EXISTS (
    SELECT 1 FROM prompt_templates WHERE task_name='ladder_collocation_judge' AND language_id=3
);


-- ---------------------------------------------------------------------------
-- 7. ladder_sentence_validity_judge (JA)
-- ---------------------------------------------------------------------------
INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'ladder_sentence_validity_judge', 3, 1, true, 'openrouter', 'qwen/qwen3.7-plus',
       'JA sentence-validity judge (TASK-508) — error must match its annotated reason',
$t$あなたは語彙練習の厳格な評価者です。この練習は、正しい文と意図的に誤らせた文を学習者に区別させます。生成器が産出した各文は、特定の注記された理由により誤っているべきです。あなたの課題：各文が「注記された理由によってのみ」誤っているかを文ごとに判定すること。

対象語：{target}

文（誤っているべき理由つき）：
{pairs_numbered}

各文について、注記された理由によって誤っている「clean さ」を 1–5 で評価する：
5 ＝ 明白に誤りで、まさに注記された理由により誤っている — 理想的な誤り文。
4 ＝ 注記された理由により誤っているが、ごく軽微な疑問あり。
3 ＝ 境界 — 誤りとも許容ともとれる。
2 ＝ 確かに誤りだが、誤因が注記と異なる（例：注記は活用誤りだが実際は助詞誤り）。学習者に示す解説が誤解を招く。
1 ＝ 実際には文法的で自然に許容される — 誤っておらず、誤り文に使えない。

母語話者がその文を許容する場合、または真の欠陥が注記された理由と異なる場合は、必ず低く（1–2）評価する。注記された理由（助数詞、助詞の混同、活用・アスペクト た／ている／てある、語順、長短母音など）について具体的に判定し、全体の座りの悪さだけで判断しないこと。

JSON のみを返す。1 始まりのインデックスをキーとし、各値は {"rating": <1-5>, "reason": "15字以内"}：
{"1": {"rating": 5, "reason": "助数詞誤り、注記と一致"}, "2": {"rating": 1, "reason": "文は完全に文法的"}}

すべての文を採点する。JSON 以外のテキストは出力せず、コードブロックも使わないこと。$t$
WHERE NOT EXISTS (
    SELECT 1 FROM prompt_templates WHERE task_name='ladder_sentence_validity_judge' AND language_id=3
);


-- ---------------------------------------------------------------------------
-- 8. exercise_sentence_generation (JA)
-- ---------------------------------------------------------------------------
INSERT INTO prompt_templates (task_name, language_id, version, is_active, provider, model, description, template_text)
SELECT 'exercise_sentence_generation', 3, 1, true, 'openrouter', 'qwen/qwen3.7-plus',
       'JA grammar-pattern sentence generator (TASK-508) — cloned from ZH lang=1 v1',
$t$目標言語（日本語）で、次を示す自然な {complexity_tier} レベルの文を {count} 文生成してください：
文型：{pattern_code}
説明：{description}
例：{example_sentence}


JSON オブジェクトの配列を返す：[{"sentence": "...", "cefr_level": "{complexity_tier}"}]
翻訳は含めないこと。文は文法的に正しく、文脈的に自然であること。$t$
WHERE NOT EXISTS (
    SELECT 1 FROM prompt_templates WHERE task_name='exercise_sentence_generation' AND language_id=3
);


-- ---------------------------------------------------------------------------
-- 9. Activate the pre-existing JA cloze_distractor_generation row (already a
--    complete JA template on qwen/qwen3.7-plus; was seeded inactive).
-- ---------------------------------------------------------------------------
UPDATE prompt_templates
   SET is_active = true, updated_at = now()
 WHERE task_name = 'cloze_distractor_generation'
   AND language_id = 3
   AND is_active = false;
