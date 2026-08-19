-- Natively authored zh/ja prompt rows (follow-on to TASK-722).
--
-- WHAT WAS WRONG
-- --------------
-- `scripts/audit_prompt_latin.py` separates Latin runs that are *machine
-- contract* (JSON keys, str.format placeholders, parser enums) from Latin that
-- is leaked English prose. Across 106 active zh/ja rows it found only a handful
-- of real defects. This migration fixes them:
--
--   translation_uniqueness_judge zh/ja  wholly English prompts (0.3%/0.4% CJK)
--   cloze_distractor_judge       zh/ja  wholly English, byte-identical to each other
--   question_inference           zh     "Martinez博士" inside the Chinese few-shot
--                                       passage; the whole scenario transplanted
--   question_main_idea           ja     English "vs"; translated English-context example
--   question_author_purpose      ja     English gloss "(Author Purpose/Tone)", "vs"
--
-- Each row was authored from scratch by `qwen/qwen3.8-max`, briefed IN the target
-- language (a brief written in English invites an English-flavoured answer, which
-- is the exact failure being repaired), via `scripts/rewrite_prompt_native.py`.
--
-- WHAT WAS DELIBERATELY *NOT* TOUCHED
-- -----------------------------------
-- Most Latin in these rows is load-bearing and translating it breaks the pipeline
-- silently, with no exception raised:
--
--   * `no_relation` / `no_inflection` / `no_collocation` are typed-schema escape
--     tokens (services/exercise_generation/schemas/ladder_typed.py:74)
--   * `corpus_validated` / `llm_asserted` are grounding constants
--     (services/vocabulary_ladder/collocation_grounding.py:53-54)
--   * the 27 persona archetypes are matched literally
--     (services/conversation_generation/scenario_generator.py:466)
--   * plain/polite/honorific/humble/formal/casual must match the `{register}`
--     value injected into ladder_p1_sentence_judge
--   * HSK / JLPT / CEFR / IPA / LinguaLoop are proper nouns
--   * pinyin examples ("qǐ lái" vs "qi3 lai2") are the point of the instruction
--   * the six dual_translation_tier* rows are not prompts at all -- they read
--     "Model-routing row only; no prompt text" and are never sent to a model
--
-- So `rewrite_prompt_native.py` carries a per-task `required_literals` list and
-- refuses any rewrite that drops one.
--
-- THE TWO SILENT-FAILURE MODES THESE PROMPTS HAVE
-- -----------------------------------------------
-- 1. services/exercise_generation/judges/cloze.py:110 is
--        verdicts[d] = 'reject' if v == 'reject' else 'keep'
--    Any other string -- a translated verdict word, a swapped one -- falls
--    through to `keep`. Every distractor survives, nothing raises, and the judge
--    becomes an expensive no-op.
-- 2. services/exercise_generation/judges/translation_uniqueness.py:17-21 runs an
--    INVERTED Likert scale (5 = clearly NOT an acceptable translation = ideal
--    distractor = accept). A prompt that "corrects" it keeps exactly the
--    also-correct options the judge exists to delete.
--
-- Neither failure raises, so `scripts/smoke_judge_prompt.py` pins expected
-- verdicts on fixtures and calls the real model.
--
-- MEASURED, 2026-08-17 (fixtures in smoke_judge_prompt.py):
--
--   translation_uniqueness zh   rewrite 1/1   incumbent n/a   -> ACTIVE
--   translation_uniqueness ja   rewrite 1/1   incumbent n/a   -> ACTIVE
--   cloze_distractor       zh   rewrite 0/2   incumbent 1/2   -> INACTIVE
--   cloze_distractor       ja   rewrite 0/2   incumbent 0/2   -> INACTIVE
--
-- The cloze numbers need reading, not just comparing. The zh rewrite is NOT
-- inverted (reading its verdicts as swapped would imply 蓝色 and 喝 are valid
-- completions). It is *more conservative*: it caught the also-acceptable synonym
-- that the incumbent MISSED in fixture 1 -- a real second-correct-answer shipped
-- by the live row -- and then over-rejected two clearly-wrong distractors. Two of
-- the fixtures are also genuinely marginal (爬床, 做会), so 0/2 overstates the
-- regression. ja is unchanged at 0/2 both ways: both prompts return all-keep, so
-- the bottleneck there is `qwen-2.5-72b-instruct`, not prompt language -- the
-- same model-dominates-prompt finding as TASK-718.
--
-- Because "different, not demonstrably better" is not grounds for changing a live
-- judge, the cloze rows land INACTIVE. TASK-719 is already slated to redesign that
-- rubric (its bands conflate topical distance with confusability); it should
-- measure these against a gold set and activate or discard them then.
--
-- Activate later with:
--   UPDATE prompt_templates SET is_active = (version = 2), updated_at = now()
--    WHERE task_name = 'cloze_distractor_judge' AND language_id IN (1, 3);
--
-- MODELS ARE UNCHANGED on every row, so any future re-measurement isolates the
-- prompt -- the discipline TASK-717/718 established.
--
-- Generated from the verified files in data/eval/ (see file hashes below), not
-- transcribed. Re-verify any row with:
--   python scripts/rewrite_prompt_native.py --task <t> --lang <l> --check <file>

