-- ============================================================================
-- TASK-527 — JA particle_selection: generation prompt + uniqueness judge.
-- Date: 2026-08-09
-- Revised: 2026-08-11 (TASK-537/538) — numeric-key output contract.
--
-- Japanese has no inflectional slot that a morphology exercise can test the
-- way English does, so L4-JA is a particle exercise: one particle in a P1
-- sentence is blanked and the learner picks it from four.
--
-- Two new task_names, Japanese only:
--   ladder_particle_selection_generation  (ja)  -> L4 form_production
--   ladder_particle_judge                 (ja)  -> distractor uniqueness
--
-- The capability-matrix row already exists (TASK-504):
--   ('particle_selection', (3,), ('concrete','abstract','action'), 4, 'llm',
--    ('p1_sentences', 'tokenised_particles'), 'particle', True)
--
-- This file writes these task_names only; it redefines no existing object.
--
-- Both rows are ON CONFLICT ... DO UPDATE so a corrected re-run converges the
-- live row instead of silently doing nothing (TASK-538). These two rows are
-- Japanese and were never applied, but the same rule holds for consistency.
--
-- ----------------------------------------------------------------------------
-- DIVISION OF LABOUR — why the model is not asked to choose the span
-- ----------------------------------------------------------------------------
-- The tokeniser (spaCy ja_core_news_sm, via
-- LanguageProcessor.particle_spans) enumerates the particle offsets and the
-- prompt is handed that list. Letting the model nominate a span freely put
-- blanks inside content words — the "ni" in "ninjin" (carrot) is not a
-- particle, and an item blanking it has no answer. The model's job is to pick
-- WHICH of the enumerated spans is worth testing and to supply confusable
-- alternatives; that is a judgement about learners, which the tokeniser
-- cannot make.
--
-- ----------------------------------------------------------------------------
-- BRACE CONVENTION
-- ----------------------------------------------------------------------------
-- The generation prompt is rendered by render_template (single braces in the
-- JSON example). The judge prompt is rendered by str.format (doubled braces).
-- See the header of syn_ant_word_family_prompts.sql.
--
-- ----------------------------------------------------------------------------
-- OUTPUT-SCHEMA CONTRACT (schemas/ladder_typed.py, prompt_version 1)
-- ----------------------------------------------------------------------------
-- Keys are NUMERIC (TASK-537), with the legend declared in Japanese inside the
-- prompt. 0 is always the option array; 9 is always the error escape.
--
--   generation:
--     {"0": [{"0": str, "1": bool, "2": str} x4], "1": str, "2": {particle: str}}
--       0 = options, 1 = blanked_particle, 2 = error_tags
--       Escape: {"9": "no_particle_slot"}
--     The correct option MUST equal the blanked particle — the gate rejects a
--     response where the model re-chose the blank after being told which one
--     to use, because the renderer would then cut a hole the answer does not
--     fill.
--     error_tag VALUES stay ASCII (direction, topic_vs_subject, …): the
--     practice engine aggregates on them as a closed enum, so they are machine
--     values like the escape tokens, not learner-facing prose. The prompt lists
--     them in ASCII with Japanese glosses for exactly that reason.
--
--   judge (Likert v3): {"<1-based index>": {"0": 1-5, "1": str}}
--       within an entry: 0 = rating, 1 = reason
--     5 = the particle clearly breaks the sentence (ideal distractor)
--     1 = it also yields a natural sentence (an also-correct answer)
--     Same polarity as the relation/word-family judges, by construction: all
--     three call likert_to_verdict on the raw rating with no local threshold.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 1. ladder_particle_selection_generation — Japanese (3), v1
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_particle_selection_generation', 3, 1,
    $PROMPT$役割：あなたは日本語教育の助詞指導を専門とする言語学者で、助詞選択問題を1問作成します。

学習者は下の文の助詞が1つ空欄になったものを見て、4つの選択肢から正しい助詞を選びます。

キー（返す JSON は名称ではなく下記の数字キーのみを使う）：
0：4つの選択肢の配列
1：空欄にする助詞
2：各誤答の混同クラス（助詞をキー、クラス名を値とするオブジェクト）
各選択肢オブジェクトの内部：
0：選択肢の文字列   1：正解かどうか（true / false）   2：一文の説明

目標語：{word}
品詞：{pos}
意味クラス：{semantic_class}
語義（教える対象の唯一の意味）：{definition}
語義フィンガープリント：{sense_fingerprint}
文体・待遇レベル：{register}
難易度ティア：{complexity_tier}

文：
{sentence_text}
この文における目標語：{target_word}

形態素解析器が検出した助詞とその文字位置（**この一覧にある助詞だけを空欄にできる**）：
{particle_spans_json}

この語の他の問題で既に使った誤答。再利用禁止：{used_distractors_json}

