-- ============================================================================
-- Dual Translation - taxonomy v2 seed (TASK-616, Stage 4 localisation)
-- Cumulative, self-contained (each version row is a COMPLETE taxonomy the cascade
-- loads as one active row). Per-pair subtype lists mirror the L2 baseline set/order;
-- the localisation payload is the enriched per-L1 templates / per-L2 glosses + the
-- explicit pairs[l1-l2] keys. The taxonomy carries NO weights (see dt_rubric_v2_seed.sql).
-- ============================================================================

BEGIN;

-- Enforce the single-active-row invariant: deactivate any other active row, then
-- upsert THIS version as the active one (idempotent: re-applying keeps exactly this
-- version active and deactivates the rest).
UPDATE public.dt_taxonomy_version SET is_active = false WHERE is_active AND version <> 2;

INSERT INTO public.dt_taxonomy_version (version, is_active, taxonomy, description)
VALUES (
    2,
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
    }
  },
  "subtype_glosses": {
    "article": {
      "en": "article — wrong, missing, or extra a/an/the; covers definiteness (a vs the) and using no article where one is required (or vice versa) with countable/uncountable nouns"
    },
    "aspect_marker": {
      "zh": "体标记——“了/过/着”等体标记使用错误（汉语用体而非时态）"
    },
    "ba_construction": {
      "zh": "把字句——“把”字结构使用错误或缺失"
    },
    "classifier": {
      "zh": "量词——量词使用错误，或与名词搭配不当（如过度使用“个”）"
    },
    "counter_classifier": {
      "ja": "助数詞——数を数える際の助数詞（カウンター）の誤り"
    },
    "keigo_register": {
      "ja": "敬語——敬語レベルの誤り（丁寧語・尊敬語・謙譲語）。文法的に正しくても敬意レベルが誤っていれば誤りとする"
    },
    "omission": {
      "en": "omission — a required word or element is missing",
      "ja": "要素の欠落——必要な語や要素が抜けている",
      "zh": "成分缺失——缺少必要的词或成分"
    },
    "particle": {
      "ja": "助詞——助詞の誤り（は/が、を、に/で など）"
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
      "en": "Aspect error: “{learner_form}” should be “{corrected_form}”. Chinese marks aspect (了/过/着), not tense — the marker shows whether the action is completed, experienced, or ongoing.",
      "ja": "アスペクト標識の誤り：「{learner_form}」は「{corrected_form}」とすべきです。中国語は時制ではなくアスペクト（了/过/着）で、動作が完了・経験・継続のいずれかを示します。",
      "zh": "体标记错误：“{learner_form}”应为“{corrected_form}”。汉语用体标记（了/过/着）而非时态，用来表示动作是否完成、是否经历过或正在进行。"
    },
    "ba_construction": {
      "en": "把-construction error: “{learner_form}” should be “{corrected_form}”. This sentence needs the 把 structure to show what happens to the object.",
      "ja": "「把」構文の誤り：「{learner_form}」は「{corrected_form}」とすべきです。この文では目的語に何が起きるかを示すために「把」構文が必要です。",
      "zh": "把字句错误：“{learner_form}”应为“{corrected_form}”。此句需要用“把”字结构来说明对宾语做了什么。"
    },
    "classifier": {
      "en": "Classifier error: “{learner_form}” is the wrong measure word. Use “{corrected_form}”, the classifier that matches this noun (don’t default to 个).",
      "ja": "量詞の誤り：「{learner_form}」は量詞が誤っています。この名詞に合う量詞「{corrected_form}」を使ってください（なんでも「个」にしないこと）。",
      "zh": "量词错误：“{learner_form}”用错了量词。应使用“{corrected_form}”，它才是与该名词搭配的量词（不要一律用“个”）。"
    },
    "counter_classifier": {
      "en": "Counter error: “{learner_form}” is the wrong counter. Use “{corrected_form}”, the counter that goes with this kind of noun.",
      "ja": "助数詞の誤り：「{learner_form}」は助数詞が誤っています。この種類の名詞に合う助数詞「{corrected_form}」を使ってください。",
      "zh": "助数词错误：“{learner_form}”用错了助数词。应使用“{corrected_form}”，它才是与这类名词搭配的助数词。"
    },
    "keigo_register": {
      "en": "Politeness (keigo) error: “{learner_form}” is at the wrong honorific level. The reference uses “{corrected_form}”, which matches the politeness expected here — even a grammatical sentence at the wrong keigo level is an error.",
      "ja": "敬語の誤り：「{learner_form}」は敬語レベルが誤っています。参照文では「{corrected_form}」を使い、この場面で求められる敬意レベルに合っています。文法的に正しくても敬語レベルが誤っていれば誤りです。",
      "zh": "敬语错误：“{learner_form}”的敬语层级不对。参考译文用的是“{corrected_form}”，符合此处所需的礼貌程度——即使句子语法正确，敬语层级错误也算错误。"
    },
    "omission": {
      "en": "Something required is missing: you wrote “{learner_form}” where the reference has “{corrected_form}”.",
      "ja": "必要な要素が抜けています。「{learner_form}」と書いていますが、参照文では「{corrected_form}」です。",
      "zh": "缺少了必要成分：你写的是“{learner_form}”，而参考译文是“{corrected_form}”。"
    },
    "particle": {
      "en": "Particle error: you used “{learner_form}”, but “{corrected_form}” is required here. The particle marks the grammatical role, so the wrong one changes how the sentence is read.",
      "ja": "助詞の誤り：「{learner_form}」を使っていますが、ここでは「{corrected_form}」が必要です。助詞は文法的な役割を示すため、誤ると文の意味が変わります。",
      "zh": "助词错误：你用的是“{learner_form}”，这里需要用“{corrected_form}”。助词标示语法关系，用错会改变句意。"
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
    'TASK-616 dual-translation taxonomy v2 - EN L2 localised. Adds per-directed-pair subtype tables ja-en / zh-en (resolved via the pairs[l1-l2] path, not the L2 baseline fallback) and richer article/preposition glosses+templates on top of the v1 baseline. Supersedes v1 (single active row). Weight up-weighting lives in dt_rubric_version v2 (TASK-616), NOT here - the taxonomy carries no weights. ZH/JA strings remain AI-authored first drafts pending native review.'
)
ON CONFLICT (version) DO UPDATE
    SET taxonomy = EXCLUDED.taxonomy,
        description = EXCLUDED.description,
        is_active = true;

COMMIT;

-- ============================================================================
-- Verification (run manually after applying):
--   SELECT count(*) FROM public.dt_taxonomy_version WHERE is_active;   -- expect 1
--   SELECT version FROM public.dt_taxonomy_version WHERE is_active;    -- expect 2
-- ============================================================================
