-- ============================================================================
-- Dual Translation - taxonomy v4 seed (TASK-616, Stage 4 localisation)
-- Cumulative, self-contained (each version row is a COMPLETE taxonomy the cascade
-- loads as one active row). Per-pair subtype lists mirror the L2 baseline set/order;
-- the localisation payload is the enriched per-L1 templates / per-L2 glosses + the
-- explicit pairs[l1-l2] keys. The taxonomy carries NO weights (see dt_rubric_v2_seed.sql).
-- ============================================================================

BEGIN;

-- Enforce the single-active-row invariant: deactivate any other active row, then
-- upsert THIS version as the active one (idempotent: re-applying keeps exactly this
-- version active and deactivates the rest).
UPDATE public.dt_taxonomy_version SET is_active = false WHERE is_active AND version <> 4;

INSERT INTO public.dt_taxonomy_version (version, is_active, taxonomy, description)
VALUES (
    4,
    true,
    $taxonomy${
  "pairs": {
    "en": {
      "subtypes": [
        "word_order",
        "word_choice",
        "omission",
        "register",
        "article",
        "preposition",
        "phrasal_verb",
        "tense_aspect",
        "subject_verb_agreement"
      ]
    },
    "en-ja": {
      "subtypes": [
        "word_order",
        "word_choice",
        "omission",
        "register",
        "particle",
        "keigo_register",
        "counter_classifier",
        "script_choice",
        "topic_comment"
      ]
    },
    "en-zh": {
      "subtypes": [
        "word_order",
        "word_choice",
        "omission",
        "register",
        "classifier",
        "aspect_marker",
        "topic_comment",
        "ba_construction",
        "resultative_complement"
      ]
    },
    "ja": {
      "subtypes": [
        "word_order",
        "word_choice",
        "omission",
        "register",
        "particle",
        "keigo_register",
        "counter_classifier",
        "script_choice",
        "topic_comment"
      ]
    },
    "ja-en": {
      "subtypes": [
        "word_order",
        "word_choice",
        "omission",
        "register",
        "article",
        "preposition",
        "phrasal_verb",
        "tense_aspect",
        "subject_verb_agreement"
      ]
    },
    "ja-zh": {
      "subtypes": [
        "word_order",
        "word_choice",
        "omission",
        "register",
        "classifier",
        "aspect_marker",
        "topic_comment",
        "ba_construction",
        "resultative_complement"
      ]
    },
    "zh": {
      "subtypes": [
        "word_order",
        "word_choice",
        "omission",
        "register",
        "classifier",
        "aspect_marker",
        "topic_comment",
        "ba_construction",
        "resultative_complement"
      ]
    },
    "zh-en": {
      "subtypes": [
        "word_order",
        "word_choice",
        "omission",
        "register",
        "article",
        "preposition",
        "phrasal_verb",
        "tense_aspect",
        "subject_verb_agreement"
      ]
    },
    "zh-ja": {
      "subtypes": [
        "word_order",
        "word_choice",
        "omission",
        "register",
        "particle",
        "keigo_register",
        "counter_classifier",
        "script_choice",
        "topic_comment"
      ]
    }
  },
  "subtype_glosses": {
    "article": {
      "en": "article — wrong, missing, or extra a/an/the; covers definiteness (a vs the) and using no article where one is required (or vice versa) with countable/uncountable nouns"
    },
    "aspect_marker": {
      "zh": "体标记——“了／过／着”等体标记使用错误。汉语用体（aspect）而非时态：了表示完成，过表示曾经经历，着表示持续状态；不能按外语的时态直接对应"
    },
    "ba_construction": {
      "zh": "把字句——“把”字结构使用错误或缺失"
    },
    "classifier": {
      "zh": "量词——量词使用错误或与名词搭配不当。常见错误是一律用“个”代替专用量词（如应为一本书、一件衣服、一只猫），或量词与名词不匹配"
    },
    "counter_classifier": {
      "ja": "助数詞——数を数える際の助数詞（カウンター）の誤り"
    },
    "keigo_register": {
      "ja": "敬語——敬語レベルの誤り。丁寧語（です・ます）、尊敬語（相手の動作を高める）、謙譲語（自分の動作をへりくだる）の使い分けを含む。文法的に正しくても、場面に求められる敬意レベルと異なれば誤りとする"
    },
    "omission": {
      "en": "omission — a required word or element is missing",
      "ja": "要素の欠落——必要な語や要素が抜けている",
      "zh": "成分缺失——缺少必要的词或成分"
    },
    "particle": {
      "ja": "助詞——助詞の誤り。特に「は」（既知の主題）と「が」（新情報の主語）の使い分け、「を」（対象）、「に」／「で」（着点・場所）の誤りを含む"
    },
    "phrasal_verb": {
      "en": "phrasal verb — wrong particle or wrong/avoided phrasal-verb form"
    },
    "preposition": {
      "en": "preposition — wrong, missing, or extra preposition (in/on/at/to/for/of ...); usually governed by the specific verb, noun, or fixed expression, not by literal translation"
    },
    "register": {
      "en": "register — wrong level of formality or tone for the context",
      "ja": "文体・語調——場面に対して丁寧さや語調のレベルが合っていない",
      "zh": "语域——正式程度或语气与语境不符"
    },
    "resultative_complement": {
      "zh": "结果补语——结果补语使用错误或缺失"
    },
    "script_choice": {
      "ja": "表記——仮名／漢字の使い分けの誤り"
    },
    "subject_verb_agreement": {
      "en": "subject-verb agreement — verb does not agree with its subject in number/person"
    },
    "tense_aspect": {
      "en": "tense/aspect — wrong verb tense or aspect"
    },
    "topic_comment": {
      "ja": "主題—解説構造——「は」による主題提示など、主題と解説の組み立て方の誤り",
      "zh": "话题—评论结构——话题/主语—述题结构使用不当（常为母语结构的过度迁移）"
    },
    "word_choice": {
      "en": "word choice — a wrong or unnatural lexical choice (right idea, wrong word)",
      "ja": "語彙選択——語の選び方が誤っている、または不自然（意味は近いが語が不適切）",
      "zh": "词语选择——用词错误或不自然（意思接近但用词不当）"
    },
    "word_order": {
      "en": "word order — words or phrases arranged in an unnatural or ungrammatical sequence",
      "ja": "語順——語や成分の並び順が不自然、または文法的に誤っている",
      "zh": "语序——词语或成分的排列顺序不自然或不合语法"
    }
  },
  "templates": {
    "article": {
      "en": "Article error: you wrote “{learner_form}”, but it should be “{corrected_form}”. English marks nouns for definiteness — use “the” for something specific or already known, “a/an” for one non-specific countable thing, and no article for general plurals or uncountables.",
      "ja": "冠詞の誤り：「{learner_form}」は「{corrected_form}」とすべきです。英語は名詞の「特定・不特定」を冠詞で示します——特定・既知は「the」、不特定で数えられる単数は「a/an」、総称の複数や不可算名詞は無冠詞です。日本語に冠詞がないため母語の影響で起きやすい誤りです。",
      "zh": "冠词错误：你写的是“{learner_form}”，应为“{corrected_form}”。英语名词要区分“定/不定”——特指或已知用“the”，泛指的单数可数名词用“a/an”，泛指复数或不可数名词则不用冠词。汉语没有冠词，这类错误常源于母语负迁移。"
    },
    "aspect_marker": {
      "en": "Aspect error: “{learner_form}” should be “{corrected_form}”. Chinese marks aspect, not tense: 了 = completed action, 过 = past experience (“have ever”), 着 = ongoing/durative state. Choose the marker by how the action unfolds, not by English tense.",
      "ja": "アスペクトの誤り：「{learner_form}」は「{corrected_form}」とすべきです。中国語は時制ではなくアスペクトを標示します：了＝完了、过＝経験（〜したことがある）、着＝持続・進行中の状態。英語などの時制ではなく、動作の様態で標識を選びます。",
      "zh": "体标记错误：“{learner_form}”应为“{corrected_form}”。汉语标示的是体而非时态：了表示动作完成，过表示曾经的经历，着表示持续／进行的状态。应按动作的展开方式选择，而不是按外语的时态对应。"
    },
    "ba_construction": {
      "en": "把-construction error: “{learner_form}” should be “{corrected_form}”. This sentence needs the 把 structure to show what happens to the object.",
      "ja": "「把」構文の誤り：「{learner_form}」は「{corrected_form}」とすべきです。この文では目的語に何が起きるかを示すために「把」構文が必要です。",
      "zh": "把字句错误：“{learner_form}”应为“{corrected_form}”。此句需要用“把”字结构来说明对宾语做了什么。"
    },
    "classifier": {
      "en": "Classifier error: “{learner_form}” uses the wrong measure word. Use “{corrected_form}” — the classifier that matches this noun (e.g. 本 for books, 件 for clothing, 只 for small animals). Don’t default everything to 个; Chinese pairs a specific classifier with each noun.",
      "ja": "量詞の誤り：「{learner_form}」は量詞が誤っています。この名詞に合う量詞「{corrected_form}」を使ってください（例：本＝本/冊、服＝件、小動物＝只）。なんでも「个」で済まず、中国語は名詞ごとに専用の量詞を用います。",
      "zh": "量词错误：“{learner_form}”用错了量词。应使用与该名词搭配的“{corrected_form}”（如书用“本”、衣服用“件”、小动物用“只”）。不要一律用“个”，汉语中每类名词都有其专用量词。"
    },
    "counter_classifier": {
      "en": "Counter error: “{learner_form}” is the wrong counter. Use “{corrected_form}”, the counter that goes with this kind of noun.",
      "ja": "助数詞の誤り：「{learner_form}」は助数詞が誤っています。この種類の名詞に合う助数詞「{corrected_form}」を使ってください。",
      "zh": "助数词错误：“{learner_form}”用错了助数词。应使用“{corrected_form}”，它才是与这类名词搭配的助数词。"
    },
    "keigo_register": {
      "en": "Politeness (keigo) error: “{learner_form}” is at the wrong honorific level; the reference uses “{corrected_form}”. Japanese distinguishes teineigo (です/ます polite), sonkeigo (exalting the other person’s actions), and kenjougo (humbling your own). Even a grammatically perfect sentence at the wrong keigo level — e.g. plain form where です/ます is expected — is an error.",
      "ja": "敬語の誤り：「{learner_form}」は敬語レベルが誤っています。参照文では「{corrected_form}」を用います。日本語は丁寧語（です・ます）、尊敬語（相手の動作を高める）、謙譲語（自分の動作をへりくだる）を区別します。文法的に正しくても、です・ますが期待される場面で普通体を用いるなど、敬意レベルが誤れば誤りです。",
      "zh": "敬语错误：“{learner_form}”的敬语层级不对，参考译文用的是“{corrected_form}”。日语区分丁宁语（です／ます）、尊敬语（抬高对方的动作）和自谦语（谦卑自己的动作）。即使句子语法完全正确，敬语层级用错（例如在需要です／ます的场合用了简体）也算错误。"
    },
    "omission": {
      "en": "Something required is missing: you wrote “{learner_form}” where the reference has “{corrected_form}”.",
      "ja": "必要な要素が抜けています。「{learner_form}」と書いていますが、参照文では「{corrected_form}」です。",
      "zh": "缺少了必要成分：你写的是“{learner_form}”，而参考译文是“{corrected_form}”。"
    },
    "particle": {
      "en": "Particle error: you used “{learner_form}”, but “{corrected_form}” is required here. Japanese particles mark grammatical role: は presents a known topic, が marks a new-information subject, を marks the direct object, and に/で mark destination/location — so the wrong particle changes how the sentence is read.",
      "ja": "助詞の誤り：「{learner_form}」ではなく、ここでは「{corrected_form}」が必要です。は＝既知の主題、が＝新情報の主語、を＝目的語、に／で＝着点・場所、のように助詞は文法的役割を示すため、誤ると文の解釈が変わります。",
      "zh": "助词错误：你用的是“{learner_form}”，这里需要用“{corrected_form}”。日语助词标示语法关系：は提示“已知主题”，が标记“新信息的主语”，を标记宾语，に／で标记方向／地点——用错助词会改变句子的意思。"
    },
    "phrasal_verb": {
      "en": "Phrasal-verb error: “{learner_form}” should be “{corrected_form}”. The particle (up/out/in …) changes the meaning, so it isn’t interchangeable.",
      "ja": "句動詞の誤り：「{learner_form}」は「{corrected_form}」とすべきです。不変化詞（up/out/in など）で意味が変わるため、入れ替えはできません。",
      "zh": "短语动词错误：“{learner_form}”应为“{corrected_form}”。小品词（up/out/in 等）会改变词义，不能随意替换。"
    },
    "preposition": {
      "en": "Preposition error: “{learner_form}” should be “{corrected_form}”. The preposition here is fixed by the verb, noun, or set phrase (e.g. depend on, interested in, arrive at) — it isn’t chosen by literal translation.",
      "ja": "前置詞の誤り：「{learner_form}」は「{corrected_form}」とすべきです。ここでの前置詞は動詞・名詞・定型表現によって決まり（例：depend on、interested in、arrive at）、逐語訳では選べません。",
      "zh": "介词错误：“{learner_form}”应为“{corrected_form}”。这里的介词由动词、名词或固定搭配决定（如 depend on、interested in、arrive at），不能按字面直译选择。"
    },
    "register": {
      "en": "“{learner_form}” is at the wrong level of formality. “{corrected_form}” matches the register (tone/politeness) of the original.",
      "ja": "「{learner_form}」は丁寧さ・語調のレベルが合っていません。「{corrected_form}」が原文の文体（語調・丁寧さ）に合います。",
      "zh": "“{learner_form}”的正式程度不合适。“{corrected_form}”更符合原文的语域（语气／礼貌程度）。"
    },
    "resultative_complement": {
      "en": "Resultative-complement error: “{learner_form}” should be “{corrected_form}”. The result of the action must be attached to the verb as a complement.",
      "ja": "結果補語の誤り：「{learner_form}」は「{corrected_form}」とすべきです。動作の結果は補語として動詞に付ける必要があります。",
      "zh": "结果补语错误：“{learner_form}”应为“{corrected_form}”。动作的结果应作为补语附在动词之后。"
    },
    "script_choice": {
      "en": "Script error: “{learner_form}” should be written as “{corrected_form}” (the expected kana/kanji choice here).",
      "ja": "表記の誤り：「{learner_form}」は「{corrected_form}」と書くべきです（ここで期待される仮名／漢字の使い分け）。",
      "zh": "书写（假名／汉字）错误：“{learner_form}”应写作“{corrected_form}”。"
    },
    "subject_verb_agreement": {
      "en": "Agreement error: “{learner_form}” doesn’t agree with its subject. Use “{corrected_form}” to match the subject in number and person.",
      "ja": "主語と動詞の一致の誤り：「{learner_form}」は主語と一致していません。数・人称を主語に合わせて「{corrected_form}」を使ってください。",
      "zh": "主谓一致错误：“{learner_form}”与主语不一致。应使用“{corrected_form}”，在数和人称上与主语保持一致。"
    },
    "tense_aspect": {
      "en": "Tense/aspect error: you wrote “{learner_form}”, but “{corrected_form}” is needed to express the correct time or aspect of the action.",
      "ja": "時制・相の誤り：「{learner_form}」と書いていますが、動作の時間や状態を正しく表すには「{corrected_form}」が必要です。",
      "zh": "时态／体错误：你写的是“{learner_form}”，需要用“{corrected_form}”来表达正确的时间或动作状态。"
    },
    "topic_comment": {
      "en": "Topic–comment error: you structured this as “{learner_form}”, but “{corrected_form}” presents the topic and comment the way the target language does.",
      "ja": "主題—解説構造の誤り：「{learner_form}」と組み立てていますが、「{corrected_form}」が目標言語に沿った主題と解説の示し方です。",
      "zh": "主题—评论结构错误：你写成了“{learner_form}”，而“{corrected_form}”按目标语言的方式来呈现主题与评论。"
    },
    "word_choice": {
      "en": "“{learner_form}” isn’t the right word here — the reference uses “{corrected_form}”. The meaning is close, but this isn’t how it’s normally expressed.",
      "ja": "「{learner_form}」は適切な語ではありません。参照文では「{corrected_form}」を使います。意味は近いですが、通常はこう表現します。",
      "zh": "“{learner_form}”用词不当——参考译文用的是“{corrected_form}”。意思接近，但通常不这样表达。"
    },
    "word_order": {
      "en": "You wrote “{learner_form}”, but the natural order here is “{corrected_form}”. The target language orders these elements differently from a word-for-word rendering.",
      "ja": "「{learner_form}」と書いていますが、ここでは「{corrected_form}」の語順が自然です。目標言語ではこれらの成分の並び方が逐語訳とは異なります。",
      "zh": "你写的是“{learner_form}”，但这里自然的语序是“{corrected_form}”。目标语言中这些成分的排列与逐字翻译不同。"
    }
  }
}$taxonomy$::jsonb,
    'TASK-616 dual-translation taxonomy v4 - ZH L2 localised. Adds en-zh / ja-zh per-pair tables and richer classifier (ge overuse / measure-word agreement) + aspect_marker (le/guo/zhe vs tense) glosses+templates on top of v3. Final localised taxonomy: all 6 directed pairs present (ja-en, zh-en, en-ja, zh-ja, en-zh, ja-zh) plus the en/ja/zh baselines. Supersedes v3 (single active row).'
)
ON CONFLICT (version) DO UPDATE
    SET taxonomy = EXCLUDED.taxonomy,
        description = EXCLUDED.description,
        is_active = true;

COMMIT;

-- ============================================================================
-- Verification (run manually after applying):
--   SELECT count(*) FROM public.dt_taxonomy_version WHERE is_active;   -- expect 1
--   SELECT version FROM public.dt_taxonomy_version WHERE is_active;    -- expect 4
-- ============================================================================