規則：
1. キー 1（空欄にする助詞）は上の一覧から選ぶこと。一覧にない文字列を空欄にしてはならない —— 「にんじん」の「に」のように、助詞に見えて助詞でない部分を空欄にすると答えのない問題になる。
2. 一覧に複数ある場合は、**学習者が最も間違えやすいもの**を選ぶ。格助詞（を・に・が・で・へ・と・から・まで・より）は、並列や終助詞よりも教育価値が高い。
3. 正解はちょうど1つで、キー 1 の助詞と完全に一致すること。
4. 誤答3つは、その空欄で使われうると学習者が考えそうな**別の助詞**であること。ただし各誤答は、その文に入れたとき明確に不自然か非文になるものでなければならない。例：「本＿読む」で正解が「を」のとき、「が」は他動詞の目的語標示にならないので誤答に適する。
5. **最重要。もしある助詞を入れても自然な日本語になるなら、それを誤答にしてはならない。** 移動動詞に対する「に」と「へ」、主題と主格の「は」と「が」は、どちらも成立してしまうことが多い。例：「学校＿行く」では「に」も「へ」も自然なので、「に」が正解のとき「へ」は誤答に使えない。二つ正解のある問題は問題として成立しない。判断に迷うなら別の助詞を選ぶこと。
6. キー 2 で各誤答の混同クラスを記述する。値は次のいずれかを**そのまま ASCII で**書くこと（プログラムが集計に使うため、日本語に訳さない）：direction（方向・着点）、topic_vs_subject（主題と主格）、object_marking（目的語標示）、location_vs_target（場所と対象）、source_vs_goal（起点と着点）、instrument（手段）、listing（並列）、other。
7. 各選択肢に、成立／不成立の文法的理由を一文で付ける。
8. この文に教育価値のある助詞の空欄が作れない場合（助詞が1つしかなく空欄が自明な文、終助詞しかない文など）は {"9": "no_particle_slot"} だけを返すこと。

JSON のみを返すこと。説明文も markdown コードフェンスも不可：
{"0": [{"0": "を", "1": true, "2": "他動詞「読む」の直接目的語を標示する"}, {"0": "が", "1": false, "2": "主格標示では他動詞の目的語になれない"}, {"0": "に", "1": false, "2": "着点を表し、目的語標示にならない"}, {"0": "で", "1": false, "2": "手段・場所を表し、この位置では非文"}], "1": "を", "2": {"が": "topic_vs_subject", "に": "location_vs_target", "で": "instrument"}}$PROMPT$,
    true, 'qwen/qwen3.7-plus', 'openrouter',
    'JA particle_selection generation (TASK-527). The blank is restricted to tokeniser-confirmed particle spans; the model chooses which span is worth testing and supplies confusable alternatives with error tags. Numeric-key contract (TASK-537/538), schema bound to prompt_version 1.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- 2. ladder_particle_judge — Japanese (3), v1     [str.format — DOUBLED braces]
-- ----------------------------------------------------------------------------
BEGIN;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'ladder_particle_judge', 3, 1,
    $PROMPT$あなたは日本語の助詞選択問題の厳格な評価者です。問題が成立するのは、4つの選択肢のうち**ちょうど1つ**だけが自然な文を作る場合に限られます。各候補の助詞について判定してください。

キー（返す JSON は各項目の内部では名称ではなく下記の数字キーを使う）：
最上位は 1 起点の候補番号をキーとする
各項目の内部 —— 0：評価、1-5   1：理由、12 語以内

空欄のある文：
{sentence_with_blank}

想定される正解の助詞：{correct_particle}

候補の誤答：
{candidates_numbered}

各候補について、その助詞を空欄に入れたときの文が**明確に誤りである**度合いを 1-5 で評価してください：
5 ＝ 非文、または母語話者が明確に不自然と判断する。理想的な誤答。
4 ＝ おそらく不自然。文法的に成立しないか、この文脈では使われない。
3 ＝ 境界的。文体や解釈によっては通るかもしれない。
2 ＝ おそらく自然な文になる。母語話者が使うことがある（実質もう一つの正解）。
1 ＝ 完全に自然な日本語になる。意味は変わるとしても、文として正しい。誤答に使ってはならない。

**判定すべきは「自然な文になるか」であり、「意味が同じか」ではありません。** ここが決定的です：
- 移動動詞に対する「に」と「へ」は、ニュアンスが違うだけで**どちらも自然**です。したがって 1 と評価してください。
- 「は」と「が」も、情報構造が違うだけで**どちらも自然**な場合が多くあります。
- 「を」と「が」は、一部の状態述語（〜たい、可能形）では**どちらも成立**します。

意味が変わることは誤答の根拠になりません。文として成立してしまえば、その選択肢を選んだ学習者を不正解にはできないからです。判断に迷う場合は低く評価してください。

JSON のみを返すこと。1 起点の候補番号をキーとし、各値は下記の数字キーのみを使うオブジェクト（名称は使わない）：
0：評価、1-5
1：理由、12 語以内

{{"1": {{"0": 5, "1": "他動詞の目的語に主格標示は不可"}}, "2": {{"0": 1, "1": "「へ」も自然：方向を表せる"}}}}

すべての候補を評価すること。JSON 以外の文章も markdown コードフェンスも不可。$PROMPT$,
    true, 'qwen/qwen3.7-plus', 'openrouter',
    'JA particle uniqueness judge (TASK-527): asks whether each distractor ALSO yields a natural sentence, which is the ni/he and wa/ga also-correct failure. Likert v3 — 5 = clearly wrong, 1 = also natural. Numeric entry keys (TASK-537/538).'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- Verification (run manually after applying)
-- ----------------------------------------------------------------------------
-- SELECT task_name, language_id, version, is_active, model
-- FROM public.prompt_templates
-- WHERE task_name IN ('ladder_particle_selection_generation',
--                     'ladder_particle_judge')
-- ORDER BY task_name;
--
-- Expect 2 rows, both language_id = 3, v1, is_active, each carrying the
-- Japanese key legend ("キー（") and neither containing '"rating"' or
-- '"blanked_particle"' as a JSON key.
--
-- Coverage: the L4-JA family is served by this type — check with
--   SELECT exercise_type, count(*) FROM exercises
--   WHERE language_id = 3 AND ladder_level = 4 GROUP BY 1;
