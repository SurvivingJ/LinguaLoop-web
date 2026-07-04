-- ============================================================================
-- Dual Translation — taxonomy v1 baseline seed (TASK-620)
-- Date: 2026-06-29
--
-- The taxonomy twin of the rubric seed (TASK-604). Seeds + activates the single
-- dt_taxonomy_version row that the grading cascade hard-requires:
-- services/dual_translation/grader_cascade.py::get_active_taxonomy raises
-- RuntimeError until an is_active row exists (no silent fallback). With the
-- rubric already seeded, this is the last data-foundation blocker before the
-- cascade can run end-to-end (only passages, TASK-603, then remain).
--
-- taxonomy shape is the canonical contract in
-- wiki/algorithms/translation-grading-cascade.tech.md "Implementation contracts"
-- (defined by TASK-606, NOT reinvented here):
--   pairs["<l2>"].subtypes               -- ordered; index IS the _decode_error contract
--   subtype_glosses["<subtype>"]["<l2>"] -- gloss shown to the grading model, in the L2
--   templates["<subtype>"]["<l1>"]       -- learner-facing explanation, {learner_form}/{corrected_form}
-- Consumers: grader_cascade._resolve_subtypes / _resolve_subtype_labels /
-- render_explanation / _decode_error.
--
-- BASELINE scope: an L2-baseline subtype table per L2 (zh/en/ja) only — every L1
-- shares the L2 baseline via _resolve_subtypes' fallback (pairs["<l1>-<l2>"] ->
-- pairs["<l2>"]), which also maximizes prompt-cache prefix reuse. Subtypes =
-- shared cross-linguistic set [word_order, word_choice, omission, register] +
-- each L2's catalogue from wiki/business-rules/translation-error-taxonomy.md
-- (EN articles/prepositions/...; JA particle/keigo_register/...; ZH classifier/
-- aspect_marker/...). category/source/severity are intentionally absent — they
-- are hardcoded enums (prompts.CATEGORY_ENUM/SOURCE_ENUM/SEVERITY_ENUM) mirroring
-- the dt_error_instance CHECK constraints; only `subtype` is versioned here.
--
-- ZH/JA glosses and templates are AI-authored first drafts, not native-reviewed --
-- same caveat as services/dual_translation/prompts.py and the rubric seed; flagged
-- for QA with TASK-616. Full per-directed-pair <l1>-<l2> subtype tables, rich
-- linguistic templates (ha/ga, keigo nuance, classifier specifics), and per-pair
-- weight overrides are TASK-616 (Stage 4), which supersedes this baseline via a
-- version bump.
--
-- Idempotent: ON CONFLICT (version) refreshes taxonomy/description in place and
-- never duplicates a row or creates a second is_active row. is_active is set only
-- on first INSERT, so re-applying after a later version has superseded v1 will
-- NOT silently re-activate v1 (mirrors the rubric seed).
-- ============================================================================

BEGIN;

INSERT INTO public.dt_taxonomy_version (version, is_active, taxonomy, description)
VALUES (
    1,
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
    }
  },
  "subtype_glosses": {
    "article": {
      "en": "article — incorrect, missing, or extra a/an/the"
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
      "en": "preposition — wrong, missing, or extra preposition (in/on/at/to ...)"
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
      "en": "Article error: you wrote “{learner_form}”, but it should be “{corrected_form}”. Check whether the noun needs a/an, the, or no article.",
      "ja": "冠詞の誤り：「{learner_form}」は「{corrected_form}」とすべきです。その名詞に a/an、the、または冠詞なしのどれが必要かを確認してください。",
      "zh": "冠词错误：你写的是“{learner_form}”，应为“{corrected_form}”。请判断该名词需要 a/an、the，还是不用冠词。"
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
      "en": "Preposition error: “{learner_form}” should be “{corrected_form}”. The correct preposition is fixed by the verb or expression here.",
      "ja": "前置詞の誤り：「{learner_form}」は「{corrected_form}」とすべきです。ここでの前置詞は動詞や定型表現によって決まります。",
      "zh": "介词错误：“{learner_form}”应为“{corrected_form}”。这里的介词由动词或固定搭配决定。"
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
    'TASK-620 dual-translation taxonomy v1 baseline seed: L2-baseline subtype tables for zh/en/ja (shared cross-linguistic subtypes + per-language catalogue), per-subtype x per-L2 glosses shown to the grading model (in the L2), and per-subtype x per-L1 explanation templates in en/zh/ja. category/source/severity are NOT here (hardcoded enums + dt_error_instance CHECK). ZH/JA glosses and templates are AI-authored first drafts pending native review (same caveat as prompts.py); full per-directed-pair tables, rich templates, and per-pair weight overrides are TASK-616, which supersedes this baseline via a version bump.'
)
ON CONFLICT (version) DO UPDATE
    SET taxonomy = EXCLUDED.taxonomy,
        description = EXCLUDED.description;

COMMIT;

-- ============================================================================
-- Verification (run manually after applying):
--   SELECT count(*) FROM public.dt_taxonomy_version WHERE is_active;  -- expect 1
--   SELECT version FROM public.dt_taxonomy_version WHERE is_active;   -- expect 1
--   SELECT jsonb_object_keys(taxonomy) FROM public.dt_taxonomy_version WHERE is_active;
--       -- expect: pairs, subtype_glosses, templates
--   SELECT jsonb_object_keys(taxonomy->'pairs') FROM public.dt_taxonomy_version WHERE is_active;
--       -- expect: en, ja, zh
-- ============================================================================