BEGIN;

-- Source file hashes:
--   translation_uniqueness_judge_zh.txt        md5 850df6527f728f295f0fdaa5e5503cb8  2170 chars
--   translation_uniqueness_judge_ja.txt        md5 eafabf9ed23f380ce46ddf774d07d7cb  1430 chars
--   question_inference_zh.txt                  md5 329a274e55c091c394f8fafe04203ca4  2218 chars
--   question_main_idea_ja.txt                  md5 a7fe0771bfef3093ca01313d21f04560  1570 chars
--   question_author_purpose_ja.txt             md5 992e62cee4b7d27337ec44565ce06904  1269 chars
--   cloze_distractor_judge_zh.txt              md5 7a5f6e8f4275cbaf71c019c977fd30d2  2579 chars
--   cloze_distractor_judge_ja.txt              md5 fde592a835ac0b58845e401e87e05d18  1457 chars

-- translation_uniqueness_judge [zh] -> v2 (ACTIVE)
UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'translation_uniqueness_judge' AND language_id = 1 AND version <> 2;
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
VALUES (
    'translation_uniqueness_judge', 1, 2, TRUE,
    'qwen/qwen3.7-plus', 'openrouter',
    '你是一名中文母语的语言测评专家。你的任务是审查一道翻译选择题是否只有一个正确答案。题目给出一个中文原句：{tl_sentence}。题目中标为正确的译文是：{correct_translation}。各译文选项所使用的语言是 {nl_language}。需要你审查的是下列被标为错误的候选译文：
{candidates_numbered}

请逐个评判上述每一个候选译文，判断它究竟有多明显地不是该中文原句的可接受译文。判断时，必须以中文原句为最终依据，而不是以标准答案为唯一依据。标准答案只是提示一种可接受译法，不能因为候选译文与标准答案在措辞、语序、语体、近义表达上不同，就认定候选译文错误。只要候选译文传达了与原句相同的意思，它也是正确的，这道题就存在唯一性缺陷。

你要特别警惕一种常见误判：把目标语言的语法差异误认为翻译错误。许多语法范畴在汉语中并不显性表达，但在其他语言中可能必须表达。因此，候选译文若仅仅在下列方面与标准答案不同，通常仍然是可接受的译文：

一、单复数。汉语名词一般不标数，除非有明确数量词或语境限制。目标语言选择单数、复数或泛指数，若没有改变事件和参与者关系，通常不应视为错误。

二、时与体。汉语只有“了、过、在、着”等词语才显性标记某些时体意义。若原句没有这些显性标记，目标语言选择不同时间或体貌形式，可能只是补足目标语言所需的语法范畴，不应轻易判错。若原句已有显性标记，候选译文明显违背该标记，则应视为实质差异。

三、有定与无定。汉语没有冠词，“书”既可以理解为“那本书”，也可以理解为“一本书”。除非原句已经用指示词、数量词或上下文明确限定，候选译文在定指与不定指上的选择通常不应单独导致错误。

四、依靠语境可以还原的主语、宾语省略。汉语常省略可恢复的成分。若候选译文补出了从原句语境可以自然恢复的主语、宾语或代词，通常不应视为增添信息；若候选译文补出了原句无法恢复的新参与者，则应视为增添信息。

反之，若候选译文在事件本身、参与者、否定、情态上有差别，那就确实是错误的译文。事件本身的差别包括动作是否发生、状态是否成立、事件性质是否改变。参与者的差别包括人物身份、对象关系、施受方向、数量角色是否被错置。否定的差别包括把肯定改成否定、把否定改成肯定，或改变否定范围。情态的差别包括必须、可能、愿意、禁止、应当、能够等意义被改变。若候选译文在这些方面与原句冲突，应给较高分数。

改述、近义词、语体或语序的不同，并不使一个译文变错。若候选译文只是把书面说法换成口语说法、把一般表达换成近义表达、把句子顺序重新安排，或把汉语隐含的连接关系按目标语言习惯显化，只要核心事件、参与者、否定和情态不变，就不应视为错误。若候选译文为了目标语言自然而做了轻微增删，但增删内容只是语法衔接，并未增加新事实，也应视为可接受倾向。

评分尺度必须严格照下列方向理解，不得改动：

5 ＝ 明显不是可接受的译文；它改变了意思、遗漏或增添了信息、或误译了关键词。是理想的干扰项。

4 ＝ 大概不可接受；称职的母语者会判它错，尽管比较接近。

3 ＝ 有争议；勉强可以辩护为一个宽松的译法。

2 ＝ 大概也可以接受；多数母语者会认可它。

1 ＝ 完全可以接受；它和原句意思相同。该选项也是正确的，必须从题目中删除。

这个分数方向是反直觉的：高分表示该候选作为干扰项越好，越应当保留；低分表示该候选也正确，越应当删除。请勿把方向写反。给 1 的候选意味着题目不唯一；给 5 的候选意味着该候选是有效干扰项。任何情况下，都不能因为候选译文“接近标准答案”就给高分，也不能因为候选译文“与标准答案不同”就给低分。关键始终是它是否仍是原句的可接受译文。

在写理由时，请用中文说明判断依据。指出候选译文与原句相比是否同义；如果不同义，说明改变了哪一类意义；如果同义，说明差异是否只属于汉语不明说的范畴。理由要具体，避免空泛。可以提到原句中的关键词语、省略成分、显性标记或语境线索，但不要引入原句没有的信息。

如果候选译文在目标语言中不够优美、不够简洁、语体略有不合，但意思没有改变，不应因此给高分。本题只判断语义可接受性，不判断风格是否最佳。若候选译文遗漏关键信息、增添原句没有的事实、改变对象关系、误译关键词，应给 4 或 5。若候选译文只是换一种说法，或把隐含信息按目标语言习惯说得更明白，且没有增加新事实，应给 1、2 或 3，视可接受程度而定。

请为每一个候选译文给出一个整数分数，并给出一条中文理由。分数必须是 1 到 5 的整数，不得半分。候选列表中有几个候选，就必须输出几个条目；不得遗漏任何一个候选译文。若某个候选难以判断，也必须在现有原句信息下选择最接近的整数分数，并在理由中说明争议点。

最终只输出一个 JSON 对象，不要输出任何解释、标题、列表或额外文字。输出形式必须严格为：
{{"1": {{"rating": 5, "reason": "..."}}, "2": {{"rating": 1, "reason": "..."}}}}

上述格式仅示意两个条目的写法；实际输出必须包含全部候选编号，每个编号对应一个条目。理由用中文书写。输出中不得添加任何额外字段，也不得改变字段名称。',
    'v2: natively authored in Chinese (qwen3.8-max). Replaces an all-English row. Inverted 1-5 scale preserved and verified live by scripts/smoke_judge_prompt.py.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = EXCLUDED.is_active,
       description   = EXCLUDED.description,
       updated_at    = now();

-- translation_uniqueness_judge [ja] -> v2 (ACTIVE)
UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'translation_uniqueness_judge' AND language_id = 3 AND version <> 2;
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
VALUES (
    'translation_uniqueness_judge', 3, 2, TRUE,
    'google/gemini-3.5-flash-lite', 'openrouter',
    'あなたは日本語母語の言語評価の専門家として、翻訳多肢選択問題の一意性を判定してください。課題の中心は、日本語の原文が明示しない事柄によって訳文候補が正解と実質的に同じになっているか、それとも意味が本当に異なるかを見極めることです。

次に、日本語の原文を示します。
原文：{tl_sentence}
正解とされている訳文：{correct_translation}
選択肢が書かれている言語：{nl_language}
誤答とされている訳文候補の一覧：
{candidates_numbered}

あなたは、誤答とされている候補訳を一つずつ、原文の日本語文の訳としてどれほど明確に受け入れられないかを評価してください。すべての候補訳を必ず採点し、一件も漏らしてはいけません。候補訳がその言語で書かれている場合でも、判定の基準は日本語原文との意味関係です。

言い換え、類義語、語域、語順、文体の違いだけでは、訳文を誤りにしません。候補訳が原文と同じ出来事、参与者、関係、否定、様相を伝えているなら、それは受け入れ可能な訳です。その場合、候補訳も正解であり、この問題は壊れています。

特に、日本語が通常明示しない範疇に注意してください。候補訳が正解訳と異なる点が、数、定・不定、文脈から復元できる主語や目的語の省略、丁寧さのレベルのみにある場合は、多くの場合、受け入れ可能な訳です。名詞の単数・複数、冠詞の有無、省略された項の補い方、敬体の違いは、命題内容を変えなければ誤りではありません。

逆に、出来事そのもの、参与者、否定、様相、誰が誰に何をしたかという関係に違いがある場合は、その候補訳は誤りです。助詞の役割、特に主題、主格、対格、与格の違いに注意してください。動作の向き、相手、対象、原因、時間、場所、数量が意味を変える形で異なっていれば、受け入れられません。

評価は、次の尺度に厳密に従い、1から5の整数のみで採点してください。方向が重要です。高い点数ほど、その候補訳が誤答として適切であり、問題に残せることを意味します。低い点数ほど、その候補訳も正解として受け入れられるため、問題から取り除く必要があることを意味します。

5：明らかに受け入れられない訳。意味を変える、必要な情報を落とす、存在しない情報を加える、重要な語を誤訳している。理想的な誤答選択肢である。
4：おそらく受け入れられない。近いが、熟練した話者なら誤りと呼ぶ違いがある。
3：議論の余地がある。緩い訳としてなら擁護できるが、正解としては不安定である。
2：おそらく受け入れられる。多くの話者は原文の訳として認めるだろう。
1：完全に受け入れられる。原文と同じ意味である。この選択肢も正解であり、問題から取り除かなければならない。

この方向を決して取り違えないでください。5は良い誤答候補、1は除去すべき追加正解です。

出力は、次の形式のオブジェクトのみとしてください。説明文、前置き、後書き、追加の記号は不要です。候補訳の一覧にあるすべての番号について、同じ番号の鍵を必ず含めてください。候補訳が三件以上ある場合も、番号を一つずつ増やしながら同じ構造を続けてください。理由は日本語で簡潔に書いてください。
{{"1": {{"rating": 5, "reason": "..."}}, "2": {{"rating": 1, "reason": "..."}}}}',
    'v2: natively authored in Japanese (qwen3.8-max). Replaces an all-English row. Inverted 1-5 scale preserved and verified live by scripts/smoke_judge_prompt.py.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = EXCLUDED.is_active,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_inference [zh] -> v2 (ACTIVE)
UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'question_inference' AND language_id = 1 AND version <> 2;
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
VALUES (
    'question_inference', 1, 2, TRUE,
    'qwen/qwen3.7-plus', 'openrouter',
    '你是一名中文母语的语言测评专家，请根据下面的材料命制一道四选一推理类阅读理解题。

出题材料：{prose}
难度等级（1至9）：{difficulty}
已出问题列表：{previous_questions}

一、考查目标
这道题要考查学生从文本中推出未明说含义的能力。答案不能在原文中被直接说出，也不能只是对细节的简单复述；它必须由文中的人物言行、环境细节、语气停顿、时间关系或因果暗示共同支撑。题干应引导学生听出言外之意，把握人物真实态度、事件潜在原因、情境可能走向或话语背后的限制条件。推理类型可包括推断人物意图、事件原因、关系变化、话语态度、后续可能或隐含限制，但本题只能选择一个最清晰的落点。

二、与已有题目的差异
请先核对已出问题列表。新题在推理类型、关注点、提问方式和答案落点上都要与已有题目明显不同。不要沿用相同线索，不要重复相似问法，不要把旧题只换几个词。若列表为空，则从材料中选择最有推理价值的一处或几处线索自行命题。

三、命题要求
1. 只生成一道题，四个选项，答案唯一。
2. 题干使用自然、规范的现代汉语，可询问“最可能推出”“可以推知”“暗示了什么”等，但不要直接要求学生寻找原文句子。
3. 正确选项必须能够由文中至少一处明确线索经过合理推断得出。线索可以是一个动作、一句含蓄的话、一个时间细节、一次回避、一个停顿、一种称呼或一处环境描写。
4. 正确选项不得照抄原文，也不得只是把原文词句换个说法；它应概括文中没有直接说明但合乎逻辑的含义。
5. 干扰项要与材料相关，表面上看合理，实际上缺少足够文本证据，或存在过度推断、因果颠倒、把可能说成必然、扩大范围、忽视语气限制等问题。
6. 不要依靠生活常识、专业背景或材料之外的信息才能判断答案。所有判断都应回到文本。
7. 四个选项的句式、长度和信息量要尽量接近，不要让正确项因为更具体、更温和、更完整或更像总结而显得突出。
8. 正确选项在四个选项中的位置不能固定。请让正确项自然分布在任意一项，避免形成固定模式。下方示例只展示推理线索和解释写法，其正确项位置不应被模仿为固定规则。
9. 题干、选项和解释都要使用地道中文，避免翻译腔。不得出现外文人名、外文术语、拼音或字母编号。若材料中出现外来名称，应改成符合中文阅读习惯的表达，但不得改变原文信息。
10. 题干不得泄露答案，选项不得互相矛盾到可以轻易排除，也不得出现明显绝对化词语，除非原文足以支持该绝对判断。
11. 题干若使用否定或限制条件，必须表达清楚，避免学生因句式绕口而误判；不要为了增加难度而故意制造歧义。
12. 选项内容应围绕同一推理焦点展开，避免四个选项分散到互不相关的事件上；若材料信息丰富，也应只选取一个最能体现言外之意的焦点。
13. 解释应先列出关键证据，再说明这些证据如何共同推出答案；对每个干扰项都要指出其不成立的原因，但无需逐字复述全部原文。

四、难度控制
请根据难度等级调整推理跨度与干扰强度。较低难度时，线索可相对集中，推理链条较短，正确项与文本证据的距离较近；较高难度时，线索可分散在不同句子中，需要整合语气、动作、场景和人物关系，干扰项也要更接近正确项。但无论难度高低，正确项都必须有充分文本依据，且只能有一个最佳答案。

五、完整示例
以下示例仅展示命题思路、语言风格和解释方式，不要求你使用相同场景，也不代表正确项应放在某一固定位置。请勿照抄示例中的人物、场景、语句或推理落点。

例文：周五下午，社区图书室的窗帘拉得严严实实。赵老师把一摞借阅卡按日期排好，时不时望向门口。小周抱着一箱旧书进来，额头上全是汗。赵老师轻声说：“先别拆，等周主任通知。”小周把箱子放到桌角，压低声音：“刚才在走廊遇见李会计，她说今年的活动经费已经报完了。”赵老师停顿了一下，把最上面那张借阅卡翻了过去：“那就先把书登记上，别写新购。”

问题：根据上述材料，最能合理推出哪一项？

选项：
赵老师已经知道周主任不会来通知。
小周没有参与过图书登记工作。
赵老师想避免让人误会这批旧书来自新经费。
李会计反对图书室举办活动。

正确答案：赵老师想避免让人误会这批旧书来自新经费。

解释：文中赵老师听到活动经费已经报完后，仍要求登记旧书，却特意叮嘱“别写新购”，说明她担心登记方式会让人以为这批书动用了新经费或新采购。这一含义没有直接说出，却由经费报完、压低声音、停顿和叮嘱共同支持。其他选项中，第一项缺少依据，文中只是等待通知，并不能推出不会来通知；第二项无从判断；第四项把经费报完误解为个人反对活动，线索不足。

六、输出要求
最终只输出一个 JSON 对象，不要输出任何前言、后记、标题、列表或额外说明，也不要用任何符号包裹输出。请确保该对象可解析，字段名和固定值不得改动、翻译、增删或调整顺序。答案字段必须填写正确选项的完整文字，且与对应选项文字完全一致，不得填写序号或位置。解释字段必须用中文说明正确选项的文本依据、推理过程，并简要说明其他选项为何不成立。

{{
  "question_text": "...",
  "question_type": "inference",
  "choices": ["...", "...", "...", "..."],
  "answer": "...",
  "explanation": "..."
}}',
    'v2: natively authored in Chinese (qwen3.8-max). Removes the English name "Martinez" from the few-shot passage and replaces the transplanted English scenario with a Chinese one.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = EXCLUDED.is_active,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_main_idea [ja] -> v2 (ACTIVE)
UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'question_main_idea' AND language_id = 3 AND version <> 2;
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
VALUES (
    'question_main_idea', 3, 2, TRUE,
    'qwen/qwen3.7-plus', 'openrouter',
    'あなたは日本語の読解問題を作成する専門家です。以下の材料の文章を読み、文章全体の主旨を問う四択問題を 1 問作ってください。

材料の文章：
{prose}

難易度：{difficulty}

既に出題済みの質問：
{previous_questions}

課題：
文章の細部ではなく、文章全体から読み取れる中心主題、筆者の主な目的、全体としてのメッセージを問う問題を 1 問作成すること。情報を統合し、その文章が主として何について書かれているかを見抜く力を測ること。個々の出来事、数字、登場人物の行動だけを確認する問題にはしないこと。

作り方：
正しい選択肢は、文章全体を最もよく要約するものにする。誤答は、次のいずれかにすること。具体的すぎるため一部の細部にとどまるもの、広すぎて文章の範囲を超えるもの、文章の内容に照らして事実として誤っているもの。正解は四つの選択肢のうち一つだけにする。正解の位置は特定の位置に固定せず、内容に応じて決めること。例の配置に引きずられないこと。選択肢には番号や記号を含めず、本文だけを書くこと。

難易度が高い場合は、正解が一文の言い換えにとどまらず、複数の記述を突き合わせないと選べないような選択肢にする。難易度が低い場合は、中心主題を比較的つかみやすくする。ただし、どちらの場合も、文章に現れない一般論や筆者の感情を正解にしないこと。

既に出題済みの質問を参照し、問いの枠組み、表現、誤答の作り方を変え、同じような問題を繰り返さないこと。対比を示すために英字の記号を用いず、日本語の表現で書き分けること。質問文は自然な現代日本語とし、学習者が迷わない表現にすること。

正解の文字列は、選択肢の本文と完全に一致させること。質問文、選択肢、正解、解説はすべて自然な現代日本語にすること。

例：
文章：
昔ながらの商店街では、空き店舗が目立つようになった。そこで地元の人々は、使われていない店を改装し、子どもが放課後に過ごせる場所として開いた。お年寄りが将棋を教え、学生が宿題を見る。買い物のついでに立ち寄る人も増え、店先には笑顔が戻った。この取り組みは、空き店舗の活用にとどまらず、地域のつながりを結び直す試みとなっている。

質問：
この文章の主旨として最も適切なものはどれか。

選択肢：
空き店舗を改装して子どもが過ごす場所を作ったこと。
地域のつながりを回復する試みとして空き店舗活用が機能していること。
空き店舗を使えば、どの商店街でも地域のつながりが必ず回復すること。
お年寄りが将棋を教えることで子どもの学力が向上すること。

正解：
地域のつながりを回復する試みとして空き店舗活用が機能していること。

解説：
文章は、空き店舗の改装という出来事を出発点にしつつ、最終には地域のつながりを結び直す試みとして意味づけている。したがって、地域のつながりを回復する試みとして空き店舗活用が機能しているという選択肢が適切である。空き店舗の改装だけを取り上げる選択肢は具体策の一部にとどまり、どの商店街でも必ず回復するとする選択肢は文章の範囲を超える一般化であり、将棋で学力が向上するとする選択肢は文章にない因果を含んでいる。

例の正解の位置は偶然のものであり、同じ位置を選ぶ必要はない。

出力：
次のオブジェクトだけを出力すること。前置き、後書き、見出し、説明文を付けないこと。

{{
  "question_text": "...",
  "question_type": "main_idea",
  "choices": ["...", "...", "...", "..."],
  "answer": "...",
  "explanation": "..."
}}',
    'v2: natively authored in Japanese (qwen3.8-max). Removes the English "vs" metalanguage and the translated English-context few-shot example.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = EXCLUDED.is_active,
       description   = EXCLUDED.description,
       updated_at    = now();

-- question_author_purpose [ja] -> v2 (ACTIVE)
UPDATE prompt_templates SET is_active = FALSE, updated_at = now()
 WHERE task_name = 'question_author_purpose' AND language_id = 3 AND version <> 2;
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
VALUES (
    'question_author_purpose', 3, 2, TRUE,
    'qwen/qwen3.7-plus', 'openrouter',
    'あなたは日本語母語の言語評価の専門家として、筆者の意図や文章の調子を問う読解問題を作成してください。次の文章を読み、四択問題を一問だけ作ります。材料となる文章は{prose}です。難易度は{difficulty}を基準とし、語彙、文の長さ、設問のひねり、選択肢の紛らわしさを調整してください。難易度が低い場合は本文の明示的な手がかりを、高い場合は間接的な表現や言い回しのニュアンスを手がかりにしてください。

すでに出題された質問の一覧である{previous_questions}を確認し、前回と同じ観点にならないようにしてください。問う観点は、書いた目的、文章の調子、筆者の態度、視点、論の進め方のいずれかから選び、前回と異なるものにしてください。このとき、英字の記号や外国語の用語は使わず、日本語で言い分けてください。

設問は、筆者がなぜその文章を書いたのか、その態度・調子・立場を問うものにしてください。筆者の意図、見方、感情的な立場の理解を測ること。書いた目的、文章の調子、立場、論の運び方のうち一つに焦点を当ててください。語の選び方、構成、全体のメッセージの分析を求めること。正解は必ず本文中の根拠に裏づけられていること。選択肢は四つすべて本文の内容から判断できるものにしてください。本文に書かれていない推測や、一般論だけでは正解を導けないようにしてください。誤答の選択肢は、本文の一部を誇張したり、反対の意味に変えたり、範囲を広げすぎたりして、明確に誤りと判断できるものにしてください。正解の位置は固定せず、四つの選択肢のどこにあってもよいようにしてください。

作成例：
文章：新しい働き方として週休三日制が注目されている。生産性の向上や育児・介護との両立を考えると、導入には確かに利点がある。ただし、業種によっては人員確保が難しく、賃金削減を招くおそれもある。したがって、一律に理想と持ち上げるのではなく、職種や企業規模に応じた慎重な設計が不可欠だろう。
質問：この文章における筆者の態度として最も適切なものはどれか。
選択肢：
・週休三日制を全面的に支持している。
・週休三日制に反対している。
・条件付きで導入を認めている。
・導入の可否に関心を持っていない。
正解：条件付きで導入を認めている。
解説：筆者は「確かに利点がある」と述べる一方で、「ただし」「おそれもある」「慎重な設計が不可欠」と留保を示しており、無条件の賛成でも反対でもないため。

最終的な出力は、次の形式のみとしてください。それ以外の説明、記号、注意書きは含めないでください。出力の形式は以下とし、種類を示す値は変えないでください。

{{
  "question_text": "...",
  "question_type": "author_purpose",
  "choices": ["...", "...", "...", "..."],
  "answer": "...",
  "explanation": "..."
}}',
    'v2: natively authored in Japanese (qwen3.8-max). Removes the English gloss "(Author Purpose/Tone)" and the "vs" metalanguage; uses 筆者 rather than 著者.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = EXCLUDED.is_active,
       description   = EXCLUDED.description,
       updated_at    = now();

-- cloze_distractor_judge [zh] -> v2 (INACTIVE; v1 stays live)
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
VALUES (
    'cloze_distractor_judge', 1, 2, FALSE,
    'deepseek/deepseek-chat', 'openrouter',
    '你是一名长期审阅汉语测试题的中文母语语言测评专家。现在请你审查一道中文完形填空题的干扰项。题目材料如下：

带空格的句子：{sentence_with_blank}

预定正确答案：{correct_answer}

待评判干扰项列表：
{distractors_numbered}

你的任务不是重新选正确答案，也不是评价正确答案是否最优，而是逐个审查每一个编号干扰项：把该干扰项原样填入空格后，判断它是否仍然可以成为一个合理的填空答案。一道合格的完形填空题只能有一个可接受答案。只要某个干扰项填入后语法可通、语义合理、搭配自然、语体相称、逻辑顺畅，哪怕不如预定答案地道，也说明题目存在第二个可接受答案，该干扰项必须判为不合格。只有当该干扰项在这个具体句子里明显说不通，任何称职的中文母语者都不会把它当作正确答案，才可以判为合格。判为合格表示保留该干扰项，判为不合格表示拒绝该干扰项。

判断尺度必须从严。若你拿不准某个干扰项是否可接受，或者需要额外设想特殊语境、补充隐含信息、替作者追加解释才能让它成立，一律判为不合格。好的完形填空题不应保留模棱两可的干扰项。

审查时，请完全依据汉语自身的语感和规则，不要借助其他语言的语感。重点检查以下方面：

一、句意与逻辑。填入后是否与上下文语义一致，是否违背常识、事件顺序、因果、转折、条件、目的、让步等关系。若句中出现关联词语或呼应结构，要看填入项是否破坏呼应。若逻辑明显断裂，可判合格；若逻辑仍能成立，则判不合格。

二、词语搭配。汉语讲究习惯搭配，必须区分固定搭配与自由组合。审查动宾是否相配、修饰语与中心语是否相配、介词框架是否完整、补语是否能接在动词后、名词能否受该形容词或数量结构修饰。不要只凭词义相近就放行。若搭配明显不合汉语习惯，可判合格；若只是不如预定答案常见，但搭配可通，则判不合格。

三、词性与句法位置。汉语各类词在句中的功能不同。填入项是否能处在空格位置，能否受前后成分修饰或支配，是否造成成分残缺、成分赘余、语序不当或句式杂糅。动词的配价也要看它能否带该宾语、能否进入该句式。形容词能否直接作谓语，副词能否修饰该谓语，介词结构能否与后续成分搭配。若句法功能明显不合，可判合格；若汉语中该用法可以成立，则判不合格。

四、汉语特有结构。离合词通常不能直接带宾语，若空格后出现宾语，而干扰项属于不能这样带的离合词，应视为不通。动补结构、结果补语、趋向补语、可能补语要看补语与动词、宾语是否匹配。把字句、被字句、比较句、存现句、连动句、兼语句各有成立条件，若干扰项破坏这些条件，可判合格；若结构仍能成立，则判不合格。

五、体貌与时间信息。汉语不靠动词变形表示时间，而常借“了、着、过”、时间词语、副词、趋向成分和语境共同表达。若句子已有完成、持续、经历、将然、惯常、瞬间等线索，要检查干扰项是否与之冲突。例如句子表示经常发生，却填入带有明显完成意味的结构；句子表示状态持续，却填入瞬时完成动作；句子表示过去经历，却与语境不符。若冲突明显，可判合格；若仍可解释，则判不合格。

六、量词与名词、动词的匹配。若空格涉及数量结构，必须审查量词是否与名词或动词相配。名量词、动量词、借用量词各有适用对象。若量词明显不能修饰该名词，或动量词不能计量该动作，可判合格；若属于可接受搭配，即使不是最佳，也应判不合格。

七、语体与色彩。书面语与口语、正式与随便、褒义与贬义、尊敬与谦逊、客观叙述与主观评价，都应与句子整体一致。若干扰项语体色彩明显错位，例如公文词语进入日常口语句，或俚俗词语进入庄重书面句，可判合格；若语体差异不影响理解且该语境可兼容，则判不合格。

八、音节与韵律。汉语重视音节匀称和节奏自然。单音节词与双音节词的嵌合会影响自然度，但韵律不自然不必然等于错误。只有当韵律冲突导致结构生硬、读起来明显不成话时，才可作为辅助理由；若只是不够优美，仍可能构成可接受答案，应判不合格。

九、近义词与同义替代。凡是与预定正确答案意义接近、在该句中可以替换而不改变基本句意的词，一律不能保留。不要因为预定答案更地道、更常见，就将近义替代判为错误。完形填空不能以唯一出题词形排除可接受同义表达。

十、语境宽窄。若句子本身信息不足，导致多个词都能填通，应从严认定干扰项不合格。题干没有明确排除的语义，不能借出题意图强行排除。只有句子内部线索明确排斥该干扰项时，才可判合格。

评判流程如下：对每个编号干扰项，先把该词原样填入空格，形成完整读法；再以中文母语者的自然语感通读全句；然后对照上述审查点，寻找是否存在明确、具体、无需额外想象的排除理由；最后作出结论。若存在明确排除理由，并且该理由来自本句内部的语法、语义、搭配、体貌、语体、结构或逻辑，则判为合格；若没有明确排除理由，或必须假设特殊语境才能排除，则判为不合格。

理由书写要求：每个编号都要给出一句简洁理由，用中文直接说明该干扰项在本句中为何明显不通，或为何可以成为可接受答案。不要泛泛而谈，不要只说“不合适”“语义不对”。合格理由应指出具体病灶，例如动宾不配、量词不合、体标记冲突、语体错位、离合词误带宾语、关联关系断裂、词性位置不合等。不合格理由应指出它能够填入并成立，例如语义可通、搭配可接受、与句内时间信息不冲突、可被母语者理解为合理答案等。不要讨论预定正确答案为何更好，除非用于说明干扰项也可接受。不要引入题干以外的背景知识。不要改动干扰项，也不要替干扰项补充省略成分。若一个干扰项同时存在多个问题，只写最直接、最确定的一条。

输出要求：最终只输出一个 JSON 对象，不要输出任何解释、标题、编号列表或额外文字，也不要使用代码围栏。对象键名必须与待评判干扰项编号一致，从第一个编号开始，逐个覆盖全部干扰项，不得遗漏。每个编号对应一个子对象，包含评判结果和理由两个字段。判为合格时，使用示例中表示保留的取值；判为不合格时，使用示例中表示拒绝的取值。字段名、字段顺序、标点和格式必须与下方示例完全一致，不得翻译、改写或增删。格式如下：
{{"1": {{"verdict": "keep", "reason": "..."}}, "2": {{"verdict": "reject", "reason": "..."}}}}',
    'v2 (INACTIVE): natively authored in Chinese (qwen3.8-max). Staged pending TASK-719 - the smoke test shows it changes verdict behaviour, not just language.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = EXCLUDED.is_active,
       description   = EXCLUDED.description,
       updated_at    = now();

-- cloze_distractor_judge [ja] -> v2 (INACTIVE; v1 stays live)
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
VALUES (
    'cloze_distractor_judge', 3, 2, FALSE,
    'qwen/qwen-2.5-72b-instruct', 'openrouter',
    'あなたは日本語母語話者の言語評価専門家として、穴埋め問題の誤答選択肢を一点の曇りなく点検してください。ここに示す材料はすべて日本語です。日本語の語感、文法、語彙、文体、敬語、慣用的な使い分けに基づいて判断してください。

問題文：{sentence_with_blank}
正解：{correct_answer}
誤答選択肢：
{distractors_numbered}

あなたの任務は、誤答選択肢を一つずつ評価し、それぞれが「この問題の誤答として適切に機能しているか」を判定することです。正解は一つだけです。誤答選択肢は、どれもこの問題文では明らかに成り立たず、力のある母語話者が妥当な答えとして選ぶ余地がないものでなければなりません。

判定の意味は次のとおりです。
・適格：その選択肢を空欄に入れると、文法的には成立し得る場合でも、この問題文では明らかに誤りだと判断できること。意味が合わない、語の相性が不自然、動作の継続・結果の状態・完了・時制が合わない、丁寧さや文体が合わない、動詞や形容詞が要求する格と合わない、自動詞と他動詞の対応が崩れる、活用形が文脈に合わない、などにより、正解にはなり得ません。
・不適格：その選択肢が、文法的にも意味的にもこの文で許容でき、母語話者が妥当な答えとして選び得ること。正解ほど自然でなくても、類義語、同義語、文脈上成り立つ言い換え、敬語や文体の許容範囲内の言い換えであれば、すべて不適格としてください。

判定は厳しくしてください。この文脈で誤答として確実に機能しているか確信が持てない場合は、不適格としてください。良い穴埋め問題では、曖昧な誤答選択肢はゼロであるべきです。

日本語固有の観点を必ず見てください。格助詞「が・を・に・で・と・へ・から・まで・より」との適合、自動詞と他動詞の取り違え、動詞の活用形、テ形・タ形・可能形・受身形・使役形などの意味、ている・てある・ておくの使い分け、和語・漢語・外来語の文体差、改まり度、敬語レベルの一致、名詞と動詞の慣用的な取り合わせ、比喩や決まり文としての自然さ、話し言葉と書き言葉の差、主語・対象・受益者の関係、数量表現や助数詞の相性、形式名詞や接続表現の制約などを検討してください。英文法の用語をそのまま当てはめず、日本語の文法と語感に基づいて説明してください。

各誤答選択肢について、問題文の空欄に実際に入れた形を頭の中で作り、読み手として自然に読めるか、正解と競合しないか、学習者を迷わせないかを確かめてください。文の一部だけを見て判断せず、空欄前後の助詞、時制、相、文体、敬語、意味役割、語の強弱や格式まで含めて判断してください。正解との微妙な差ではなく、この文で許容できるかどうかで判断してください。

出力は、評価対象の誤答選択肢の番号を鍵とし、それぞれの判定と理由を値とするジェイソンオブジェクトだけにしてください。理由には、どの日本語の制約に反するか、あるいはなぜ許容されるかを具体的に書いてください。判定値は、誤答として維持すべき場合は採用、取り下げるべき場合は不採用とし、下の例にある鍵名と値の綴りを一切変えずにそのまま使ってください。理由の値も日本語で具体的に書くこと。出力形式は次のとおりです。

{{"1": {{"verdict": "keep", "reason": "..."}}, "2": {{"verdict": "reject", "reason": "..."}}}}',
    'v2 (INACTIVE): natively authored in Japanese (qwen3.8-max). Staged pending TASK-719 - see the zh note; ja shows no measurable change either way.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = EXCLUDED.is_active,
       description   = EXCLUDED.description,
       updated_at    = now();

COMMIT;
